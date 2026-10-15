"""Native nearest-Unit ownership and ancestor reset/blocking regression."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from tia_webapi import WebApi, leaf_var
from fraktal_tia_binding import Catalog

spec = importlib.util.spec_from_file_location('unit_guard', HERE.parent / 'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UNIT)


def probe(out):
    kinds = Catalog.read().enums['E_HmiRequestKind']
    checks = []
    complete = False
    root = 'StationA'
    owner = root + '.Satellite.Inner'
    target = owner + '.Cell.Gate'
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row, ensure_ascii=True) + '\n')
            stream.flush()

        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})

        def check(label, actual, expected):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((label, ok))
            emit({'event': 'check', 'label': label, 'actual': actual,
                  'expected': expected, 'passed': ok})
            if not ok:
                raise AssertionError(label)

        def wait(predicate, label):
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(.02)
            raise AssertionError(label)

        def write(values):
            emit({'event': 'mutation-guard', 'status': UNIT.guard(), 'targets': list(values)})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')), 'value': v})
                                for p, v in values.items()])
            if any(error for value, error in replies):
                raise AssertionError('native write refused')

        def request(kind, **fields):
            seq = (int(read(root + '.HmiRequest.Sequence')) + 1) & 0xffffffff or 1
            values = dict(Kind=kinds[kind], IntValue=0, User='', Secret='', TargetPath='')
            values.update(fields)
            write({root + '.HmiRequest.' + n: v for n, v in values.items()})
            write({root + '.HmiRequest.Sequence': seq})
            wait(lambda: read(root + '.HmiResponse.AckSequence') == seq, 'mailbox ack')
            return seq, read(root + '.HmiResponse.Accepted')

        try:
            api.login('fraktal')
            emit({'event': 'connection', 'pin': api.fingerprint, 'status': UNIT.guard()})
            for name in (root, root + '.Satellite', owner, 'StationB'):
                check(name + ' initially has no active alarm', read(name + '.AlarmLog.NActive'), 0)
            seq, accepted = request('LOGIN', User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
            check('login consumed', accepted, True)
            wait(lambda: read(root + '.Access.LoginResultSequence') == seq and
                 not read(root + '.Access.LoginBusy'), 'login result')
            check('admin authenticated', read(root + '.Access.CurrentLevel'), 4)
            modes = Catalog.read().enums['E_Mode']
            check('MANUAL cascade accepted', request('SET_MODE', IntValue=modes['MANUAL'])[1], True)
            wait(lambda: read(owner + '.ModeActivePublished') == modes['MANUAL'], 'nested manual mode')
            check('nested manual fault accepted', request('MANUAL_COMMAND', TargetPath=target, IntValue=4)[1], True)
            wait(lambda: read(owner + '.AlarmLog.NActive') == 1 and
                 read(owner + '.AlarmLog.Active[1].State') == 2, 'nearest owner WAIT_RESET')
            check('fault source stays canonical', read(owner + '.AlarmLog.Active[1].SourcePath'), target)
            check('first-out text preserved', read(owner + '.AlarmLog.Active[1].Description'), 'test.first')
            check('nearest Unit blocks', read(owner + '.AlarmLog.Blocking'), True)
            check('root own log not duplicated', read(root + '.AlarmLog.NActive'), 0)
            check('middle Unit own log not duplicated', read(root + '.Satellite.AlarmLog.NActive'), 0)
            check('root manual release query accepted', request('RELEASE_MANUAL', TargetPath=target, IntValue=1)[1], True)
            check('ancestor release reflects nested blocking', read(root + '.HmiResponse.Report.Released'), False)
            count = read(root + '.HmiResponse.Report.Count')
            descriptions = [read(root + '.HmiResponse.Report.Reasons[%d].Description' % i)
                            for i in range(1, count + 1)]
            check('ancestor explains manual reset', 'std.release.manualReset' in descriptions, True)
            check('peer root stays nonblocking', read('StationB.AlarmLog.Blocking'), False)
            check('root operator reset accepted', request('OPERATOR_RESET')[1], True)
            wait(lambda: not read(owner + '.AlarmLog.Blocking') and read(target + '.Status.State') == 0,
                 'ancestor reset clears nearest owner and command')
            check('nearest owner active list clears', read(owner + '.AlarmLog.NActive'), 0)
            check('ancestor release query accepted after reset', request('RELEASE_MANUAL', TargetPath=target, IntValue=1)[1], True)
            check('one reset restores release', read(root + '.HmiResponse.Report.Released'), True)
            check('logout consumed', request('LOGOUT')[1], True)
            wait(lambda: read(root + '.Access.CurrentLevel') == 0, 'logout')
            check('mailbox secret cleared', read(root + '.HmiRequest.Secret'), '')
            complete = True
        finally:
            api.conn.close()
            if not complete:
                checks.append(('probe completed', False))
            emit({'event': 'summary', 'checks': len(checks), 'failures': sum(not ok for _, ok in checks),
                  'completed': complete})
            suite = ET.Element('testsuite', name='Fraktal.TIA.NestedAlarm', tests=str(len(checks)),
                               failures=str(sum(not ok for _, ok in checks)))
            for label, ok in checks:
                case = ET.SubElement(suite, 'testcase', name=label)
                if not ok:
                    ET.SubElement(case, 'failure', message=label)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'), encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    probe(Path(sys.argv[1]))

"""Native config capability, atomic model change and local-retain acceptance."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Tests/Config')
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from tia_webapi import WebApi, leaf_var
from fraktal_tia_binding import Catalog
spec = importlib.util.spec_from_file_location('unit_guard', HERE.parent / 'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec); spec.loader.exec_module(UNIT)


def probe(out):
    catalog = Catalog.read(); kinds = catalog.enums['E_HmiRequestKind']; modes = catalog.enums['E_Mode']
    checks = []; complete = False
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row, ensure_ascii=True) + '\n'); stream.flush()

        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})

        def check(label, actual, expected):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((label, ok)); emit({'event': 'check', 'label': label, 'actual': actual, 'expected': expected, 'passed': ok})
            if not ok:
                raise AssertionError(label)

        def wait(predicate, label):
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if predicate(): return
                time.sleep(.02)
            raise AssertionError(label)

        def write(values):
            emit({'event': 'mutation-guard', 'status': UNIT.guard(), 'targets': list(values)})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')), 'value': v}) for p, v in values.items()])
            if any(error for value, error in replies):
                emit({'event': 'write-errors', 'errors': [{'path': path, 'code': error['code']} for path, (value, error) in zip(values, replies) if error]})
                raise AssertionError('native write refused')

        def request(kind, root='StationA', **fields):
            seq = (int(read(root + '.HmiRequest.Sequence')) + 1) & 0xffffffff or 1
            values = dict(Kind=kinds[kind], TargetPath='', NameValue='', TextValue='', IntValue=0,
                          BoolValue=False, DurationMs=0, User='', Secret='')
            values.update(fields)
            write({root + '.HmiRequest.' + n: v for n, v in values.items()})
            write({root + '.HmiRequest.Sequence': seq})
            wait(lambda: read(root + '.HmiResponse.AckSequence') == seq, 'mailbox ack')
            return seq, read(root + '.HmiResponse.Accepted')

        def login(user='admin'):
            seq, ok = request('LOGIN', User=user, Secret=os.environ['FRAKTAL_TIA_' + user.upper() + '_PIN'])
            check(user + ' login consumed', ok, True)
            wait(lambda: read('StationA.Access.LoginResultSequence') == seq and not read('StationA.Access.LoginBusy'), 'login result')
            check(user + ' authenticated', read('StationA.Access.CurrentLevel'), 4 if user == 'admin' else 1)

        def edit(scope, key, value, revision=2, model=0):
            return request('WRITE_CONFIG', TargetPath=scope, NameValue=key, TextValue=value, IntValue=revision, DurationMs=model)[1]

        def query(model=0):
            entries = []; index = 0
            names = ('Scope', 'Item', 'ValueText', 'WriteKey', 'WriteRevision', 'ConfigKind', 'Writable',
                     'RequiresReady', 'Readable', 'ReadLevel', 'WriteLevel', 'ModelScoped')
            while True:
                assert request('QUERY_CONFIG', IntValue=index, DurationMs=model)[1]
                base = 'StationA.HmiResponse.ConfigPage'
                count = read(base + '.EntryCount'); pages = read(base + '.PageCount')
                paths = [base + '.Entries[%d].%s' % (slot, field) for slot in range(1, count + 1) for field in names]
                replies = api.bulk([('PlcProgram.Read', {'var': leaf_var(p.split('.'))}) for p in paths])
                assert not any(error for value, error in replies)
                values = [value for value, error in replies]
                entries += [dict(zip(names, values[i:i + len(names)])) for i in range(0, len(values), len(names))]
                if index + 1 >= pages: return entries
                index += 1

        def corrupt(scope, key, model, value, schema=4):
            fields = dict(CorruptScope=scope, CorruptKey=key, CorruptModel=model,
                          CorruptText=value, CorruptSchema=schema, CorruptPulse=True)
            write({'GDB_ConfigTest.' + k: v for k, v in fields.items()})
            wait(lambda: not read('GDB_ConfigTest.CorruptPulse'), 'corruption consumed')
            check('retained test record exists', read('GDB_ConfigTest.CorruptSlot') > 0, True)

        def restart(power=False):
            nonlocal api
            api.conn.close()
            if power:
                result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(HERE / 'cycle_simulator.ps1')], capture_output=True)
                emit({'event': 'power-cycle', 'output': result.stdout.decode('utf-8-sig'), 'exit_code': result.returncode})
                assert result.returncode == 0
            else:
                for action in ('halt', 'run'):
                    emit({'event': 'mode-guard', 'action': action, 'status': UNIT.guard()})
                    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(HERE.parents[1] / 'Spikes/S12_TypeMap/simulator.ps1'), '-Action', action], capture_output=True)
                    emit({'event': 'mode-result', 'output': result.stdout.decode('utf-8-sig'), 'exit_code': result.returncode})
                    assert result.returncode == 0
            api = WebApi('169.254.212.49', pin, False); api.login('fraktal')

        try:
            api.login('fraktal'); emit({'event':'connection','status':UNIT.guard()})
            login()
            check('AUTO mode accepted', request('SET_MODE', IntValue=modes['AUTO'])[1], True)
            wait(lambda: read('StationA.ModeActivePublished') == modes['AUTO'], 'AUTO mode')
            check('initial Start release query accepted', request('RELEASE_START')[1], True)
            check('initial Start released', read('StationA.HmiResponse.Report.Released'), True)
            write({'GDB_ConfigTest.BlockRestore':True})
            corrupt('StationA','preset','MODEL_A','22',schema=999)
            restart()
            check('blocking policy retained across STOP/RUN', read('GDB_ConfigTest.BlockRestore'), True)
            check('blocked restore policy published', read('StationA.ConfigPersist.RestorePolicy'), 1)
            check('restore loss published', read('StationA.ConfigPersist.RestoreLost'), True)
            check('loss is unacknowledged', read('StationA.ConfigPersist.RestoreAcknowledged'), False)
            login()
            check('AUTO mode accepted', request('SET_MODE', IntValue=modes['AUTO'])[1], True)
            wait(lambda: read('StationA.ModeActivePublished') == modes['AUTO'], 'AUTO mode')
            check('blocked Start release query accepted', request('RELEASE_START')[1], True)
            check('unacknowledged loss withholds Start', read('StationA.HmiResponse.Report.Released'), False)
            count=read('StationA.HmiResponse.Report.Count')
            reasons=[read('StationA.HmiResponse.Report.Reasons[%d].Description'%i) for i in range(1,count+1)]
            emit({'event':'release-reasons','descriptions':reasons})
            check('Start refusal names config loss', 'std.release.configRestoreUnacknowledged' in reasons, True)
            check('admin acknowledges restore loss', request('ACK_CONFIG_RESTORE')[1], True)
            check('acknowledged Start query accepted', request('RELEASE_START')[1], True)
            check('one acknowledgment releases Start', read('StationA.HmiResponse.Report.Released'), True)
            check('rejected model record defaulted completely', read('StationA.ParCfg.Preset'), 10)
            write({'GDB_ConfigTest.BlockRestore':False})
            check('default restore policy restored', read('StationA.ConfigPersist.RestorePolicy'), 0)
            check('MANUAL mode restored', request('SET_MODE', IntValue=modes['MANUAL'])[1], True)
            wait(lambda: read('StationA.ModeActivePublished') == modes['MANUAL'], 'MANUAL mode')
            check('logout accepted', request('LOGOUT')[1], True)
            complete=True
        finally:
            api.conn.close()
            if not complete: checks.append(('probe completed', False))
            emit({'event': 'summary', 'checks': len(checks), 'failures': sum(not ok for _, ok in checks), 'completed': complete})
            suite = ET.Element('testsuite', name='Fraktal.TIA.ConfigRestorePolicy', tests=str(len(checks)), failures=str(sum(not ok for _, ok in checks)))
            for label, ok in checks:
                case = ET.SubElement(suite, 'testcase', name=label)
                if not ok: ET.SubElement(case, 'failure', message=label)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'), encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    probe(Path(sys.argv[1]))

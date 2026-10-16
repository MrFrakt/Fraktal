"""Normalize mutated bench values and verify durable idle/privacy boundaries."""
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def verify(out):
    rows = []
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row)+'\n'); stream.flush()

        def check(label, actual, expected=True):
            passed = type(actual) is type(expected) and actual == expected
            rows.append((label, passed))
            emit(dict(event='check', label=label, actual=actual, expected=expected, passed=passed))
            assert passed, label

        try:
            api.login('fraktal')
            box = Mailbox(api, guard, emit)
            catalog = Catalog.read()
            manual = catalog.enums['E_Mode']['MANUAL']
            for root in ('StationA', 'StationB'):
                assert box.request('LOGIN', root, User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                deadline = time.monotonic()+10
                while box.read(root+'.Access.LoginBusy') and time.monotonic() < deadline: time.sleep(.05)
                assert box.read(root+'.Access.CurrentLevel') == 4
                if any(box.read(root+'.'+state) for state in ('Busy', 'Error', 'Done', 'Aborted')):
                    check('release bench command '+root, box.request('OPERATOR_RESET', root))
                    deadline = time.monotonic()+10
                    while (box.read(root+'.Busy') or box.read(root+'.Error')) and time.monotonic() < deadline: time.sleep(.05)
                    assert not box.read(root+'.Busy') and not box.read(root+'.Error')
                check('return to MANUAL '+root, box.request('SET_MODE', root, IntValue=manual))
                deadline = time.monotonic()+10
                while box.read(root+'.ModeActivePublished') != manual and time.monotonic() < deadline: time.sleep(.05)
                assert box.read(root+'.ModeActivePublished') == manual
            for scope, key, value in [('StationA','siteLabel','bench'), ('StationA.Satellite','siteLabel','bench'),
                                      ('StationA','long.'+'k'*135,'long default'), ('StationA','ratio','1.25')]:
                check('normalize '+scope+' '+key, box.request('WRITE_CONFIG', TargetPath=scope, NameValue=key, TextValue=value, IntValue=1))
            for key, text, member in (('gain', '1e-40', 'Gain'), ('ratio', '1e-310', 'Ratio')):
                previous = box.read('StationA.StationCfg.'+member)
                check('native subnormal refused '+key, box.request('WRITE_CONFIG', TargetPath='StationA', NameValue=key,
                      TextValue=text, IntValue=1), False)
                check('underflow leaves config unchanged '+key, box.read('StationA.StationCfg.'+member), previous)
            for root in ('StationA', 'StationB'):
                check('no remaining named sets '+root, box.request('LIST_CONFIG_SETS', root))
                for i in range(1, box.read(root+'.ConfigSetCount')+1):
                    name = box.read(root+'.ConfigSets[%d].SetName'%i)
                    check('remove bench set '+root+' '+name, box.request('DELETE_CONFIG_SET', root, TextValue=name))
                assert box.request('LIST_CONFIG_SETS', root)
                check('empty set list '+root, box.read(root+'.ConfigSetCount'), 0)
            # All new implementation storage remains private; owner values are readonly.
            for path in ('FRK_ConfigScratch.EnumCount', 'FRK_ConfigScratch.Value.Decimal'):
                _, error = api.bulk([('PlcProgram.Read', dict(var=leaf_var(path.split('.'))))])[0]
                check('private '+path, error['code'], 200)
            for path, value in [('StationA.StationCfg.Ratio', 2.0), ('StationA.StationCfg.Grade', 2), ('StationA.StationCfg.Offsets[-1]', 1)]:
                emit(dict(event='readonly-write-guard', status=guard(), path=path))
                _, error = api.bulk([('PlcProgram.Write', dict(var=leaf_var(path.split('.')), value=value))])[0]
                check('readonly '+path, error['code'], 205)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                if all(not box.read(root+'.ConfigPersist.Pending') and not box.read(root+'.ConfigPersist.Failed') for root in ('StationA','StationB')): break
                time.sleep(.1)
            else: raise TimeoutError('final verified durability')
            for root in ('StationA', 'StationB'):
                check('logout '+root, box.request('LOGOUT', root))
                for member, expected in [('ModeActivePublished', catalog.enums['E_Mode']['MANUAL']), ('RunningPublished', False),
                                         ('Busy', False), ('Error', False), ('Held', False), ('Access.CurrentLevel', 0),
                                         ('Status.State', catalog.enums['E_ExecState']['READY']), ('AlarmLog.Blocking', False),
                                         ('ConfigPersist.Pending', False), ('ConfigPersist.Failed', False),
                                         ('StationCfg.Ratio', 1.25), ('StationCfg.Gain', 2.5), ('StationCfg.Grade', 1)]:
                    check(root+'.'+member, box.read(root+'.'+member), expected)
            check('preserved owner RUN', guard()['state'], 'Run')
            emit(dict(event='summary', completed=True, assertions=len(rows), failures=0))
        finally:
            api.conn.close()


if __name__ == '__main__':
    verify(Path(sys.argv[1]))

"""Disable committed test stimuli, idle the roots, then verify a guarded restart."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def normalize(out):
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    with out.open('x', encoding='ascii') as stream:
        def emit(row):
            stream.write(json.dumps(row)+'\n'); stream.flush()
        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})
        def write(values):
            emit({'event': 'mutation-guard', 'status': guard(), 'targets': list(values)})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')), 'value': v}) for p, v in values.items()])
            assert not any(error for _, error in replies), replies
        def wait(predicate, label):
            deadline = time.monotonic()+60
            while not predicate():
                assert time.monotonic() < deadline, label
                time.sleep(.03)
        try:
            api.login('fraktal')
            mail = Mailbox(api, guard, emit)
            for prefix, args in [('GDB_RecoveryTest.', dict(Enabled=False, RestartOnStart=False, Fault=False,
                    Finish=False, Permit=True, LateTimeout=False, AbortPLC=False)),
                    ('GDB_ProfileIntegration.', dict(Owner=1, Enabled=False, StepNo=10, Branch=0,
                    TimeClass=0, Expected=0, Finish=False, ForceLateTimeout=False))]:
                sequence = (read(prefix+'AckSeq')+1) % 4294967296
                write({prefix+n: v for n, v in args.items()})
                write({prefix+'RequestSeq': sequence})
                wait(lambda: read(prefix+'AckSeq') == sequence, 'test stimulus withdrawn')
            write({p: False for p in ('GDB_SequenceViewTest.Enabled', 'GDB_SequenceDiagnosticTest.Enabled',
                'GDB_SequenceQuiesceTest.Enabled', 'GDB_UnitTest.FaultRoot', 'GDB_UnitTest.IssueChild',
                'GDB_StateAlarmTest.CauseLive')})
            for root in ('StationA', 'StationB'):
                assert mail.request('LOGIN', root, User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                wait(lambda: read(root+'.Access.CurrentLevel') == 4 and not read(root+'.Access.LoginBusy'), 'login completed')
                if read(root+'.AlarmLog.Blocking'):
                    assert mail.request('OPERATOR_RESET', root)
                    wait(lambda: not read(root+'.AlarmLog.Blocking'), 'alarm occurrence cleared')
                if read(root+'.Status.State') != Catalog.read().enums['E_ExecState']['READY']:
                    assert mail.request('STOP', root)
                    write({'GDB_UnitTest.FinishCycle': True})
                    wait(lambda: read(root+'.Status.State') == Catalog.read().enums['E_ExecState']['READY'], 'Unit command stopped')
                    write({'GDB_UnitTest.FinishCycle': False})
                assert mail.request('SET_MODE', root, IntValue=Catalog.read().enums['E_Mode']['MANUAL'])
                wait(lambda: read(root+'.ModeActivePublished') == Catalog.read().enums['E_Mode']['MANUAL'], 'MANUAL committed')
                assert mail.request('LOGOUT', root)
            api.conn.close()
            for action in ('halt', 'run'):
                emit({'event': 'restart-guard', 'action': action, 'status': guard()})
                result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'), '-Action', action], capture_output=True)
                emit({'event': 'restart', 'action': action, 'exit_code': result.returncode,
                      'output': result.stdout.decode('utf-8-sig')})
                assert result.returncode == 0
            emit({'event': 'summary', 'complete': True, 'status': guard()})
        finally:
            api.conn.close()


if __name__ == '__main__':
    normalize(Path(sys.argv[1]))

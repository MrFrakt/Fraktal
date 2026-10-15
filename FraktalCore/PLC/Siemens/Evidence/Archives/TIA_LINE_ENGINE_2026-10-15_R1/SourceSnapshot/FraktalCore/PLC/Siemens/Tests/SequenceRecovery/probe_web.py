"""Guarded native GRAPH freeze, deliberate recovery, reissue and hard boundaries."""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from fraktal_tia_binding import Catalog
from tia_target_guard import guard
from tia_mailbox import Mailbox
from tia_webapi import WebApi, leaf_var


def probe(out):
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    enum = Catalog.read().enums
    root, target, control = 'StationA', 'StationA.Cell.Clamp', 'GDB_RecoveryTest.'
    settings = dict(Enabled=False, RestartOnStart=False, Fault=False, Finish=False, Permit=True, LateTimeout=False, AbortPLC=False)
    checks, complete = [], False
    with out.open('x', encoding='ascii') as stream:
        def emit(row):
            stream.write(json.dumps(row)+'\n'); stream.flush()
        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})
        def write(values):
            emit({'event': 'mutation-guard', 'owner': guard(), 'targets': list(values)})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')), 'value': v}) for p, v in values.items()])
            assert not any(error for _, error in replies), replies
        def wait(predicate, label, seconds=45):
            deadline = time.monotonic()+seconds
            while not predicate():
                assert time.monotonic() < deadline, label
                time.sleep(.03)
        def check(label, actual, expected):
            ok = type(actual) is type(expected) and actual == expected
            emit({'event': 'check', 'label': label, 'actual': actual, 'expected': expected, 'passed': ok})
            checks.append(ok)
            assert ok, label
        def request(**changes):
            settings.update(changes)
            sequence = (read(control+'AckSeq')+1) % 4294967296
            write({control+n: v for n, v in settings.items()})
            write({control+'RequestSeq': sequence})
            wait(lambda: read(control+'AckSeq') == sequence, 'complete test arguments sampled')
        def login():
            if read(root+'.Access.CurrentLevel') != 4:
                assert mail.request('LOGIN', User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                wait(lambda: read(root+'.Access.CurrentLevel') == 4 and not read(root+'.Access.LoginBusy'), 'admin authenticated')
        def mode(name):
            assert mail.request('SET_MODE', IntValue=enum['E_Mode'][name])
            wait(lambda: read(root+'.ModeActivePublished') == enum['E_Mode'][name], 'mode committed')
        def idle():
            request(Enabled=False, Fault=False, Finish=False, Permit=True, LateTimeout=False, AbortPLC=False)
            login()
            if read(root+'.AlarmLog.Blocking'):
                assert mail.request('OPERATOR_RESET')
                wait(lambda: not read(root+'.AlarmLog.Blocking'), 'alarm occurrence reset')
            if read(root+'.Status.State') != enum['E_ExecState']['READY']:
                assert mail.request('STOP')
                write({'GDB_UnitTest.FinishCycle': True})
                wait(lambda: read(root+'.Status.State') == enum['E_ExecState']['READY'], 'Unit command released')
                write({'GDB_UnitTest.FinishCycle': False})
            mode('MANUAL'); mode('AUTO')
            wait(lambda: read(target+'.Status.State') == enum['E_ExecState']['READY'], 'child ready')
        def start(restart=False):
            idle()
            request(Enabled=True, RestartOnStart=restart)
            check('Start accepted', mail.request('START'), True)
            wait(lambda: read(control+'Seq.Step') == 42 and read(target+'.Busy'), 'GRAPH reaches command step')
            wait(lambda: read(control+'Delay') > 5, 'step timer has progressed')
        def fault():
            request(Fault=True)
            wait(lambda: read(root+'.Error') and read(control+'Frozen'), 'fault freezes GRAPH')
            wait(lambda: not read(target+'.Execute'), 'issued child Execute withdrawn')
            check('failed step retained', read(control+'Seq.Step'), 42)
            check('failure cannot advance chart', read(control+'Running'), False)
            check('failed row marked', read(root+'.SequenceSteps[2].ErrorActive'), True)
            check('fault is a reset alarm', read(root+'.AlarmLog.Blocking'), True)
        def reset():
            request(Fault=False)
            check('operator reset accepted', mail.request('OPERATOR_RESET'), True)
            wait(lambda: read(root+'.Status.State') == enum['E_ExecState']['READY'], 'fault latch released')
            wait(lambda: read(control+'ResumePending'), 'retained step rearmed')
            check('reset keeps failed step', read(control+'Seq.Step'), 42)
            check('step delay rearmed', read(control+'Delay'), 0)
            check('cleared row mark', read(root+'.SequenceSteps[2].ErrorActive'), False)
            check('reset does not start motion', read(target+'.Execute'), False)
            check('reset does not run chart', read(control+'Running'), False)

        try:
            api.login('fraktal')
            mail = Mailbox(api, guard, emit)
            emit({'event': 'connection', 'owner': guard(), 'certificate_sha256': api.fingerprint})
            out.with_suffix('.certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
            wait(lambda: not read('FRK_PersistStatus.Restoring'), 'LOAD_DB restore complete')
            write({p: False for p in ('GDB_ProfileIntegration.Enabled', 'GDB_SequenceViewTest.Enabled',
                                      'GDB_SequenceDiagnosticTest.Enabled', 'GDB_SequenceQuiesceTest.Enabled')})
            for path in ('FRK_SequenceOwners.O001.Valid', 'GDB_RecoveryWork.Seq.Step'):
                error = api.bulk([('PlcProgram.Read', {'var': leaf_var(path.split('.'))})])[0][1]
                check('private recovery work '+path, error['code'], 200)
            emit({'event': 'mutation-guard', 'owner': guard(), 'targets': [control+'Seq.Step']})
            error = api.bulk([('PlcProgram.Write', {'var': leaf_var((control+'Seq.Step').split('.')), 'value': 99})])[0][1]
            check('step mirror readonly', error['code'], 205)

            start()
            entries, issues, events = (read(control+n) for n in ('EntryCount', 'IssueCount', 'EventCount'))
            delay = read(control+'Delay')
            fault()
            low = read(control+'LowScans')
            request(Fault=False)
            time.sleep(.15)
            check('clearing condition keeps ERROR latched', read(root+'.Error'), True)
            check('clearing condition never reissues', read(control+'IssueCount'), issues)
            check('frozen timer does not progress', read(control+'Delay') >= delay, True)
            frozen_delay = read(control+'Delay'); time.sleep(.1)
            check('frozen timer stable', read(control+'Delay'), frozen_delay)
            reset()
            time.sleep(.15)
            check('no spontaneous retry after reset', read(control+'IssueCount'), issues)
            check('Execute-low scan occurred', read(control+'LowScans') > low, True)
            check('deliberate recovery Start', mail.request('START'), True)
            wait(lambda: read(control+'IssueCount') == issues+1 and read(target+'.Busy'), 'same step command reissued')
            check('resume skips initial step', read(control+'EntryCount'), entries)
            check('resume re-tests retained step', read(control+'Seq.Step'), 42)
            check('step event latch rearmed', read(control+'EventCount'), events+1)
            check('resume withdraws frozen flag', read(control+'Frozen'), False)
            check('peer root remains ready', read('StationB.Status.State'), enum['E_ExecState']['READY'])
            request(Finish=True)
            wait(lambda: read(control+'Seq.Step') == 99, 'completed retry advances native chart')
            check('retry reaches successor', read(control+'Seq.Step'), 99)

            start(restart=True)
            entries = read(control+'EntryCount'); issues = read(control+'IssueCount')
            fault(); reset()
            check('restart policy Start', mail.request('START'), True)
            wait(lambda: read(control+'IssueCount') == issues+1, 'new command issued after explicit restart')
            check('project policy restarts initial step', read(control+'EntryCount'), entries+1)

            start()
            issues, events = read(control+'IssueCount'), read(control+'EventCount')
            request(Permit=False)
            wait(lambda: read(target+'.Held') and read(root+'.Held'), 'restorable child hold rolls up')
            check('HELD keeps command BUSY', read(root+'.Busy'), True)
            check('HELD is not ERROR', read(root+'.Error'), False)
            check('HELD does not freeze graph', read(control+'Frozen'), False)
            check('HELD does not create reset alarm', read(root+'.AlarmLog.Blocking'), False)
            request(Permit=True)
            wait(lambda: not read(target+'.Held') and not read(root+'.Held'), 'same permit resumes held child')
            check('HELD does not reissue', read(control+'IssueCount'), issues)
            check('HELD does not rearm step event', read(control+'EventCount'), events)

            request(LateTimeout=True)
            wait(lambda: read(root+'.Error') and read(control+'Frozen'), 'late kernel fault frozen next scan')
            check('late fault retains step', read(control+'Seq.Step'), 42)
            check('late fault reason', read(root+'.Status.Diagnostic.ReasonCode'), enum['E_Reason']['TIMEOUT'])
            reset()
            check('late fault recovery Start', mail.request('START'), True)
            wait(lambda: read(control+'IssueCount') == issues+1, 'late fault command reissued')

            # Both abort paths are framework restart boundaries, including ERROR.
            for from_error in (False, True):
                start()
                if from_error:
                    fault()
                entries = read(control+'EntryCount')
                # Abort is a PLC input, not an HMI mailbox request ordinal.
                request(AbortPLC=True)
                check('PLC abort test argument committed', read(control+'AbortPLC'), True)
                wait(lambda: read(control+'Seq.Step') == 0, 'abort invalidates retained step')
                request(AbortPLC=False)
                request(Fault=False)
                if read(root+'.AlarmLog.Blocking'):
                    assert mail.request('OPERATOR_RESET')
                wait(lambda: read(root+'.Status.State') == enum['E_ExecState']['READY'], 'aborted latch released')
                check('after abort Start', mail.request('START'), True)
                wait(lambda: read(control+'Seq.Step') == 42 and read(target+'.Busy'), 'abort restarts chart')
                check('abort returns through initial step', read(control+'EntryCount'), entries+1)

            start()
            entries = read(control+'EntryCount')
            write({'GDB_SequenceQuiesceTest.Enabled': True})
            wait(lambda: read(control+'Seq.Step') == 0 and not read(target+'.Execute'), 'restore quiescence invalidates live work')
            write({'GDB_SequenceQuiesceTest.Enabled': False})
            wait(lambda: read(root+'.Status.State') == enum['E_ExecState']['READY'], 'quiesced Unit returns ready')
            check('quiescence never restarts motion', read(target+'.Execute'), False)
            check('quiescence retains no active step', read(control+'Seq.Step'), 0)
            check('quiescence drops operator session', read(root+'.Access.CurrentLevel'), 0)
            login()
            check('after quiescence Start', mail.request('START'), True)
            wait(lambda: read(control+'Seq.Step') == 42 and read(target+'.Busy'), 'quiescence restarts chart')
            check('quiescence returns through initial step', read(control+'EntryCount'), entries+1)

            idle()
            mode('MANUAL')
            check('mode boundary resets sequence', read(control+'Seq.Step'), 0)
            check('final chart cleared', read(root+'.SequenceStepCount'), 0)
            check('final root ready', read(root+'.Status.State'), enum['E_ExecState']['READY'])
            check('final no alarm', read(root+'.AlarmLog.Blocking'), False)
            check('final logout', mail.request('LOGOUT'), True)
            complete = True
        finally:
            emit({'event': 'summary', 'checks': len(checks), 'passed': sum(checks), 'complete': complete})
            api.conn.close()
    assert complete and all(checks)
    return len(checks)


if __name__ == '__main__':
    print(json.dumps({'checks': probe(Path(sys.argv[1]))}))

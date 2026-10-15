"""Read deterministic native cases and exercise the actual generated Unit frame."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def probe(out):
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    enum = Catalog.read().enums
    root = 'StationA'
    control = 'GDB_ProfileIntegration.'
    profile = root + '.Profiler.'
    checks = []
    complete = False
    with out.open('x', encoding='ascii') as stream:
        def emit(row):
            stream.write(json.dumps(row, ensure_ascii=True) + '\n')
            stream.flush()

        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})

        def write(values):
            emit({'event': 'mutation-guard', 'status': guard(), 'targets': list(values)})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')), 'value': v}) for p, v in values.items()])
            assert not any(error for _, error in replies), 'native test control write refused'

        def wait(predicate, label, seconds=65):
            deadline = time.monotonic() + seconds
            while not predicate():
                assert time.monotonic() < deadline, label
                time.sleep(.03)

        def check(label, actual, expected):
            passed = type(actual) is type(expected) and actual == expected
            emit({'event': 'check', 'label': label, 'actual': actual, 'expected': expected, 'passed': passed})
            checks.append(passed)
            assert passed, label

        def request(**values):
            seq = int(read(control + 'AckSeq')) + 1
            write({control + name: value for name, value in values.items()})
            write({control + 'RequestSeq': seq})
            wait(lambda: read(control + 'AckSeq') == seq, 'test arguments committed')

        def login():
            if read(root + '.Access.CurrentLevel') != 4:
                assert mail.request('LOGIN', User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                wait(lambda: read(root + '.Access.CurrentLevel') == 4 and not read(root + '.Access.LoginBusy'), 'admin authenticated')

        def mode(name):
            busy = read(root + '.Busy')
            assert mail.request('SET_MODE', IntValue=enum['E_Mode'][name])
            if busy:
                # The Unit fixture completes its current operation before the
                # requested mode can commit. This is its existing plant input.
                write({'GDB_UnitTest.FinishCycle': True})
            wait(lambda: read(root + '.ModeActivePublished') == enum['E_Mode'][name], 'mode committed')
            if busy:
                write({'GDB_UnitTest.FinishCycle': False})

        def idle():
            request(Owner=1, Enabled=False, Finish=False, ForceLateTimeout=False)
            login()
            if read(root + '.AlarmLog.Blocking'):
                assert mail.request('OPERATOR_RESET')
                wait(lambda: not read(root + '.AlarmLog.Blocking'), 'alarm reset')
            if read(root + '.Status.State') != enum['E_ExecState']['READY']:
                assert mail.request('STOP')
                write({'GDB_UnitTest.FinishCycle': True})
                wait(lambda: read(root + '.Status.State') == enum['E_ExecState']['READY'], 'graceful stop')
                write({'GDB_UnitTest.FinishCycle': False})
            mode('MANUAL')

        def start(name='AUTO', **values):
            idle()
            mode(name)
            settings = dict(Owner=1, Enabled=True, StepNo=10, Branch=0, TimeClass=enum['E_TimeClass']['WORK'], Expected=10000, Finish=False, ForceLateTimeout=False)
            settings.update(values)
            request(**settings)
            assert mail.request('START')
            wait(lambda: read(root + '.Busy'), 'Unit busy')
            wait(lambda: read(root + '.CurrentStep.StepNo') == settings['StepNo'], 'step recorded')

        try:
            api.login('fraktal')
            mail = Mailbox(api, guard, emit)
            emit({'event': 'connection', 'status': guard(), 'pin': api.fingerprint})
            wait(lambda: not read('FRK_PersistStatus.Restoring'), 'selected document restore')
            wait(lambda: read('GDB_ProfileCases.Complete'), 'native deterministic cases complete')
            labels = json.loads((out.parent / 'profile_cases.json').read_text('ascii'))
            check('native case count', read('GDB_ProfileCases.Count'), len(labels))
            for index, label in enumerate(labels, 1):
                check(label, read('GDB_ProfileCases.Passed[%d]' % index), True)

            write({'GDB_SequenceViewTest.Enabled': False, 'GDB_SequenceDiagnosticTest.Enabled': False,
                   'GDB_SequenceQuiesceTest.Enabled': False})
            request(Owner=1, Enabled=False, Finish=False)
            login()
            assert mail.request('RELEASE_ACTION', IntValue=enum['E_GatedAction']['ALARM_RESET'])
            if read(root + '.HmiResponse.Report.Released'):
                check('pre-test operator reset accepted', mail.request('OPERATOR_RESET'), True)
            else:
                check('fresh fixture needs no fault reset', read(root + '.Error'), False)
            wait(lambda: read(root + '.Status.State') == enum['E_ExecState']['READY'], 'previous test latches released')
            for path in ('FRK_Profiles.P001.Book.Running', 'GDB_ProfileWork.Book.Running', 'GDB_ProfileIntegrationWork.StepNo'):
                _, error = api.bulk([('PlcProgram.Read', {'var': leaf_var(path.split('.'))})])[0]
                check('private work refused ' + path, error['code'], 200)
            for path in (profile + 'HistoryHead', profile + 'LastCycle.CycleNo', root + '.Starved', root + '.Blocked'):
                emit({'event': 'mutation-guard', 'status': guard(), 'targets': [path]})
                _, error = api.bulk([('PlcProgram.Write', {'var': leaf_var(path.split('.')), 'value': 0})])[0]
                check('public mirror readonly ' + path, error['code'], 205)

            before = read(profile + 'LastCycle.CycleNo')
            start(Finish=True)
            wait(lambda: read(profile + 'LastCycle.CycleNo') == before + 1, 'first-scan cycle recorded')
            check('first-scan waterfall', read(profile + 'LastCycle.NSteps'), 1)
            check('first-scan monotonic duration', read(profile + 'LastCycle.Total'), 0)
            check('zero-duration rolling minimum', read(profile + 'MinCycleTime'), 0)
            check('first-scan history entered', read(profile + 'History[%d].CycleNo' % read(profile + 'HistoryHead')), before + 1)
            before += 1
            start()
            check('work is not starved', read(root + '.Starved'), False)
            check('work is not blocked', read(root + '.Blocked'), False)
            time.sleep(.05)
            request(StepNo=20, TimeClass=enum['E_TimeClass']['WAIT_UPSTREAM'])
            wait(lambda: read(root + '.Starved'), 'upstream wait classified')
            check('upstream wait is not blocked', read(root + '.Blocked'), False)
            time.sleep(.05)
            request(StepNo=30, TimeClass=enum['E_TimeClass']['WAIT_DOWNSTREAM'])
            wait(lambda: read(root + '.Blocked'), 'downstream wait classified')
            check('downstream wait is not starved', read(root + '.Starved'), False)
            time.sleep(.05)
            request(StepNo=40, TimeClass=enum['E_TimeClass']['WORK'], Expected=9000, Finish=True)
            wait(lambda: read(profile + 'LastCycle.CycleNo') == before + 1, 'cycle completed by sequence helper')
            check('native waterfall length', read(profile + 'LastCycle.NSteps'), 4)
            check('native waterfall not truncated', read(profile + 'LastCycle.Truncated'), False)
            check('native terminal guard', read(profile + 'LastCycle.Steps[4].Expected'), 9000)
            durations = [read(profile + 'LastCycle.Steps[%d].Duration' % n) for n in range(1, 5)]
            check('native elapsed is sum of waterfall', read(profile + 'LastCycle.Total'), sum(durations))
            check('native work split from own classes', read(profile + 'LastCycle.WorkTime'), durations[0] + durations[3])
            check('native wait split from own classes', read(profile + 'LastCycle.WaitTime'), durations[1] + durations[2])
            check('native upstream bucket', read(profile + 'LastCycle.ByClass[%d]' % enum['E_TimeClass']['WAIT_UPSTREAM']), durations[1])
            check('native downstream bucket', read(profile + 'LastCycle.ByClass[%d]' % enum['E_TimeClass']['WAIT_DOWNSTREAM']), durations[2])
            check('native duration is nonzero', read(profile + 'LastCycle.Total') > 0, True)
            check('native step stats recorded', read(profile + 'StepStats[1].Count') > 0, True)
            check('native timestamp quality', read(profile + 'LastCycle.StartedTimeSynchronized'), False)
            check('second root remains isolated', read('StationB.Profiler.LastCycle.CycleNo'), 0)
            time.sleep(.15)
            check('terminal holding does not duplicate cycle', read(profile + 'LastCycle.CycleNo'), before + 1)

            request(StepNo=20, Branch=1, TimeClass=enum['E_TimeClass']['WAIT_UPSTREAM'], Finish=True)
            time.sleep(.15)
            check('parallel finish does not complete main line', read(profile + 'LastCycle.CycleNo'), before + 1)
            check('parallel wait is not main-line starved', read(root + '.Starved'), False)
            check('parallel wait is not main-line blocked', read(root + '.Blocked'), False)
            check('parallel visit does not consume stat slot', read(profile + 'StatsTruncated'), False)

            request(StepNo=10, Branch=0, TimeClass=enum['E_TimeClass']['WORK'], Finish=False)
            wait(lambda: read(root + '.CurrentStep.StepNo') == 10, 'partial next cycle open')
            mode('MANUAL')
            check('mode exit does not publish partial cycle', read(profile + 'LastCycle.CycleNo'), before + 1)
            check('mode exit retains completed waterfall', read(profile + 'LastCycle.NSteps'), 4)
            check('mode exit clears starved', read(root + '.Starved'), False)
            check('mode exit clears blocked', read(root + '.Blocked'), False)

            start(name='HOME', StepNo=60, Finish=True)
            time.sleep(.15)
            check('HOME sequence is not an AUTO cycle', read(profile + 'LastCycle.CycleNo'), before + 1)

            start(StepNo=70, TimeClass=enum['E_TimeClass']['WAIT_UPSTREAM'])
            wait(lambda: read(root + '.Starved'), 'partial cycle before quiesce')
            write({'GDB_SequenceQuiesceTest.Enabled': True})
            wait(lambda: not read(root + '.Starved'), 'quiesce withdraws live classification')
            write({'GDB_SequenceQuiesceTest.Enabled': False})
            request(Enabled=False, Finish=False)
            check('quiesce retains completed history', read(profile + 'LastCycle.CycleNo'), before + 1)
            check('quiesce clears blocked', read(root + '.Blocked'), False)
            start(TimeClass=enum['E_TimeClass']['WAIT_UPSTREAM'])
            request(Finish=True, ForceLateTimeout=True)
            wait(lambda: read(root + '.Error'), 'kernel resolves the injected late timeout')
            check('late timeout does not count a completed cycle', read(profile + 'LastCycle.CycleNo'), before + 1)
            check('late timeout preserves completed waterfall', read(profile + 'LastCycle.NSteps'), 4)
            check('late timeout reports its reason', read(root + '.Status.Diagnostic.ReasonCode'), enum['E_Reason']['TIMEOUT'])
            check('late timeout withdraws starved', read(root + '.Starved'), False)
            request(Enabled=False, Finish=False, ForceLateTimeout=False)
            check('late timeout operator reset accepted', mail.request('OPERATOR_RESET'), True)
            wait(lambda: read(root + '.Status.State') == enum['E_ExecState']['READY'], 'injected timeout latch released')
            idle()
            check('final root ready', read(root + '.Status.State'), enum['E_ExecState']['READY'])
            check('final no reset alarm', read(root + '.AlarmLog.Blocking'), False)
            check('final logout', mail.request('LOGOUT'), True)
            complete = True
        finally:
            emit({'event': 'summary', 'checks': len(checks), 'passed': sum(checks), 'complete': complete})
            api.conn.close()
    assert complete and all(checks)
    return len(checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    print(json.dumps({'checks': probe(parser.parse_args().out)}))

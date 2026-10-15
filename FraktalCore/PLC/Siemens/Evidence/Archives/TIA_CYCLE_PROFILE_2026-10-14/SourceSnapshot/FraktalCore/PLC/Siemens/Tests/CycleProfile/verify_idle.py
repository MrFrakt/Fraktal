"""Capture the normalized fixture and verify retained login after restart."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from tia_mailbox import Mailbox
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def verify(out):
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    events = []
    try:
        api.login('fraktal')
        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})
        mail = Mailbox(api, guard, events.append)
        assert mail.request('LOGIN', User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
        deadline = time.monotonic() + 30
        while read('StationA.Access.CurrentLevel') != 4 or read('StationA.Access.LoginBusy'):
            assert time.monotonic() < deadline, 'retained private user login'
            time.sleep(.03)
        assert mail.request('LOGOUT')
        wanted = {'FRK_PersistStatus.Restoring': False, 'FRK_PersistStatus.Failed': False,
                  'FRK_PersistStatus.Medium': 'LOAD_DB', 'FRK_PersistStatus.DocumentCount': 17,
                  'GDB_ProfileIntegration.Enabled': False, 'GDB_SequenceViewTest.Enabled': False,
                  'GDB_SequenceDiagnosticTest.Enabled': False, 'GDB_SequenceQuiesceTest.Enabled': False}
        for root in ('StationA', 'StationB'):
            wanted.update({root + '.' + field: value for field, value in {
                'Status.State': 0, 'ModeActivePublished': 1, 'Access.CurrentLevel': 0,
                'Busy': False, 'Held': False, 'AlarmLog.Blocking': False, 'Pending.ReasonCode': 0,
                'ConfigPersist.Pending': False, 'ConfigPersist.Failed': False,
                'SequenceStepCount': 0, 'Profiler.LastCycle.CycleNo': 0, 'Profiler.HistoryHead': 0,
                'Starved': False, 'Blocked': False}.items()})
        actual = {path: read(path) for path in wanted}
        assert actual == wanted, {p: v for p, v in actual.items() if v != wanted[p]}
        with out.open('x', encoding='ascii') as stream:
            json.dump({'owner': guard(), 'retained_login': True, 'events': events,
                       'values': actual, 'complete': True}, stream, indent=2)
            stream.write('\n')
        return {'normalized': len(actual), 'retained_login': True}
    finally:
        api.conn.close()


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]))))

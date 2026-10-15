"""Read-only final state witness; no credentials are recorded."""
from pathlib import Path
import importlib.util
import json
import os
import sys

repo = Path('C:/Projects/Fraktal')
sys.path.insert(0, str(repo / 'FraktalCore/PLC/Siemens/tools'))
from tia_webapi import WebApi, leaf_var
from fraktal_tia_binding import Catalog

spec = importlib.util.spec_from_file_location('guard', repo / 'FraktalCore/PLC/Siemens/Tests/Unit/probe_web.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
try:
    status = guard.guard()
    assert status['state'] == 'Run', status
    api.login('fraktal')
    rows = {}
    for unit in ('StationA', 'StationA.Satellite', 'StationA.Satellite.Inner', 'StationB'):
        fields = ('Access.CurrentLevel', 'Access.LoginBusy', 'ModeActivePublished',
                  'RunningPublished', 'Status.State', 'AlarmLog.NActive', 'AlarmLog.Blocking')
        row = {f: api.call('PlcProgram.Read', {'var': leaf_var((unit + '.' + f).split('.'))}) for f in fields}
        assert row['Access.CurrentLevel'] == 0 and not row['Access.LoginBusy'], (unit, row)
        assert not row['RunningPublished'] and row['Status.State'] == 0, (unit, row)
        assert row['ModeActivePublished'] == Catalog.read().enums['E_Mode']['MANUAL'], (unit, row)
        assert row['AlarmLog.NActive'] == 0 and not row['AlarmLog.Blocking'], (unit, row)
        if unit in ('StationA', 'StationB'):
            row['secretCleared'] = api.call('PlcProgram.Read', {'var': leaf_var([unit, 'HmiRequest', 'Secret'])}) == ''
            assert row['secretCleared']
            row['StateFlagCount'] = api.call('PlcProgram.Read', {'var': leaf_var([unit, 'StateFlagCount'])})
            row['AtHome'] = api.call('PlcProgram.Read', {'var': leaf_var([unit, 'OutImm', 'AtHome'])})
            assert row['StateFlagCount'] == 1 and row['AtHome']
        rows[unit] = row
    with Path(sys.argv[1]).open('x', encoding='ascii', newline='\n') as stream:
        json.dump({'status': status, 'units': rows}, stream, indent=2)
        stream.write('\n')
finally:
    api.conn.close()

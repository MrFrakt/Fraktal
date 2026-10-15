"""Verify recovery controls and the qualified LOAD_DB/profile normalized state."""
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def verify(out):
    spec = importlib.util.spec_from_file_location('profile_idle', HERE.parent/'CycleProfile/verify_idle.py')
    idle = importlib.util.module_from_spec(spec); spec.loader.exec_module(idle)
    result = idle.verify(out.with_suffix('.profile.json'))
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    try:
        api.login('fraktal')
        wanted = {'Enabled': False, 'Fault': False, 'Finish': False, 'LateTimeout': False, 'AbortPLC': False,
                  'Running': False, 'Frozen': False, 'ResumePending': False, 'Seq.Step': 0}
        actual = {n: api.call('PlcProgram.Read', {'var': leaf_var(('GDB_RecoveryTest.'+n).split('.'))}) for n in wanted}
        assert actual == wanted, actual
        with out.open('x', encoding='ascii') as stream:
            json.dump({'complete': True, 'owner': guard(), 'profile': result, 'recovery': actual}, stream, indent=2)
            stream.write('\n')
        print(json.dumps({'normalized': result['normalized']+len(actual), 'retained_login': result['retained_login']}))
    finally:
        api.conn.close()


if __name__ == '__main__':
    verify(Path(sys.argv[1]))

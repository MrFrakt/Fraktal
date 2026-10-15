"""Native proof of public/private retentive fields on the isolated simulator."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from tia_webapi import WebApi, leaf_var
spec = importlib.util.spec_from_file_location('unit_guard', HERE.parent / 'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UNIT)


def probe(out):
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    count = 0
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row) + '\n'); stream.flush()

        def read(field):
            return api.call('PlcProgram.Read', {'var': leaf_var(['GDB_RetainProbe', field])})

        def check(label, actual, expected):
            nonlocal count
            count += 1
            emit({'label': label, 'actual': actual, 'expected': expected, 'passed': actual == expected})
            assert actual == expected, label

        try:
            api.login('fraktal')
            emit({'event': 'mutation-guard', 'status': UNIT.guard()})
            for name, value in (('Proposed', 789123), ('WritePulse', True)):
                api.call('PlcProgram.Write', {'var': leaf_var(['GDB_RetainProbe', name]), 'value': value})
            deadline = time.monotonic() + 4
            while read('WritePulse') and time.monotonic() < deadline:
                time.sleep(.02)
            check('retained live value', read('Saved'), 789123)
            check('private retained value witnessed', read('Live'), 789123)
            rows = api.bulk([('PlcProgram.Read', {'var': leaf_var(['GDB_RetainProbe', 'Hidden'])})])
            check('private retained storage stays hidden', rows[0][1]['code'], 200)
            for action in ('halt', 'run'):
                emit({'event': 'mode-guard', 'status': UNIT.guard(), 'action': action})
                result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                         str(HERE.parents[1] / 'Spikes/S12_TypeMap/simulator.ps1'), '-Action', action], capture_output=True)
                assert result.returncode == 0
                emit({'event': 'mode-result', 'output': result.stdout.decode('utf-8-sig')})
            check('STOP-RUN retains public value', read('Saved'), 789123)
            check('STOP-RUN retains private value', read('Live'), 789123)
            api.conn.close()
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                     str(HERE / 'cycle_simulator.ps1')], capture_output=True)
            emit({'event': 'power-cycle', 'exit_code': result.returncode, 'output': result.stdout.decode('utf-8-sig')})
            assert result.returncode == 0, result.stderr.decode('utf-8-sig')
            api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
            api.login('fraktal')
            check('power-cycle retains public value', read('Saved'), 789123)
            check('power-cycle retains private value', read('Live'), 789123)
            emit({'event': 'summary', 'checks': count, 'failures': 0})
        finally:
            api.conn.close()


if __name__ == '__main__':
    probe(Path(sys.argv[1]))

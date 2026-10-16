"""Qualify the native profile through the production gateway, mapper and views."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def probe(out):
    out.mkdir(parents=True, exist_ok=False)
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    gateway = None
    hmi = HERE.parents[3] / 'HMI'
    sdk = Path(r'C:\Users\Siemens\Documents\FlutterSdk\flutter')
    stop = out / 'gateway.stop'
    try:
        api.login('fraktal')
        (out / 'target.json').write_text(json.dumps(guard(), indent=2) + '\n', encoding='ascii')

        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})

        p = 'StationA.Profiler.'
        base = p + 'LastCycle.'
        expected = {'cycleNo': read(base + 'CycleNo'), 'total': read(base + 'Total'),
                    'work': read(base + 'WorkTime'), 'wait': read(base + 'WaitTime'),
                    'minimum': read(p + 'MinCycleTime'), 'steps': [], 'stats': []}
        assert expected['cycleNo'] > 0, 'Complete the native profile probe first'
        for index in range(1, read(base + 'NSteps') + 1):
            prefix = base + 'Steps[%d].' % index
            expected['steps'].append({name: read(prefix + field) for name, field in
                [('number', 'StepNo'), ('name', 'StepName'), ('class', 'TimeClass'),
                 ('duration', 'Duration'), ('expected', 'Expected')]})
        for index in range(1, 5):
            prefix = p + 'StepStats[%d].' % index
            if read(prefix + 'Count') > 0:
                expected['stats'].append({name: read(prefix + field) for name, field in
                    [('number', 'Id'), ('class', 'TimeClass'), ('average', 'Avg'), ('maximum', 'Maximum')]})
        (out / 'native_expected.json').write_text(json.dumps(expected, indent=2) + '\n', encoding='ascii')
        certificate = out / 'certificate.der'
        certificate.write_bytes(api.conn.sock.getpeercert(binary_form=True))
        api.conn.close()
        with (out / 'gateway.log').open('x', encoding='utf-8') as log:
            gateway = subprocess.Popen([str(sdk / 'bin/cache/dart-sdk/bin/dart.exe'),
                '--packages=' + str(hmi / 'gateway/.dart_tool/package_config.json'),
                str(HERE.parent / 'Manifest/run_gateway.dart'), str(certificate),
                str(HERE.parents[1] / 'Spikes/S12_TypeMap/simulator.ps1'), str(stop)],
                cwd=hmi, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic() + 90
            while 'bench-ready' not in (out / 'gateway.log').read_text('utf-8'):
                assert gateway.poll() is None, 'gateway exited before ready'
                assert time.monotonic() < deadline, 'gateway ready deadline'
                time.sleep(.2)
            env = dict(os.environ, FRAKTAL_TIA_PROFILE_LIVE='1', FRAKTAL_TIA_HMI_OUTPUT=str(out))
            with (out / 'flutter.log').open('x', encoding='utf-8') as log:
                result = subprocess.run([str(sdk / 'bin/flutter.bat'), 'test', '--no-pub', '--run-skipped', '-t', 'live',
                    '--concurrency=1', 'test/live_tia_cycle_profile_test.dart'], cwd=hmi, env=env,
                    stdout=log, stderr=subprocess.STDOUT, timeout=450, creationflags=subprocess.CREATE_NO_WINDOW)
            assert result.returncode == 0, 'Native profile HMI gate failed; see flutter.log'
    finally:
        api.conn.close()
        if gateway is not None:
            stop.write_text('stop owned profile gateway\n', encoding='ascii')
            gateway.wait(timeout=60)
    return {'native_profile_hmi': 'passed', 'output': str(out)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    print(json.dumps(probe(parser.parse_args().out)))

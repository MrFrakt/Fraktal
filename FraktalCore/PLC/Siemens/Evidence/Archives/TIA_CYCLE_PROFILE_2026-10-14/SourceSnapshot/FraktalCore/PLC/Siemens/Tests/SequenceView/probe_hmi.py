"""Render the combined isolated sequence bench through the production gateway."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from tia_webapi import WebApi, leaf_var
from tia_target_guard import guard
from tia_mailbox import Mailbox
from fraktal_tia_binding import Catalog


def probe(out):
    out.mkdir(parents=True, exist_ok=False)
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) /
                 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    gateway = None
    stop = out / 'gateway.stop'
    hmi = HERE.parents[3] / 'HMI'
    sdk = Path(r'C:\Users\Siemens\Documents\FlutterSdk\flutter')
    with (out / 'native.jsonl').open('x', encoding='ascii') as evidence:
        def emit(row):
            evidence.write(json.dumps(row) + '\n'); evidence.flush()

        def write(values):
            emit({'event': 'mutation-guard', 'owner': guard(), 'targets': list(values)})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')),
                                                     'value': v}) for p, v in values.items()])
            assert not any(e for _, e in replies), 'native control write failed'

        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})

        try:
            api.login('fraktal')
            certificate = out / 'certificate.der'
            certificate.write_bytes(api.conn.sock.getpeercert(binary_form=True))
            assert not read('FRK_PersistStatus.Restoring'), 'restore not complete'
            write({'GDB_SequenceViewTest.Enabled': False,
                   'GDB_SequenceViewTest.Annotate': False})
            mailbox = Mailbox(api, guard, emit)
            assert mailbox.request('LOGIN', User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
            deadline = time.monotonic() + 20
            while read('StationA.Access.CurrentLevel') != 4:
                assert time.monotonic() < deadline, 'admin login deadline'
                time.sleep(.05)
            for mode in ('AUTO', 'MANUAL'):
                ordinal = Catalog.read().enums['E_Mode'][mode]
                assert mailbox.request('SET_MODE', IntValue=ordinal)
                deadline = time.monotonic() + 20
                while read('StationA.ModeActivePublished') != ordinal:
                    assert time.monotonic() < deadline, 'mode commit deadline'
                    time.sleep(.05)
            assert mailbox.request('LOGOUT')
            assert read('StationA.SequenceStepCount') == 0, 'start with fresh mode chart'
            c = 'GDB_SequenceViewTest.'
            write({c + k: v for k, v in dict(Owner=1, UseHelper=False, StepNo=42,
                   StepName='test.integration.main', Branch=0, Depth=0, Visit=1,
                   ExpectedTime=50, Elapsed=75, Parent=False, AwaitEnabled=False,
                   Annotate=True, IsError=False, Key='test.integration.warning',
                   SourcePath='StationA.Cell.Clamp', Enabled=True, FastPulse=True).items()})
            api.conn.close()
            with (out / 'gateway.log').open('x', encoding='utf-8') as gateway_log:
                gateway = subprocess.Popen([
                    str(sdk / 'bin/cache/dart-sdk/bin/dart.exe'),
                    '--packages=' + str(hmi / 'gateway/.dart_tool/package_config.json'),
                    str(HERE.parent / 'Manifest/run_gateway.dart'), str(certificate),
                    str(HERE.parents[1] / 'Spikes/S12_TypeMap/simulator.ps1'), str(stop)],
                    cwd=hmi, stdout=gateway_log, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                deadline = time.monotonic() + 90
                while 'bench-ready' not in (out / 'gateway.log').read_text('utf-8'):
                    assert gateway.poll() is None, 'gateway exited before ready'
                    assert time.monotonic() < deadline, 'gateway ready deadline'
                    time.sleep(.2)
                env = dict(os.environ, FRAKTAL_TIA_SEQUENCE_LIVE='1',
                           FRAKTAL_TIA_HMI_OUTPUT=str(out))
                with (out / 'flutter.log').open('x', encoding='utf-8') as flutter_log:
                    result = subprocess.run([str(sdk / 'bin/flutter.bat'), 'test',
                        '--run-skipped', '-t', 'live', '--concurrency=1',
                        'test/live_tia_sequence_view_test.dart'], cwd=hmi, env=env,
                        stdout=flutter_log, stderr=subprocess.STDOUT, timeout=450,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                emit({'event': 'flutter-result', 'exit': result.returncode})
                assert result.returncode == 0, 'native HMI test failed; see flutter.log'
        finally:
            if gateway is not None:
                stop.write_text('stop owned test gateway\n', encoding='ascii')
                gateway.wait(timeout=60)
            # The old HTTPS socket can expire during the UI test. Connect before
            # cleanup; never replay a write whose transport outcome is unknown.
            api.conn.close()
            api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) /
                         'Fraktal/TiaStations/FrkS12.webapi.pin', False)
            api.login('fraktal')
            write({'GDB_SequenceViewTest.Enabled': False,
                   'GDB_SequenceViewTest.Annotate': False})
            api.conn.close()
    return {'nativeHmi': 'passed', 'output': str(out)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    print(json.dumps(probe(parser.parse_args().out)))

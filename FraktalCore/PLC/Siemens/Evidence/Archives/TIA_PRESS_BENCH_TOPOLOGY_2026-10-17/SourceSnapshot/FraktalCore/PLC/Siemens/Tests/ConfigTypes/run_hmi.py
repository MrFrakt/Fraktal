"""Run the existing guarded gateway and generic HMI against typed config."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PLC = HERE.parents[1]
sys.path.insert(0, str(PLC/'tools'))
from tia_target_guard import guard
from tia_webapi import WebApi


def run(out):
    out.mkdir(parents=True, exist_ok=False)
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    guard()
    api = WebApi('169.254.212.49', pin, False)
    certificate = out/'certificate.der'
    certificate.write_bytes(api.conn.sock.getpeercert(binary_form=True))
    api.conn.close()
    dart = Path('C:/Users/Siemens/Documents/FlutterSdk/flutter/bin/cache/dart-sdk/bin/dart.exe')
    flutter = dart.parents[3]/'flutter.bat'
    stop = out/'gateway.stop'
    environment = dict(os.environ, FRAKTAL_TIA_MANIFEST_LIVE='1', FRAKTAL_TIA_ACCESS_LIVE='1',
                       FRAKTAL_TIA_CONFIG_TYPES_LIVE='1', FRAKTAL_TIA_HMI_OUTPUT=str(out), FRAKTAL_TIA_SIM_INSTANCE='Fraktal')
    with (out/'gateway.log').open('xb') as log:
        gateway = subprocess.Popen([str(dart), 'run', 'run_gateway.dart', str(certificate),
                                    str(PLC/'Spikes/S12_TypeMap/simulator.ps1'), str(stop)],
                                   cwd=HERE.parent/'Manifest', env=environment, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic()+120
            while time.monotonic() < deadline:
                if gateway.poll() is not None: raise RuntimeError('gateway exited before readiness')
                if b'bench-ready' in (out/'gateway.log').read_bytes(): break
                time.sleep(.2)
            else: raise TimeoutError('gateway readiness')
            with (out/'flutter.log').open('xb') as result_log:
                result = subprocess.run([str(flutter), 'test', '--no-pub', '--run-skipped', '-t', 'live',
                                         '--concurrency=1', 'test/live_tia_manifest_test.dart'],
                                        cwd=PLC.parents[1]/'HMI', env=environment, stdout=result_log,
                                        stderr=subprocess.STDOUT, timeout=600)
            assert result.returncode == 0, 'live HMI test failed; see flutter.log'
        finally:
            stop.write_bytes(b'stop\n')
            try: gateway.wait(timeout=45)
            except subprocess.TimeoutExpired:
                gateway.terminate(); gateway.wait(timeout=15)
    record = dict(complete=True, certificate_sha256=api.fingerprint, status=guard())
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n', encoding='ascii')
    print(json.dumps(record))


if __name__ == '__main__':
    run(Path(sys.argv[1]))

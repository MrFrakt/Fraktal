"""Existing generic HMI over the production session; fixed isolated line bench."""
import json
import os
from pathlib import Path
import subprocess
import sys

from owner_target import WORK, TIA, guard, original
sys.path.insert(0, str(TIA/'tools'))
from tia_webapi import WebApi


def run(output):
    if output.resolve().parent != WORK.resolve(): raise ValueError('fixed private evidence directory required')
    before = original()
    guard()
    output.mkdir(exist_ok=False)
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/LineOwner_20261016.webapi.pin'
    api = WebApi('169.254.212.53', pin, False)
    (output/'certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
    api.conn.close()
    env = dict(os.environ, FRAKTAL_TIA_LINE_LIVE='1', FRAKTAL_TIA_LINE_OUTPUT=str(output))
    with (output/'flutter.log').open('xb') as log:
        result = subprocess.run([r'C:\Users\Siemens\Documents\FlutterSdk\flutter\bin\flutter.bat',
                                 'test', '--no-pub', '--run-skipped', '-t', 'live', '--concurrency=1',
                                 'test/live_tia_line_test.dart'], cwd=TIA.parents[1]/'HMI', env=env,
                                stdout=log, stderr=subprocess.STDOUT, timeout=660)
    after = original()
    (output/'guard.json').write_text(json.dumps(dict(before=before, after=after,
        certificate_sha256=api.fingerprint, exit_code=result.returncode), indent=2)+'\n', encoding='ascii')
    if after != before: raise RuntimeError('original Fraktal changed')
    if result.returncode: raise RuntimeError('live HMI failed; see flutter.log')
    print(json.dumps(dict(result='PASS',status=guard())))


if __name__ == '__main__': run(Path(sys.argv[1]))

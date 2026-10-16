"""Fixed isolated production-line target; never substitutes the saved Fraktal CPU."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from run_bench import DRIVER, DRIVER_SHA256, powershell

HERE = Path(__file__).resolve().parent
TIA = HERE.parents[1]
PROFILE_PATH = HERE/'bench_owner.json'
PROFILE = json.loads(PROFILE_PATH.read_bytes())
HELPER = TIA/'tools/Invoke-TiaIsolatedBench.ps1'
WORK = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Line_Owner_20261016'
PROJECT = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Line_Owner_Runtime_20261016/FrkS12/FrkS12.ap20'


def action(name):
    result, rows = powershell(HELPER, '-Profile', str(PROFILE_PATH), '-Action', name)
    if result.returncode: raise RuntimeError('isolated line target action failed: '+result.stdout)
    return rows[-1]


def guard():
    status = action('status')
    if status['state'] != 'Run' or status['cpu'] != 'CPU1516': raise RuntimeError('line owner bench must be RUN/CPU1516')
    return status


def original():
    result, rows = powershell(TIA/'Spikes/S12_TypeMap/simulator.ps1', '-Action', 'status')
    if result.returncode: raise RuntimeError('cannot record original Fraktal state')
    return {k: v for k,v in rows[-1].items() if k != 't'}


def provision_web(output):
    """Give only the disposable CPU the existing process-data web credential."""
    if output.resolve().parent != WORK.resolve(): raise ValueError('fixed private evidence directory required')
    if hashlib.sha256(DRIVER.read_bytes()).hexdigest() != DRIVER_SHA256: raise ValueError('approved driver differs')
    if not os.environ.get('FRAKTAL_TIA_WEB_PASSWORD'): raise ValueError('DPAPI credential wrapper required')
    before = original()
    guard()
    commands = ['open-project --path "'+str(PROJECT)+'"',
                'webserver-user --plc PLC_1 --name fraktal --permissions ReadTagStatus,ModifyTagStatus --password-env FRAKTAL_TIA_WEB_PASSWORD',
                'save', 'compile --plc PLC_1 --hw',
                'download --plc PLC_1 --pc-interface "Siemens PLCSIM Virtual Ethernet Adapter" --pc-number 1 --target "1 X1" --confirm-target '+PROFILE['address']+' --user-management keep --trust-plc PLC_1', 'save']
    plan = output.with_suffix('.plan')
    with plan.open('xb') as stream: stream.write(('\n'.join(commands)+'\n').encode('ascii'))
    with output.open('xb') as stream:
        stream.write((json.dumps(dict(original_before=before,bench=guard(),driver_sha256=DRIVER_SHA256))+'\n').encode('ascii'));stream.flush()
        result = subprocess.run([str(DRIVER), 'plan', str(plan)], stdout=stream, stderr=subprocess.STDOUT)
        after = original()
        stream.write((json.dumps(dict(original_after=after,exit_code=result.returncode))+'\n').encode('ascii'))
    if after != before: raise RuntimeError('original Fraktal state changed')
    if result.returncode: raise RuntimeError('web provisioning failed; no replay')
    action('run')


def download(revision):
    if revision.resolve().parent != WORK.resolve(): raise ValueError('fixed isolated workspace required')
    if not PROJECT.is_file() or hashlib.sha256(DRIVER.read_bytes()).hexdigest() != DRIVER_SHA256:
        raise ValueError('saved copy or approved driver differs')
    verified=json.loads((revision/'owner_verified_private.json').read_bytes())
    if not all(verified.get(name) for name in ('sources','interfaces','data_interfaces')):
        raise ValueError('native read-back verification required before download')
    rows = [json.loads(line) for line in (revision/'build.log').read_text(encoding='utf-8-sig').splitlines() if line.startswith('{')]
    compiles = [r for r in rows if r.get('event') == 'compile']
    if not compiles or any(r['errors'] or r['warnings'] for r in compiles): raise ValueError('clean program compile required')
    before = original()
    bench = action('status')
    commands = ['open-project --path "'+str(PROJECT)+'"', 'compile --plc PLC_1',
                'download --plc PLC_1 --pc-interface "Siemens PLCSIM Virtual Ethernet Adapter" --pc-number 1 --target "1 X1" --confirm-target '+PROFILE['address']+' --user-management keep --trust-plc PLC_1', 'save']
    plan = revision/'isolated_download.plan'
    with plan.open('xb') as stream: stream.write(('\n'.join(commands)+'\n').encode('ascii'))
    with (revision/'download.log').open('xb') as stream:
        stream.write((json.dumps(dict(driver_sha256=DRIVER_SHA256,bench=bench,original_before=before))+'\n').encode('ascii'));stream.flush()
        result = subprocess.run([str(DRIVER), 'plan', str(plan)], stdout=stream, stderr=subprocess.STDOUT)
    after = original()
    with (revision/'download_guard.json').open('x',encoding='ascii',newline='\n') as stream:
        json.dump(dict(before=before,after=after,exit_code=result.returncode),stream,indent=2);stream.write('\n')
    if after != before: raise RuntimeError('original Fraktal state changed')
    if result.returncode: raise RuntimeError('download failed; no replay')
    action('run')


if __name__ == '__main__':
    import sys
    if sys.argv[1] == '--provision-web': provision_web(Path(sys.argv[2]))
    else: download(Path(sys.argv[1]))

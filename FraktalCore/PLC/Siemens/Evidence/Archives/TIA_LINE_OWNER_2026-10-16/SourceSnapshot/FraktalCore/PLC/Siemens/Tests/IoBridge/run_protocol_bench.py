"""Run only the fixed isolated native-protocol CPU, preserving Fraktal.

Start protocol_simulator.ps1 -Action host first. This deliberately has no
physical-target option and cannot download the I/O bridge to the real 1214C.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
TIA = HERE.parents[1]
DRIVER = TIA / 'tools/TiaCli/bin/candidate_structure_examples/Fraktal.Tia.Cli.exe'
DRIVER_SHA256 = 'ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74'


def owner_state(row):
    # The SDK status emitter timestamps every observation; that timestamp is
    # not part of the controller state that must remain unchanged.
    return {key: value for key, value in row.items() if key != 't'}


def powershell(script, action, owner=False):
    env = dict(os.environ)
    if owner: env['FRAKTAL_TIA_SIM_INSTANCE'] = 'Fraktal'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), '-Action', action],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return result, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('--observe', action='store_true', help='read existing native results only; never download/replay')
    args = parser.parse_args()
    work = args.work.resolve()
    expected_work = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaSpikes/Press_IoBridge_20261015'
    if work != expected_work.resolve(): raise ValueError('fixed protocol work directory required')
    project = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/IoBridge_Protocol_Qualified_20261015/FrkS12/FrkS12.ap20'
    if not project.is_file(): raise ValueError('qualified offline protocol project missing')
    if hashlib.sha256(DRIVER.read_bytes()).hexdigest() != DRIVER_SHA256: raise ValueError('approved driver hash differs')
    owner_script = TIA / 'Spikes/S12_TypeMap/simulator.ps1'
    owner, owner_rows = powershell(owner_script, 'status', True)
    if owner.returncode: raise RuntimeError('cannot record owner state: ' + owner.stdout)
    before = owner_rows[-1]
    status, rows = powershell(HERE / 'protocol_simulator.ps1', 'status')
    if status.returncode: raise RuntimeError('isolated bench preflight failed: ' + status.stdout)
    target = rows[-1]
    if target['name'] != 'FrkIoBridgeTest' or target['address'] != '169.254.212.51' or any(target[k] for k in ('ie1', 'ie2', 'ie3')):
        raise ValueError('protocol target differs')
    if args.observe:
        result, rows = powershell(HERE / 'protocol_simulator.ps1', 'read')
        after_result, after_rows = powershell(owner_script, 'status', True)
        data = {'mode': 'read-only-observation', 'owner_before': before,
                'owner_after': after_rows[-1], 'exit_code': result.returncode,
                'rows': rows, 'output': result.stdout}
        with (work / 'protocol_observed.json').open('x', encoding='utf-8', newline='\n') as stream: json.dump(data, stream, indent=2)
        if after_result.returncode or owner_state(after_rows[-1]) != owner_state(before): raise RuntimeError('owner state changed')
        if result.returncode: raise RuntimeError('native protocol assertions failed')
        print(json.dumps(rows[-1]))
        return
    build_log = work / 'protocol05_build.log'
    compiled = [json.loads(line) for line in build_log.read_text(encoding='utf-8-sig').splitlines() if line.startswith('{')]
    compiled = [row for row in compiled if row.get('event') == 'compile']
    if len(compiled) != 2 or any(row['errors'] or row['warnings'] for row in compiled): raise ValueError('clean software/hardware compile required')
    plan = work / 'protocol_download.plan'
    lines = ['open-project --path "' + str(project) + '"', 'compile --plc PLC_1',
             'download --plc PLC_1 --pc-interface "Siemens PLCSIM Virtual Ethernet Adapter" --pc-number 1 --target "1 X1" --confirm-target 169.254.212.51 --user-management keep --trust-plc PLC_1', 'save']
    with plan.open('xb') as stream: stream.write(('\n'.join(lines) + '\n').encode('ascii'))
    with (work / 'protocol_download.log').open('xb') as stream:
        stream.write((json.dumps({'event': 'driver', 'sha256': DRIVER_SHA256, 'target': target, 'owner_before': before}) + '\n').encode('ascii')); stream.flush()
        result = subprocess.run([str(DRIVER), 'plan', str(plan)], stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode: raise RuntimeError('protocol download failed; no replay')
    result, rows = powershell(HERE / 'protocol_simulator.ps1', 'run')
    if result.returncode: raise RuntimeError('protocol bench RUN failed: ' + result.stdout)
    observations = []
    for _ in range(4):
        result, rows = powershell(HERE / 'protocol_simulator.ps1', 'read')
        observations.append({'exit_code': result.returncode, 'rows': rows, 'output': result.stdout})
        if not result.returncode: break
        time.sleep(.5)
    after_result, after_rows = powershell(owner_script, 'status', True)
    data = {'driver_sha256': DRIVER_SHA256, 'owner_before': before, 'owner_after': after_rows[-1], 'reads': observations}
    with (work / 'protocol_results.json').open('x', encoding='utf-8', newline='\n') as stream: json.dump(data, stream, indent=2)
    if after_result.returncode or owner_state(after_rows[-1]) != owner_state(before): raise RuntimeError('owner state changed')
    if result.returncode: raise RuntimeError('native protocol assertions failed; see protocol_results.json')
    print(json.dumps(rows[-1]))


if __name__ == '__main__': main()

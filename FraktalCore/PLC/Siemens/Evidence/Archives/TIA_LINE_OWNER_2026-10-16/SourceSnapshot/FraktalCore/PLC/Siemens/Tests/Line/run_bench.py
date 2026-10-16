"""Download/read only the isolated Line bench; guard the saved Fraktal CPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from make_fixture import build

HERE = Path(__file__).resolve().parent
TIA = HERE.parents[1]
DRIVER = TIA/'tools/TiaCli/bin/candidate_structure_examples/Fraktal.Tia.Cli.exe'
DRIVER_SHA256 = 'ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74'


def powershell(script, *args):
    environment = dict(os.environ, FRAKTAL_TIA_SIM_INSTANCE='Fraktal')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=environment)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return result, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revision', type=Path)
    parser.add_argument('--observe', action='store_true')
    args = parser.parse_args()
    root = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Line_Kernel_20261015'
    revision = args.revision.resolve()
    if revision.parent != root.resolve(): raise ValueError('fixed Line bench directory required')
    project = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Line_Kernel_20261015/FrkS12/FrkS12.ap20'
    if not project.is_file(): raise ValueError('isolated project missing')
    if hashlib.sha256(DRIVER.read_bytes()).hexdigest() != DRIVER_SHA256: raise ValueError('approved driver hash differs')
    sources, labels = build()
    actual = {p.name for p in (revision/'sources').iterdir() if p.suffix in ('.scl', '.udt', '.db')}
    if actual != set(sources): raise ValueError('compiled source inventory differs')
    for name, text in sources.items():
        if (revision/'sources'/name).read_bytes() != text.encode('ascii'): raise ValueError('fixture changed since compile: '+name)
    owner_script = TIA/'Spikes/S12_TypeMap/simulator.ps1'
    helper = TIA/'tools/Invoke-TiaIsolatedBench.ps1'
    profile_args = ('-Profile', str(HERE/'bench.json'))
    owner, rows = powershell(owner_script, '-Action', 'status')
    if owner.returncode: raise RuntimeError('cannot record owner state: '+owner.stdout)
    before = rows[-1]
    result, rows = powershell(helper, *profile_args, '-Action', 'status')
    if result.returncode: raise RuntimeError('isolated bench preflight failed: '+result.stdout)
    bench = rows[-1]
    profile = json.loads((HERE/'bench.json').read_bytes())
    if bench['name'] != profile['name'] or bench['address'] != profile['address'] or any(bench[n] for n in ('ie1', 'ie2', 'ie3')):
        raise ValueError('isolated bench differs')
    if not args.observe:
        compiled = [json.loads(line) for line in (revision/'build.log').read_text(encoding='utf-8-sig').splitlines() if line.startswith('{')]
        compiles = [row for row in compiled if row.get('event') == 'compile']
        if not compiles or any(row['errors'] or row['warnings'] for row in compiles): raise ValueError('clean compile required')
        plan = revision/'isolated_download.plan'
        commands = ['open-project --path "'+str(project)+'"', 'compile --plc PLC_1',
                    'download --plc PLC_1 --pc-interface "Siemens PLCSIM Virtual Ethernet Adapter" --pc-number 1 --target "1 X1" --confirm-target '+profile['address']+' --user-management keep --trust-plc PLC_1', 'save']
        with plan.open('xb') as stream: stream.write(('\n'.join(commands)+'\n').encode('ascii'))
        with (revision/'download.log').open('xb') as stream:
            stream.write((json.dumps(dict(driver_sha256=DRIVER_SHA256, target=bench, owner_before=before))+'\n').encode('ascii')); stream.flush()
            result = subprocess.run([str(DRIVER), 'plan', str(plan)], stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode: raise RuntimeError('download failed; no replay')
        result, _ = powershell(helper, *profile_args, '-Action', 'run')
        if result.returncode: raise RuntimeError('bench RUN failed: '+result.stdout)
    result, rows = powershell(helper, *profile_args, '-Action', 'read', '-ExpectedChecks', str(len(labels)))
    after, after_rows = powershell(owner_script, '-Action', 'status')
    record = dict(mode='observe' if args.observe else 'download', owner_before=before,
                  owner_after=after_rows[-1] if after_rows else None, rows=rows,
                  output=result.stdout, exit_code=result.returncode)
    output = revision/('observed.json' if args.observe else 'results.json')
    with output.open('x', encoding='utf-8', newline='\n') as stream: json.dump(record, stream, indent=2); stream.write('\n')
    state = lambda row: {k: v for k, v in row.items() if k != 't'}
    if after.returncode or not after_rows or state(after_rows[-1]) != state(before): raise RuntimeError('saved Fraktal state changed')
    if result.returncode: raise RuntimeError('native Line assertions failed: '+result.stdout)
    print(json.dumps(rows[-1]))


if __name__ == '__main__': main()

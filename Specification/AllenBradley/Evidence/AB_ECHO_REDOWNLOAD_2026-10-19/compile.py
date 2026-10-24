"""Offline v38 native build + actual read-back for the regenerated current-source image."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
OUT = Path('C:/work/fraktal-ab-echo-20261019')
sys.path.insert(0, str(TOOLS))
import fraktal_ab_readback as readback
import fraktal_ab_sdk_log_gate as gate
source = OUT/'genealogy_current.L5X'
expected = '91BF67C9101EAE863CF29C1A9DF6413D7256AB056D985394587F0183AA525714'
if hashlib.sha256(source.read_bytes()).hexdigest().upper() != expected:
    raise SystemExit('source hash guard refused')
probe = TOOLS/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
rows = []
for label, target in [('echo', 'EchoController'), ('physical', 'PhysicalController')]:
    output = OUT/(label + '_readback.L5X')
    run = subprocess.run([str(probe), '--build-readback', str(source), str(output), target],
                         capture_output=True, timeout=600)
    log = (run.stdout + run.stderr)
    (OUT/(label + '_build.log')).write_bytes(log)
    audit = gate.audit_log(log.decode('utf-8', errors='replace'), ('Build',), require_clean_import=True)
    if run.returncode:
        raise SystemExit(f'{label} native build failed: {run.returncode}')
    compared = readback.compare(source, output)
    with (OUT/(label + '_compare.json')).open('x', encoding='utf-8') as stream:
        json.dump(compared, stream, indent=2)
    rows.append(dict(target=target, buildClean=audit['Clean'], equivalent=compared['Equivalent'],
                     executableBodies=compared['ExecutableBodies'],
                     initialValues=compared['AuthoredInitialValues']))
    if not compared['Equivalent'] or not audit['Clean']:
        raise SystemExit(json.dumps(rows))
with (OUT/'compiled.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(sourceSha256=expected, rows=rows), stream, indent=2)
print(json.dumps(rows))

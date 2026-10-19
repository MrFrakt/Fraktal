import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path(__file__).parent
DEST = ROOT/'Specification/AllenBradley/Evidence/AB_HOST_RECOVERY_2026-10-18'
DEST.mkdir(exist_ok=False)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def capture(name, command):
    result = subprocess.run(command, capture_output=True, timeout=60)
    (WORK/name).write_bytes(result.stdout)
    if result.returncode:
        raise RuntimeError((name, result.returncode, result.stderr.decode(errors='replace')))

capture('final_identity.json', ['python', 'C:/work/fraktal-echo-deploy-20261018/guard_echo.py'])
capture('final_echo.json', ['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe', 'inspect'])
files = ['live_batch.json', 'recovery.json', 'generation.json', 'final_identity.json', 'final_echo.json',
         'live.events.sqlite', 'live.cursor.json', 'after_sink.sqlite', 'after_sink.cursor.json',
         'before_replace.sqlite', 'before_replace.cursor.json', 'ab_tests_01.log', 'focused_tests_01.log',
         'root_tests_01.log', 'spec_gate_01.log', 'contracts_gate_01.log', 'consistency_gate_01.log',
         'prove_recovery.py', 'prove_generation.py', 'package_evidence.py']
for name in files:
    shutil.copy2(WORK/name, DEST/name)
sources = ['FraktalCore/PLC/Allen-Bradley/tools/'+name for name in
           ('fraktal_ab_host_events.py', 'fraktal_ab_host_sink.py',
            'test_fraktal_ab_host_events.py', 'test_fraktal_ab_host_sink.py')]
bindings = []
for name in sources:
    path = ROOT/name
    copied = DEST/'Sources'/name
    copied.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, copied)
    bindings.append(dict(path=name, sha256=sha(path)))
artifacts = [dict(path=p.relative_to(DEST).as_posix(), sha256=sha(p), bytes=p.stat().st_size)
             for p in sorted(DEST.rglob('*')) if p.is_file()]
manifest = dict(schema='fraktal.ab.host-recovery-evidence-manifest', version=1,
    baselineCommit='a29a5282cf21fcba3764ee0b4d6a8dbca14ed3c0', controllerWrites=0,
    abTests=1839, focusedTests=45, rootTests=74, liveChecks=24,
    nativeAlarmSubscriberQualified=False, unixNativeProcessQualified=False,
    sourceBindings=bindings, artifacts=artifacts)
with (DEST/'manifest.json').open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(files=len(artifacts), bytes=sum(p['bytes'] for p in artifacts),
                      manifestSha256=sha(DEST/'manifest.json'))))

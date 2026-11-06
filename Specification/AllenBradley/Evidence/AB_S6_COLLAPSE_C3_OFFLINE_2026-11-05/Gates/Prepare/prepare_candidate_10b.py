"""The access audits, ACD and Capacity for source 10, which prepare_candidate_10 left unfinished.

prepare_candidate_10 ran every build, read-back and SDK-log audit with exit 0.
Its access audits exited 1 on both targets: audit_access_04 expects the S2
record's public tags, which include the six module context tags C3 removes by
design ("declared public but not present"). audit_access_05 is the same audit
without them. This reruns the audits on the same read-backs, then the steps
the first script skipped, on the exact source 10 bytes.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

W = Path(__file__).parent
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
PREPARE = 'C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe'
PY = sys.executable
source, acd, review = W / 's6_collapse_10.L5X', W / 's6_collapse_10.ACD', W / 'capacity_review_10.ACD'
first = json.loads((W / 'prepare_candidate_10.json').read_text(encoding='utf-8'))
exits = {}


def run(label, *args):
    exits[label] = subprocess.run([PY, str(W / 'run_logged.py'), label, *map(str, args)], cwd=R).returncode
    return exits[label]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert sha(source) == first['sourceSha256'] and not acd.exists()
assert all(v == 0 for k, v in first['exits'].items() if not k.startswith('access_'))
pins = dict(sourceSha256=first['sourceSha256'])
for target in ('EchoController', 'PhysicalController'):
    run(f'access_{target}_10b', PY, W / 'audit_access_05.py', W / f'{target}_readback_10.L5X',
        W / f'access_{target}_10b.json')
if all(v == 0 for v in exits.values()):
    run('prepare_acd_10', PREPARE, source, acd, W / 'prepared_readback_10.L5X')
    run('prepared_compare_10', PY, T / 'fraktal_ab_readback.py', source, W / 'prepared_readback_10.L5X')
    if all(v == 0 for v in exits.values()):
        pins['acdSha256'] = sha(acd)
        shutil.copyfile(acd, review)
        run('capacity_10', PY, T / 'fraktal_ab_studio_capacity.py', '--acd', review, '--expect-sha256',
            pins['acdSha256'], '--output', W / 'capacity_auto_10.json', '--capture-output', W / 'capacity_capture_10.json')
        assert sha(acd) == pins['acdSha256']
result = dict(passed=all(v == 0 for v in exits.values()) and 'acdSha256' in pins, exits=exits, **pins,
              supersededAudits=['access_EchoController_10', 'access_PhysicalController_10'],
              controllerAccess=False, downloads=0)
with (W / 'prepare_candidate_10b.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)

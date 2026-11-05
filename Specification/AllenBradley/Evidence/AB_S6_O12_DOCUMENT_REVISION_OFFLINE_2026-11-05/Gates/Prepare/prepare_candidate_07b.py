"""The ACD and Capacity steps for source 07, which prepare_candidate_07 skipped.

prepare_candidate_07 ran every build, read-back and SDK-log audit with exit 0.
Its one non-zero exit was `access_press_EchoController_07`: audit_access_03 is
written for the V6.11 genealogy declaration (it expects the host-service
ingress), and the press canonical image has none, so it was the wrong audit
for that image, not a finding. The genealogy source's own access audits passed
on both targets. This runs the skipped steps on the exact source 07 bytes.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

W = Path(__file__).parent
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
PREPARE = 'C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe'
PY = sys.executable
source, acd, review = W / 's6_host_07.L5X', W / 's6_host_07.ACD', W / 'capacity_review_07.ACD'
first = json.loads((W / 'prepare_candidate_07.json').read_text(encoding='utf-8'))
exits = {}


def run(label, *args):
    exits[label] = subprocess.run([PY, str(W / 'run_logged.py'), label, *map(str, args)], cwd=R).returncode
    return exits[label]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert sha(source) == first['sourceSha256'] and not acd.exists()
assert all(v == 0 for k, v in first['exits'].items() if k != 'access_press_EchoController_07')
pins = dict(sourceSha256=first['sourceSha256'])
run('prepare_acd_07', PREPARE, source, acd, W / 'prepared_readback_07.L5X')
run('prepared_compare_07', PY, T / 'fraktal_ab_readback.py', source, W / 'prepared_readback_07.L5X')
if all(v == 0 for v in exits.values()):
    pins['acdSha256'] = sha(acd)
    shutil.copyfile(acd, review)
    run('capacity_07', PY, T / 'fraktal_ab_studio_capacity.py', '--acd', review, '--expect-sha256', pins['acdSha256'],
        '--output', W / 'capacity_auto_07.json', '--capture-output', W / 'capacity_capture_07.json')
    assert sha(acd) == pins['acdSha256']
result = dict(passed=all(v == 0 for v in exits.values()) and 'acdSha256' in pins, exits=exits, **pins,
              misappliedAudit='access_press_EchoController_07', controllerAccess=False, downloads=0)
with (W / 'prepare_candidate_07b.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)

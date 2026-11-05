"""Offline preparation of the S6 V6.11 candidate, third source (no controller access).

Source 01 failed both v38 builds (a BOOL comparison operand); 02 built but
its revision guard refused the baseline's documents. 03 carries both fixes.
Every step runs and is logged; the result lists each exit.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

W = Path(__file__).parent
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
SDK = T / 'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
PREPARE = 'C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe'
PY = sys.executable
source, acd, review = W / 's6_host_03.L5X', W / 's6_host_03.ACD', W / 'capacity_review_03.ACD'
exits = {}


def run(label, *args):
    exits[label] = subprocess.run([PY, str(W / 'run_logged.py'), label, *map(str, args)], cwd=R).returncode
    return exits[label]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert not source.exists() and not acd.exists()
run('generate_03', PY, T / 'fraktal_ab_generate.py', 'C:/work/echo38_5580_seed.L5X', source,
    '--declaration', 'fraktal_ab_genealogy_s6_host_demo')
pins = dict(sourceSha256=sha(source))
run('bool_scan_03', PY, W / 'scan_bool_operands_03.py')
for target in ('EchoController', 'PhysicalController'):
    output = W / f'{target}_readback_03.L5X'
    run(f'build_{target}_03', SDK, '--build-readback', source, output, target)
    run(f'readback_{target}_03', PY, T / 'fraktal_ab_readback.py', source, output)
    run(f'audit_{target}_03', PY, T / 'fraktal_ab_sdk_log_gate.py', W / f'build_{target}_03.log',
        '--require', 'Open project', '--require', 'Build', '--require', 'Save As')
    run(f'access_{target}_03', PY, W / 'audit_access_02.py', output, W / f'access_{target}_03.json')
if all(v == 0 for v in exits.values()):
    run('prepare_acd_03', PREPARE, source, acd, W / 'prepared_readback_03.L5X')
    run('prepared_compare_03', PY, T / 'fraktal_ab_readback.py', source, W / 'prepared_readback_03.L5X')
    pins['acdSha256'] = sha(acd)
    shutil.copyfile(acd, review)
    run('capacity_03', PY, T / 'fraktal_ab_studio_capacity.py', '--acd', review, '--expect-sha256', pins['acdSha256'],
        '--output', W / 'capacity_auto_03.json', '--capture-output', W / 'capacity_capture_03.json')
    assert sha(acd) == pins['acdSha256']
result = dict(passed=all(v == 0 for v in exits.values()) and 'acdSha256' in pins, exits=exits, **pins,
              controllerAccess=False, downloads=0)
with (W / 'prepare_candidate_03.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)

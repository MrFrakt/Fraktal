"""Offline preparation of source 07: O12's document revision (WP6.6 C0b). No controller access.

Source 06 was the first SessionPermits fix. 07 changes only the document
revision: every document producer and the revision guard now use the O12
identity, and each declaration accepts exactly its recorded pre-collapse
revisions. The genealogy guard grows from 122 to 123 terms (three nested
groups); the press canonical image's from 5 to 6 (two chained groups), so it
is built on the Echo target too. Every step runs and is logged.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

W = Path(__file__).parent
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
SDK = T / 'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
PREPARE = 'C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe'
SEED = 'C:/work/echo38_5580_seed.L5X'
PY = sys.executable
source, acd, review = W / 's6_host_07.L5X', W / 's6_host_07.ACD', W / 'capacity_review_07.ACD'
press = W / 'press_canonical_07.L5X'
exits = {}


def run(label, *args):
    exits[label] = subprocess.run([PY, str(W / 'run_logged.py'), label, *map(str, args)], cwd=R).returncode
    return exits[label]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert not source.exists() and not acd.exists() and not press.exists()
run('generate_07', PY, T / 'fraktal_ab_generate.py', SEED, source, '--declaration', 'fraktal_ab_genealogy_s6_host_demo')
run('generate_press_07', PY, T / 'fraktal_ab_generate.py', SEED, press, '--declaration', 'fraktal_ab_press_canonical_echo38')
pins = dict(sourceSha256=sha(source), pressSha256=sha(press))
run('bool_scan_07', PY, T / 'fraktal_ab_st_bool_operands.py', source)
run('bool_scan_press_07', PY, T / 'fraktal_ab_st_bool_operands.py', press)
builds = [('EchoController', source, ''), ('PhysicalController', source, ''), ('EchoController', press, 'press_')]
for target, image, prefix in builds:
    output = W / f'{prefix}{target}_readback_07.L5X'
    run(f'build_{prefix}{target}_07', SDK, '--build-readback', image, output, target)
    run(f'readback_{prefix}{target}_07', PY, T / 'fraktal_ab_readback.py', image, output)
    run(f'audit_{prefix}{target}_07', PY, T / 'fraktal_ab_sdk_log_gate.py', W / f'build_{prefix}{target}_07.log',
        '--require', 'Open project', '--require', 'Build', '--require', 'Save As')
    run(f'access_{prefix}{target}_07', PY, W / 'audit_access_03.py', output, W / f'access_{prefix}{target}_07.json')
if all(v == 0 for v in exits.values()):
    run('prepare_acd_07', PREPARE, source, acd, W / 'prepared_readback_07.L5X')
    run('prepared_compare_07', PY, T / 'fraktal_ab_readback.py', source, W / 'prepared_readback_07.L5X')
    pins['acdSha256'] = sha(acd)
    shutil.copyfile(acd, review)
    run('capacity_07', PY, T / 'fraktal_ab_studio_capacity.py', '--acd', review, '--expect-sha256', pins['acdSha256'],
        '--output', W / 'capacity_auto_07.json', '--capture-output', W / 'capacity_capture_07.json')
    assert sha(acd) == pins['acdSha256']
result = dict(passed=all(v == 0 for v in exits.values()) and 'acdSha256' in pins, exits=exits, **pins,
              controllerAccess=False, downloads=0)
with (W / 'prepare_candidate_07.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)

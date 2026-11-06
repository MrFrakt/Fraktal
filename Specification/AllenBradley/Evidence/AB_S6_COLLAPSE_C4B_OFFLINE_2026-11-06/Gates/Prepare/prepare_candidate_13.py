"""C4b offline preparation, source 13. The reader change must regenerate the
C4a PLC images byte for byte, and repeat v38 build/readback and Capacity.
No controller access.
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
source, acd, review = W / 's6_collapse_13.L5X', W / 's6_collapse_13.ACD', W / 'capacity_review_13.ACD'
press = W / 'press_collapse_13.L5X'
legacy = {'fraktal_ab_genealogy_s6_host_demo': ('s6_host_legacy_13.L5X', 's6_host_07.L5X'),
          'fraktal_ab_press_canonical_echo38': ('press_canonical_legacy_13.L5X', 'press_canonical_07.L5X')}
exits = {}


def run(label, *args):
    exits[label] = subprocess.run([PY, str(W / 'run_logged.py'), label, *map(str, args)], cwd=R).returncode
    return exits[label]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert not source.exists() and not acd.exists() and not press.exists()
run('generate_13', PY, T / 'fraktal_ab_generate.py', SEED, source, '--declaration', 'fraktal_ab_genealogy_s6_collapse_demo')
run('generate_press_13', PY, T / 'fraktal_ab_generate.py', SEED, press, '--declaration', 'fraktal_ab_press_s6_collapse_echo38')
pins = dict(sourceSha256=sha(source), pressSha256=sha(press), legacy={})
for declaration, (output, before) in legacy.items():
    run(f'regenerate_{declaration}_13', PY, T / 'fraktal_ab_generate.py', SEED, W / output, '--declaration', declaration)
    pins['legacy'][declaration] = sha(W / output)
    exits[f'legacy_identical_{declaration}_13'] = 0 if sha(W / output) == sha(W / before) else 1
run('bool_scan_13', PY, T / 'fraktal_ab_st_bool_operands.py', source)
run('bool_scan_press_13', PY, T / 'fraktal_ab_st_bool_operands.py', press)
for target, image, prefix, audit in (('EchoController', source, '', True), ('PhysicalController', source, '', True),
                                     ('EchoController', press, 'press_', False)):
    output = W / f'{prefix}{target}_readback_13.L5X'
    run(f'build_{prefix}{target}_13', SDK, '--build-readback', image, output, target)
    run(f'readback_{prefix}{target}_13', PY, T / 'fraktal_ab_readback.py', image, output)
    run(f'audit_{prefix}{target}_13', PY, T / 'fraktal_ab_sdk_log_gate.py', W / f'build_{prefix}{target}_13.log',
        '--require', 'Open project', '--require', 'Build', '--require', 'Save As')
    if audit:
        run(f'access_{prefix}{target}_13', PY, W / 'audit_access_06.py', output, W / f'access_{prefix}{target}_13.json')
if all(v == 0 for v in exits.values()):
    run('prepare_acd_13', PREPARE, source, acd, W / 'prepared_readback_13.L5X')
    run('prepared_compare_13', PY, T / 'fraktal_ab_readback.py', source, W / 'prepared_readback_13.L5X')
    pins['acdSha256'] = sha(acd)
    shutil.copyfile(acd, review)
    run('capacity_13', PY, T / 'fraktal_ab_studio_capacity.py', '--acd', review, '--expect-sha256', pins['acdSha256'],
        '--output', W / 'capacity_auto_13.json', '--capture-output', W / 'capacity_capture_13.json')
    assert sha(acd) == pins['acdSha256']
result = dict(passed=all(v == 0 for v in exits.values()) and 'acdSha256' in pins, exits=exits, **pins,
              controllerAccess=False, downloads=0)
with (W / 'prepare_candidate_13.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)

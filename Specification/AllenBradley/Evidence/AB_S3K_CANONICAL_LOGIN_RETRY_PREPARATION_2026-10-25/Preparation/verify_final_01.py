"""Audit offline outputs and recheck the restored baseline without writes."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

W = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'
R = W.parent / 'retry_login_01'
PRIOR = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
sys.path.insert(0, str(T))
from fraktal_ab_sdk_log_gate import audit_log

load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()

audits = {}
for label in ('native_EchoController_02', 'native_PhysicalController_02', 'prepare_acd_02'):
    audit = audit_log((W / (label + '.log')).read_text(), ('Open project', 'Build', 'Save As'), True)
    assert audit['Clean'], (label, audit)
    audits[label] = audit
with (W / 'sdk_audits_01.json').open('x') as out:
    json.dump(dict(passed=True, audits=audits), out, indent=2)

for label in ('ab_suite_01', 'final_root_tests_01', 'final_spec_01', 'final_contracts_01',
              'final_consistency_01', 'final_whitespace_01', 'login_tests_green_01', 'compatibility_01',
              'replay_prior_01', 'retry_checks_01', 'retry_helper_build_01', 'offline_workflow_01'):
    assert load(W / (label + '_exit.json'))['exitCode'] == 0, label
for label in ('readback_EchoController_02', 'readback_PhysicalController_02', 'prepared_compare_02'):
    assert load(W / (label + '.log'))['Equivalent'], label
for label in ('access_Echo_02', 'access_Physical_02'):
    assert load(W / (label + '.json'))['passed'], label
assert 'Ran 2295 tests' in (W / 'ab_suite_01.log').read_text()
assert 'Ran 74 tests' in (W / 'final_root_tests_01.log').read_text()
assert load(W / 'accepted_images_02.json')['images'] == 12
assert load(W / 'capture_replay_01.json')['captures'] == 1431
assert load(W / 'source_delta_01.json')['changedRoutines'] == ['FRK_PressHmiMailbox']
assert sha(R / 's3k_command_a.ACD') == load(W / 'capacity_auto_02.json')['CanonicalSha256']
assert sha(R / 's3k_command_a.L5X') == 'B543336202821F95BC41A5A51441E86021F1BA9EFF28D42FABCD1AA83D7C782A'
assert not (R / 'authorization.json').exists() and not (R / 'session_started.json').exists()

for label, args in [
    ('baseline_guard_final_01', [sys.executable, R / 'scripts/guard_echo.py']),
    ('baseline_state_final_01', [sys.executable, PRIOR / 'final_checks.py', W / 'baseline_state_final_01.json']),
    ('baseline_preflight_final_01', [sys.executable, PRIOR / 'scripts/preflight.py', '--verify-only']),
]:
    subprocess.run([sys.executable, str(W / 'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)
assert load(W / 'baseline_state_final_01.json')['passed']
dump_root = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
assert not list(dump_root.rglob('*.dmp'))

# Freeze the runnable helper, gates and all source files used by this stage.
prior_bindings = load(W.parent / 'download_01/runtime_source_bindings_01.json')['sha256']
paths = {ROOT / name for name in prior_bindings}
paths.update(T.glob('*.py'))
paths.update(p for p in R.rglob('*') if p.is_file() and not any(x in ('bin', 'obj', '__pycache__') for x in p.relative_to(R).parts))
paths.update(R / 'session/bin/Debug/net8.0/win-x86' / ('S3kSession' + suffix) for suffix in ('.dll', '.exe'))
bindings = dict(gatesPassed=True, controllerChangesAuthorized=False, preparedAcdSha256=sha(R / 's3k_command_a.ACD'),
                sha256={p.as_posix(): sha(p) for p in sorted(paths) if p.suffix.lower() != '.acd'})
with (R / 'source_bindings.json').open('x') as out:
    json.dump(bindings, out, indent=2)
with (W / 'final_preparation_checks_01.json').open('x') as out:
    json.dump(dict(passed=True, abTests=2295, rootTests=74, priorImages=12, priorCaptures=1431,
                   controllerChangesDuringPreparation=0, currentImage='genealogy', baselineFinalChecksPassed=True,
                   noDumps=True, retryApproved=False, boundFiles=len(bindings['sha256']),
                   utc=datetime.datetime.now(datetime.timezone.utc).isoformat()), out, indent=2)
print(json.dumps(dict(passed=True, boundFiles=len(bindings['sha256']), controllerChanges=0)))

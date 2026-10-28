from pathlib import Path
import gzip
import json
import subprocess
import sys

W = Path(__file__).parent
D = W.parent / 'retry_coherence_01'
R = Path('C:/Users/SoftIndVM/Fraktal')
approval = json.loads((D / 'authorization.json').read_bytes())
assert approval['OwnerInstruction'] == 'Approve guarded S4b paced coherence retry'
assert approval['DartReadQualificationAuthorized'] is True
assert not (D / 'session_result.json').exists(), 'approved active session required for this supplementary capture'
assert not (D / 'restore_genealogy_exit.json').exists(), 'candidate already rolled back'
old = json.loads(gzip.decompress((D / 'dart_qualification.json.gz').read_bytes()))
expected = old['snapshots'][0]['contentHash']
assert expected and old['readOnly'] and old['writes'] == 0
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], cwd=R, check=True)
command = ['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe',
    '--packages=' + str(D / 'dart_package_config.json'), str(W / 'coherence_readonly_diagnostics_01.dart'),
    expected, str(D / 'readonly_diagnostics_01.json.gz')]
raise SystemExit(subprocess.run(command, cwd=R).returncode)

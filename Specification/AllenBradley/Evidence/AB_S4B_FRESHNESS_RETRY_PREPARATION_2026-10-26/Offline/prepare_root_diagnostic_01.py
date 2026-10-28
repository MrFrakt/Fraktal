"""Prepare an unapproved fresh session with rejected-snapshot diagnostics."""
from pathlib import Path
import hashlib
import json
import shutil

W = Path(__file__).parent
OLD = W.parent / 'retry_template_01'
D = W.parent / 'retry_root_diagnostic_01'
assert not D.exists()
D.mkdir()
(D / 'scripts').mkdir()
(D / 'session').mkdir()
for name in ('run_logged.py', 'scripts/guard_echo.py', 'scripts/preflight.py',
             'ensure_manual_baseline.py', 'ensure_manual_candidate.py',
             'pre_restore_guard.py', 'restore_original_medium.py', 'audit_access.py',
             'candidate_equivalence.py', 'candidate_regressions_v2.py',
             'qualification_session_v2.py', 'session/Program.cs', 'session/S4bSession.csproj'):
    content = (OLD / name).read_text(encoding='utf-8').replace(OLD.as_posix(), D.as_posix())
    with (D / name).open('x', encoding='utf-8', newline='') as stream:
        stream.write(content)
for name in ('dart_package_config.json', 'canonical.sha256', 'genealogy.sha256',
             'capacity_review.json', 'canonical_prepared_compare.json', 'authorization.template.json'):
    shutil.copyfile(OLD / name, D / name)
shutil.copyfile(W / 'canonical_read_view_01.ACD', D / 's4b_read_view.ACD')
shutil.copyfile(W / 'canonical_read_view_01.L5X', D / 's4b_read_view.L5X')
assert hashlib.sha256((D / 's4b_read_view.ACD').read_bytes()).hexdigest().upper() == '7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
assert json.loads((D / 'authorization.template.json').read_bytes())['CurrentOwnerApproved'] is False
checks = (W / 'qualification_checks_v2.py').read_text(encoding='utf-8')
checks = checks.replace("D=W.parent/'session_01'", "D=W.parent/'retry_root_diagnostic_01'")
for before, after in (('missing_approval_cli_02', 'missing_approval_cli_root_diagnostic_01'),
                      ('missing_approval_sdk_02', 'missing_approval_sdk_root_diagnostic_01'),
                      ('qualification_checks_02.json', 'root_diagnostic_authorization_checks_01.json')):
    checks = checks.replace(before, after)
with (W / 'root_diagnostic_authorization_checks.py').open('x', encoding='utf-8', newline='') as stream:
    stream.write(checks)
print(json.dumps(dict(prepared=True, authorized=False, session=str(D), controllerChanges=0,
    candidateWriteScopeUnchanged=True, productionSourcesUnchanged=True)))

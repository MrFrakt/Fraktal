"""Fresh unapproved retry, unchanged ACD, corrected read-only discovery."""
from pathlib import Path
import hashlib,json,shutil
W=Path(__file__).parent;OLD=W.parent/'session_01';D=W.parent/'retry_template_01'
assert not D.exists();D.mkdir();(D/'scripts').mkdir();(D/'session').mkdir()
def save(p,text):
    with (D/p).open('x',encoding='utf-8',newline='') as stream:stream.write(text)
for name in ('run_logged.py','scripts/guard_echo.py','scripts/preflight.py','ensure_manual_baseline.py','ensure_manual_candidate.py',
    'pre_restore_guard.py','restore_original_medium.py','audit_access.py','candidate_equivalence.py','candidate_regressions_v2.py',
    'qualification_session_v2.py','session/Program.cs','session/S4bSession.csproj'):
    text=(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),D.as_posix())
    text=text.replace("'source_bindings_02.json'","'source_bindings.json'")
    save(name,text)
for name in ('dart_package_config.json','canonical.sha256','genealogy.sha256','capacity_review.json','canonical_prepared_compare.json','authorization.template.json'):
    shutil.copyfile(OLD/name,D/name)
shutil.copyfile(W/'canonical_read_view_01.ACD',D/'s4b_read_view.ACD')
shutil.copyfile(W/'canonical_read_view_01.L5X',D/'s4b_read_view.L5X')
pin=hashlib.sha256((D/'s4b_read_view.ACD').read_bytes()).hexdigest().upper()
assert pin=='7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
assert json.loads((D/'authorization.template.json').read_bytes())['CurrentOwnerApproved'] is False
checks=(W/'qualification_checks_v2.py').read_text(encoding='utf-8').replace("D=W.parent/'session_01'","D=W.parent/'retry_template_01'")
for old,new in [('missing_approval_cli_02','missing_approval_cli_retry_01'),('missing_approval_sdk_02','missing_approval_sdk_retry_01'),('qualification_checks_02.json','retry_authorization_checks_01.json')]:checks=checks.replace(old,new)
with (W/'retry_authorization_checks.py').open('x',encoding='utf-8',newline='') as stream:stream.write(checks)
print(json.dumps(dict(prepared=True,authorized=False,session=str(D),acdSha256=pin,scopeUnchanged=True,controllerChanges=0)))

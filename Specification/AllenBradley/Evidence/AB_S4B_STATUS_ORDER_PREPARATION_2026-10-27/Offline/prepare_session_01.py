"""Fresh unapproved session; controller image and write vectors are unchanged."""
from pathlib import Path
import hashlib
import json
import shutil
W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')
G=OLD.parent/'offline_01'
S=W.parent/'session_01'
assert not S.exists()
S.mkdir()
for name in ('run_logged.py','scripts/guard_echo.py','scripts/preflight.py',
    'ensure_manual_baseline.py','ensure_manual_candidate.py','pre_restore_guard.py',
    'restore_original_medium.py','audit_access.py','candidate_equivalence.py',
    'candidate_regressions_v2.py','qualification_session_v2.py','task_monitor.py','session_ready.py',
    'desktop_readonly.py','desktop_coverage.py','desktop_diagnostic_qualification_test.dart',
    'session/Program.cs','session/S4bSession.csproj'):
    target=S/name
    target.parent.mkdir(parents=True,exist_ok=True)
    content=(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
    with target.open('x',encoding='utf-8',newline='') as f:f.write(content)
for name in ('dart_package_config.json','canonical.sha256','genealogy.sha256','capacity_review.json',
    'canonical_prepared_compare.json','authorization.template.json','desktop_expected_inventory.json'):
    shutil.copyfile(OLD/name,S/name)
for name in ('ACD','L5X'):
    shutil.copyfile(G/('canonical_cold_01.'+name),S/('s4b_read_view.'+name))
assert hashlib.sha256((S/'s4b_read_view.ACD').read_bytes()).hexdigest().upper()=='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5'
approval=json.loads((S/'authorization.template.json').read_bytes())
assert approval['CurrentOwnerApproved'] is False
approval['Scope']+=' The generic cyclic read plan reads discovered module Status groups at the end of each full walk; no additional reads, changed freshness limits or altered row proofs.'
with (S/'authorization.template.json').open('w',encoding='utf-8') as f:json.dump(approval,f,indent=2)
for origin,name in (('cold_authorization_checks_01.py','status_authorization_checks_01.py'),
    ('workflow_checks_01.py','workflow_checks_01.py'),('readiness_checks_01.py','readiness_checks_01.py'),
    ('readonly_refusals_01.py','readonly_refusals_01.py')):
    content=(G/origin).read_text(encoding='utf-8')
    content=content.replace('C:/work/fraktal-ab-s4b-cold-20261026/session_01',S.as_posix())
    content=content.replace('cold_authorization_checks_01.json','status_authorization_checks_01.json')
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(content)
print(json.dumps(dict(prepared=True,currentOwnerApproved=False,controllerChanges=0,
    canonicalSha256=approval['CanonicalSha256'],controllerWriteVectorsUnchanged=True)))

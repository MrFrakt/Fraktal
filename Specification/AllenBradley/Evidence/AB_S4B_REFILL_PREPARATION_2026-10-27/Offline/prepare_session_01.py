"""Fresh unapproved refill retry, retaining the proven busy-witness apparatus."""
from pathlib import Path
import hashlib
import json
import shutil

W=Path(__file__).parent;S=W.parent/'session_01'
OLD=Path('C:/work/fraktal-ab-s4b-busy-witness-20261027/session_01');B=OLD.parent/'offline_01'
G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')
assert not S.exists()
q=json.loads((OLD/'runtime_summary_01.json').read_bytes())
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed'] and q['authorizationConsumed']
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87 and q['loginBusyWitness']['passed']
S.mkdir()
for name in ('run_logged.py','scripts/guard_echo.py','scripts/preflight.py',
    'ensure_manual_baseline.py','ensure_manual_candidate.py','pre_restore_guard.py',
    'restore_original_medium.py','audit_access.py','candidate_equivalence.py',
    'candidate_regressions_v2.py','qualification_session_v2.py','task_monitor.py','session_ready.py',
    'desktop_readonly.py','desktop_coverage.py','desktop_diagnostic_qualification_test.dart',
    'session/Program.cs','session/S4bSession.csproj','part_read_diagnostics.py','login_busy_witness.py'):
    target=S/name;target.parent.mkdir(parents=True,exist_ok=True)
    content=(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
    with target.open('x',encoding='utf-8',newline='') as f:f.write(content)
for name in ('dart_package_config.json','canonical.sha256','genealogy.sha256','capacity_review.json',
    'canonical_prepared_compare.json','authorization.template.json','desktop_expected_inventory.json'):
    shutil.copyfile(OLD/name,S/name)
for extension in ('ACD','L5X'):
    shutil.copyfile(G/('canonical_cold_01.'+extension),S/('s4b_read_view.'+extension))
assert hashlib.sha256((S/'s4b_read_view.ACD').read_bytes()).hexdigest().upper()=='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5'
approval=json.loads((S/'authorization.template.json').read_bytes())
assert not approval['CurrentOwnerApproved']
approval['Scope']+=' The generic read planner refills each completed row slot immediately, with at most four active guarded rows and one slot waiter. Count dependencies and the Status phase still drain the entire active window. A refused walk drains all started rows and does not dispatch further work after observing failure. Per-row leases/proofs, native reads, source ages, Good/expiry limits, attempts/deadlines and all PLC write vectors remain unchanged. Native performance of this scheduling correction is unproven.'
approval['BoundedRowRefill']=True
(S/'authorization.template.json').write_text(json.dumps(approval,indent=2)+'\n',encoding='utf-8',newline='')
for name in ('part_read_diagnostics.py','test_part_read_diagnostics.py','login_busy_witness.py','test_login_busy_witness.py'):
    shutil.copyfile(B/name,W/name)
for origin,target in (('authorization_checks_02.py','authorization_checks_01.py'),
    ('workflow_checks_01.py','workflow_checks_01.py'),('readiness_checks_01.py','readiness_checks_01.py'),
    ('readonly_refusals_01.py','readonly_refusals_01.py')):
    content=(B/origin).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
    with (W/target).open('x',encoding='utf-8',newline='') as f:f.write(content)
print(json.dumps(dict(prepared=True,currentOwnerApproved=False,controllerChanges=0,
    samePlcImage=True,writeVectorsUnchanged=True,busyWitnessRetained=True)))

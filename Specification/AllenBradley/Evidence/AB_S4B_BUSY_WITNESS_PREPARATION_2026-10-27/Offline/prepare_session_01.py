"""Fresh unapproved session; unchanged shipping client, image and write vectors."""
from pathlib import Path
import hashlib
import json
import shutil

W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s4b-array-tiers-20261027/session_01')
A=OLD.parent/'offline_01'
G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')
S=W.parent/'session_01'
assert not S.exists()
previous=json.loads((OLD/'runtime_summary_01.json').read_bytes())
assert previous['genealogyRestored'] and previous['baselineCases']==31 and previous['finalChecksPassed']
S.mkdir()
names=('run_logged.py','scripts/guard_echo.py','scripts/preflight.py',
    'ensure_manual_baseline.py','ensure_manual_candidate.py','pre_restore_guard.py',
    'restore_original_medium.py','audit_access.py','candidate_equivalence.py',
    'candidate_regressions_v2.py','qualification_session_v2.py','task_monitor.py','session_ready.py',
    'desktop_readonly.py','desktop_coverage.py','desktop_diagnostic_qualification_test.dart',
    'session/Program.cs','session/S4bSession.csproj','part_read_diagnostics.py')
for name in names:
    target=S/name;target.parent.mkdir(parents=True,exist_ok=True)
    content=(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
    if name=='candidate_regressions_v2.py':
        old="return fixture.paired_run(destination,candidate_factory=candidate.application,equivalence_gate=equivalence.run,prefix='s4b')"
        assert content.count(old)==1
        content=content.replace(old,"from login_busy_witness import with_busy_witness\n    parent=fixture.paired_run(destination,candidate_factory=candidate.application,equivalence_gate=equivalence.run,prefix='s4b')\n    return with_busy_witness(parent,destination)")
    with target.open('x',encoding='utf-8',newline='') as f:f.write(content)
shutil.copyfile(W/'login_busy_witness.py',S/'login_busy_witness.py')
for name in ('dart_package_config.json','canonical.sha256','genealogy.sha256','capacity_review.json',
    'canonical_prepared_compare.json','authorization.template.json','desktop_expected_inventory.json'):
    shutil.copyfile(OLD/name,S/name)
for extension in ('ACD','L5X'):
    shutil.copyfile(G/('canonical_cold_01.'+extension),S/('s4b_read_view.'+extension))
assert hashlib.sha256((S/'s4b_read_view.ACD').read_bytes()).hexdigest().upper()=='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5'
approval=json.loads((S/'authorization.template.json').read_bytes())
assert not approval['CurrentOwnerApproved']
approval['Scope']+=' Session-only login-busy proof warms the two public scalar paths before login, then reads canonical BOOL and legacy DINT under the existing same-scan guard immediately after the existing acknowledgement. It retains the full later comparison with its actual state, every original refusal/fixture/cleanup gate and the unchanged read-only client. No additional PLC writes or changed retries/quality limits.'
approval['SessionOnlyLoginBusyWitness']=True
(S/'authorization.template.json').write_text(json.dumps(approval,indent=2)+'\n',encoding='utf-8',newline='')
for name in ('part_read_diagnostics.py','test_part_read_diagnostics.py'):
    shutil.copyfile(A/name,W/name)
for name in ('array_authorization_checks_01.py','workflow_checks_01.py','readiness_checks_01.py','readonly_refusals_01.py'):
    source=A/name
    if not source.is_file():
        matches=list(A.glob('*authorization_checks_01.py'))
        assert name=='array_authorization_checks_01.py' and len(matches)==1
        source=matches[0]
    content=source.read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(content)
print(json.dumps(dict(prepared=True,currentOwnerApproved=False,controllerChanges=0,
    sameImage=True,shippingClientUnchanged=True,writeVectorsUnchanged=True)))

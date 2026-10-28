"""Validate the already prepared unapproved pool session; no controller access.

prepare_session_reference_02.py is a later reconstruction, not the source run
recorded by prepare_session_01.log. This gate validates actual prepared inputs.
"""
from pathlib import Path
import hashlib,json
W=Path(__file__).parent;S=W.parent/'session_01'
OLD=Path('C:/work/fraktal-ab-s4b-startup-20261027/session_01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(S/'s4b_read_view.ACD')=='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5'
assert sha(S/'s4b_read_view.L5X')=='60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E'
for name in ('authorization.json','session_started.json','deploy_attempt.json','echo_before_s4b.ACD','source_bindings.json','desktop_live'):
    assert not (S/name).exists(),name
approval=json.loads((S/'authorization.template.json').read_bytes())
assert approval['CurrentOwnerApproved'] is False
assert 'four read-only CIP connections' in approval['Scope']
assert 'one outstanding request per socket' in approval['Scope']
for name in ('qualification_session_v2.py','candidate_regressions_v2.py','desktop_readonly.py','desktop_diagnostic_qualification_test.dart','task_monitor.py','session/Program.cs'):
    expected=(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
    assert (S/name).read_text(encoding='utf-8')==expected,name
with (W/'verified_prepared_session_02.json').open('x',encoding='utf-8') as f:
    json.dump(dict(passed=True,controllerAccess=False,currentOwnerApproved=False,preparedInputsVerified=True,readConnections=4),f,indent=2)
print('Prepared image, inherited write/rollback scope and unapproved four-connection reader verified; no controller access.')

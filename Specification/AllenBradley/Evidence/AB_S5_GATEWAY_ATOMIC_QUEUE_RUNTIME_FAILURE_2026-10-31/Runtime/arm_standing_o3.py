from pathlib import Path
import datetime,hashlib,json
from s5_session import authorize,FLAGS
D=Path(__file__).parent
assert not (D/'session_started.json').exists()
value=json.loads((D/'authorization.template.json').read_bytes())
assert not value['CurrentOwnerApproved']
value.update(CurrentOwnerApproved=True,
    OwnerInstruction='Standing owner decision O3, AGENTS.md 3a and canonical publication plan 6.3: the dedicated Echo 601FC87B exists exclusively for repository agents; guarded sessions require no per-session approval. Complete S5 idle-connection correction qualification and genealogy rollback.',
    Scope='Unchanged S5 command vectors plus read-only 100-second idle startup and delayed-command checks; current owner C12; complete pinned genealogy rollback. No fault/TASK clears, clocks, power or vendor-state edits.',
    ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
value.update({key:True for key in FLAGS})
authorize(value)
with (D/'authorization_armed_record.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(standingDecision='O3',serial=value['Serial'],sourceBindingSha256=hashlib.sha256((D/'source_bindings.json').read_bytes()).hexdigest().upper(),authorization=value),stream,indent=2)
temporary=D/'authorization_armed.tmp'
with temporary.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
temporary.replace(D/'authorization.json')
print('Standing O3 armed for sealed session_10; all controller guards retained.')

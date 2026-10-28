from pathlib import Path
import json,shutil
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/prepare_session_01.py')
source=original.read_text(encoding='utf-8')
for before,after in (
 ("OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-timing-20261027/session_01')"),
 ("G=OLD.parent/'offline_01'","G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')")):
    assert source.count(before)==1
    source=source.replace(before,after)
exec(compile(source,str(original),'exec'),{'__file__':__file__})
S=W.parent/'session_01';T=Path('C:/work/fraktal-ab-s4b-timing-20261027/session_01')
shutil.copyfile(T/'part_read_diagnostics.py',S/'part_read_diagnostics.py')
for name in ('part_read_diagnostics.py','test_part_read_diagnostics.py'):
    shutil.copyfile(T.parent/'offline_01'/name,W/name)
path=S/'authorization.template.json';approval=json.loads(path.read_bytes())
assert approval['CurrentOwnerApproved'] is False
approval['Scope']=(
 'Fresh exact service/listener/identity/mode/fault/idle/session guards and backup; '
 'guarded MANUAL normalization if needed; Program/download/Run of unchanged V6.8 image; '
 'five-document restore and inherited 41 candidate cases (31 main, two Access, eight config/set-store), with exact restoration; '
 'concurrent four-connection serial-pinned read-only Dart observation, one outstanding request per socket; '
 'logical primitive-array leaf tiers now skip fully excluded groups and honor the slow heartbeat for all consumed slow leaves; '
 'the server response-processing clock includes worker queue time through the original age boundary; '
 'source timestamps, Good/expiry limits, row proofs, retry/deadline and direct read-only policy stay unchanged; '
 'existing Part tracing and opt-in CIP phase/queue/delivery tracing remain; '
 'read-only TASK monitoring at 100 ms from before download; strict LIVE/nonempty/full desktop coverage; '
 'remaining configuration/detail/oracle equivalence/generic acquisition/final scan only if ready, stopping candidate work at first failure; '
 'pinned genealogy rollback, exact original host documents, five-document restore, 31 baseline cases, MANUAL cleanup and final checks/preflight; '
 'no added PLC write vectors, fault/TASK-counter clears, clock changes, power/vendor-state operations or Echo hard kills. '
 'Native performance and acceptance of these corrections remain unproven.')
path.write_text(json.dumps(approval,indent=2)+'\n',encoding='utf-8',newline='')
print('Prepared unapproved array-tier/queue retry; unchanged PLC image/write vectors; no controller access.')

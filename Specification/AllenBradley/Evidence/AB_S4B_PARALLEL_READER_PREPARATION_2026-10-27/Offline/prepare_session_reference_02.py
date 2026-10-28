from pathlib import Path
import json
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/prepare_session_01.py')
source=original.read_text(encoding='utf-8')
before="OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')"
assert source.count(before)==1
source=source.replace(before,"OLD=Path('C:/work/fraktal-ab-s4b-startup-20261027/session_01')")
before="G=OLD.parent/'offline_01'"
assert source.count(before)==1
source=source.replace(before,"G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')")
before="approval['Scope']+=' The generic cyclic read plan reads discovered module Status groups at the end of each full walk; no additional reads, changed freshness limits or altered row proofs.'"
assert source.count(before)==1
source=source.replace(before,"approval['Scope']+=' The generic desktop reader now opens four read-only CIP connections, all pinned to the same controller serial, with at most one outstanding request per socket. Complete guarded rows lease one connection; full walks use bounded cohorts of four and count-dependency barriers. Targeted reads stay serial. Out-of-order source/count observations follow publication revisions; contradictory counts, counter restart and transport failure abort the pool. No PLC write vectors, freshness limits, retry budgets, row proofs or acceptance rules are added or relaxed. Native performance remains unproven.'")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
S=W.parent/'session_01'
assert (S/'desktop_diagnostic_qualification_test.dart').read_bytes()==Path('C:/work/fraktal-ab-s4b-startup-20261027/session_01/desktop_diagnostic_qualification_test.dart').read_bytes()
assert not (S/'authorization.json').exists()
print(json.dumps(dict(prepared=True,connections=4,currentOwnerApproved=False,controllerChanges=0)))

"""Verify the prepared inputs after execution, before updating current status docs."""
from pathlib import Path
import hashlib,json
W=Path(__file__).parent;D=W.parent/'session_01'
b=json.loads((D/'source_bindings.json').read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
mutable=D/'s4a_coherence.ACD'
rows=[]
for name,expected in b['sha256'].items():
    source=Path(name);actual=sha(source)
    if source==mutable:continue
    assert actual==expected,name
    rows.append(dict(path=name,sha256=actual))
assert sha(W/'command_a_02.ACD')==b['sha256'][str(mutable)]
report=dict(passed=True,unchangedBoundFiles=len(rows),verified=rows,
    originalPreparedAcdUnchanged=True,preparedAcdSha256=sha(W/'command_a_02.ACD'),
    sdkSavedSessionCopySha256=sha(mutable),
    sdkSaveMutatesPrivateCopyOnly=True)
with (D/'native_source_verified_01.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='verified'}))

from pathlib import Path
import hashlib,json
W=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
old=json.loads((W/'profile_10/sources.json').read_bytes())
current=json.loads((W/'profile_12/sources.json').read_bytes())
rows=[]
for relative in ['packages/fraktal_opcua_client/lib/src/cip_read_coherence.dart','test/cip_read_coherence_test.dart']:
    target=H/relative;previous=target.read_bytes()
    assert hashlib.sha256(previous).hexdigest()==current[relative],relative
    raw=(W/'profile_10/Sources'/relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==old[relative],relative
    target.write_bytes(raw)
    rows.append(dict(path=relative,before=current[relative],after=old[relative]))
with (W/'removed_phase_hint_01.json').open('x') as f:
    json.dump(dict(reason='Remove unproven advisory prediction; keep carried reads and every original proof/budget.',rows=rows),f,indent=2)
print(json.dumps(dict(restored=len(rows),source='profile_10',proofLimitsUnchanged=True)))

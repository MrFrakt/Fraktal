"""Apply the recorded Echo-only standing authorization after preparation seal."""
from pathlib import Path
import datetime,gzip,hashlib,json
from qualification_session_v2 import authorize,FLAGS,PIN,SOURCE
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
P=R/'Specification/AllenBradley/Evidence/AB_S4B_Q_OBSERVER_PREPARATION_2026-10-29'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
manifest=json.loads((P/'artifact_manifest.json').read_bytes())
for entry in manifest['artifacts']:
    p=P/entry['path'];assert sha(p)==entry['sha256'].upper(),p
    if 'expandedSha256' in entry:assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==entry['expandedSha256']
assert sha(P.with_suffix('.md'))==manifest['report']['sha256']
bindings=json.loads((D/'source_bindings.json').read_bytes())
assert sha(D/'source_bindings.json')==manifest['sourceBindingsSha256']
for path,pin in bindings['sha256'].items():assert sha(Path(path))==pin.upper(),path
assert sha(D/'s4b_read_view.ACD')==PIN and sha(D/'s4b_read_view.L5X')==SOURCE
agents=(R/'AGENTS.md').read_text(encoding='utf-8')
assert 'guarded Echo sessions no longer need' in agents and '601FC87B' in agents
value=json.loads((D/'authorization.template.json').read_bytes())
value.update(CurrentOwnerApproved=True,OwnerInstruction='Standing owner authorization O3, recorded 2026-10-27 in AGENTS.md section 3a and canonical plan sections 4 and 6.3: guarded Echo sessions no longer need per-session approval. This record applies only to the prepared S4b-Q scope on 601FC87B, 127.0.0.1 slot 0; all guards and rollback remain required.',
    AuthorizationBasis='Existing explicit owner standing authorization; no new approval inferred',
    PreparedManifestSha256=sha(P/'artifact_manifest.json'),SourceBindingsSha256=sha(D/'source_bindings.json'),
    RecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
value.update({key:True for key in FLAGS});authorize(value)
with (D/'authorization.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
print(json.dumps(dict(authorized=True,basis='O3',serial=value['Serial'],pin=PIN,verifiedArtifacts=len(manifest['artifacts']),verifiedSources=len(bindings['sha256']))))

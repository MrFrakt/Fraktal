from pathlib import Path
import datetime,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3d-20261022/prepare_f1995b2579fe4f7a9d15d02dd8ed53e9')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=json.loads((W/'source_bindings_01.json').read_text())
expected={
 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s2_equivalence.py':'bd76ff3e5a41b462cefd942f6c1b280b2a90e17b6c4dcdf0612a4b54f9a0f6ae',
 'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_pair_read_window.py':'14b0f9adc395529047577ced013393de25852ec5bb05e0e1b80fbe8c7b3ea190'}
after={p:sha(ROOT/p) for p in before['sha256']}
changed={p:h for p,h in after.items() if h!=before['sha256'][p]}
assert changed==expected,changed
report=dict(passed=True,sourceCommit=before['sourceCommit'],capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),unchangedFiles=68,changedReadOnlyHarnessFiles=2,plcSourcesUnchanged=True,preparedSourceBindingsSha256=sha(W/'source_bindings_01.json'),changes=[dict(path=p,before=before['sha256'][p],after=h) for p,h in changed.items()],sha256=after)
with (R/'source_bindings_runtime_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='sha256'}))

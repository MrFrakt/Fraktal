"""Record current exact-session approval and verify prepared inputs, read-only."""
from pathlib import Path
import datetime,gzip,hashlib,json,shutil,uuid
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
P=Path('C:/work/fraktal-ab-s3g-20261023/prepare_feb76c7a0968442293ee0d20b812eb17')
E=ROOT/'Specification/AllenBradley/Evidence/AB_S3G_CANONICAL_PREPARATION_2026-10-23'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_text())
assert sha(E.with_suffix('.md'))==m['reportSha256']
for item in m['artifacts']:
    file=E/item['path'];raw=file.read_bytes()
    assert len(raw)==item['bytes'] and sha(file)==item['sha256'],file
    if item.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['expandedSha256']
v=json.loads((P/'full_preparation_verification_01.json').read_text())
for name,pin in v['sha256'].items():assert sha(ROOT/name)==pin,name
assert sha(P/'s3g_canonical.ACD').upper()==m['preparedAcdSha256']
assert sha(P/'session/bin/Debug/net8.0/win-x86/S3gSession.exe')==m['sessionExecutableSha256']
assert sha(P/'session/Program.cs')==m['sessionSourceSha256']
assert not (P/'authorization.json').exists() and not (P/'deploy_attempt.json').exists()
R=P.parent/('runtime_'+uuid.uuid4().hex);R.mkdir()
shutil.copyfile(P/'run_logged.py',R/'run_logged.py')
shutil.copyfile(__file__,R/'begin_authorized_s3g.py')
approval=json.loads((P/'authorization.template.json').read_text())
for key in ('CurrentOwnerApproved','ManualNormalizationAuthorized','AccessVectorsAuthorized','ConfigurationVectorsAuthorized','NativeMetricsVectorsAuthorized'):
    approval[key]=True
approval.update(ApprovalQuestion='call_5e5f359334b94e09adf9531a212f0d9c:0',
    Answer='Approve this guarded S3g session',CapturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    PreparationManifestSha256=sha(E/'manifest.json'),RuntimeEvidenceDirectory=str(R))
assert not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
for path in (P/'authorization.json',R/'authorization.json'):
    with path.open('x') as f:json.dump(approval,f,indent=2)
with (R/'runtime_inputs_01.json').open('x') as f:
    json.dump(dict(passed=True,capturedUtc=approval['CapturedUtc'],preparedAcdSha256=m['preparedAcdSha256'],
        preparedSourceSha256=m['sourceSha256'],sessionExecutableSha256=m['sessionExecutableSha256'],
        preparationManifestSha256=sha(E/'manifest.json'),sourceBindings=len(v['sha256']),sha256=v['sha256'],
        currentAuthorization=True,faultClearAuthorized=False,clockSetAuthorized=False),f,indent=2)
print(json.dumps(dict(passed=True,runtime=str(R),currentAuthorization=True,sourceBindings=len(v['sha256']))))

"""Record current owner authority and bind the unchanged prepared S3h image."""
from pathlib import Path
import datetime,hashlib,json,shutil
R=Path(__file__).parent;P=R.parent/'prepare_5822102a73e348ec95ff7082959ef940'
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_text());v=json.loads((P/'preparation_verification_01.json').read_text())
assert m['preparedAcdSha256']==sha(P/'s3h_canonical.ACD').upper()=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
assert sha(P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe')==m['sessionExecutableSha256']
assert sha(P/'session/Program.cs')==m['sessionSourceSha256']
assert sha(P/'s3h_candidate_03.L5X')==m['sourceSha256']
for name,pin in v['sha256'].items():assert sha(ROOT/name)==pin,name
for item in m['artifacts']:
    assert sha(E/item['path'])==item['sha256'],item['path']
assert sha(E.parent/m['report'])==m['reportSha256']
for name in ('authorization.json','deploy_attempt.json','backup.sha256','canonical_downloaded.L5X','genealogy_restored.L5X'):
    assert not (P/name).exists(),name
approval=json.loads((P/'authorization.template.json').read_text())
approval.update(CurrentOwnerApproved=True,ManualNormalizationAuthorized=True,AccessVectorsAuthorized=True,
    ConfigurationVectorsAuthorized=True,ApprovalQuestion='call_ee9b48ca64a744a5a7221f84bf3615a1:0',
    ApprovalAnswer='Approve this guarded S3h session',ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    PreparationManifestSha256=sha(E/'manifest.json'),PreparationReportSha256=m['reportSha256'],
    RuntimeDirectory=R.as_posix())
assert not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
for path in (P/'authorization.json',R/'owner_session_approval.json'):
    with path.open('x',encoding='utf-8') as f:json.dump(approval,f,indent=2)
shutil.copyfile(P/'run_logged.py',R/'run_logged.py')
prior=Path('C:/work/fraktal-ab-s3g-20261023/runtime_9564a5c9669b42eeadca0c412b7ea3f7')
text=(prior/'candidate_then_restore.py').read_text().replace('prepare_feb76c7a0968442293ee0d20b812eb17',P.name)
text=text.replace('s3g_native_candidate_01.L5X','s3h_candidate_03.L5X').replace('audit_s3g_access.py','audit_access.py').replace('s3g','s3h').replace('S3g','S3h')
text=text.replace('call_5e5f359334b94e09adf9531a212f0d9c:0',approval['ApprovalQuestion'])
with (R/'candidate_then_restore.py').open('x',encoding='utf-8') as f:f.write(text)
with (R/'initial_source_verification.json').open('x',encoding='utf-8') as f:
    json.dump(dict(passed=True,capturedUtc=approval['ApprovedUtc'],sourceBindings=len(v['sha256']),sha256=v['sha256'],
        sessionExecutableSha256=m['sessionExecutableSha256'],preparedAcdSha256=m['preparedAcdSha256']),f,indent=2)
print(json.dumps(dict(passed=True,sourceBindings=len(v['sha256']),preparedAcdSha256=m['preparedAcdSha256'],
    approvalQuestion=approval['ApprovalQuestion'],controllerChanges=0)))

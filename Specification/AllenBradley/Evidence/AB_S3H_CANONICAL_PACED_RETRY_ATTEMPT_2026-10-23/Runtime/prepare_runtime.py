"""Bind current owner approval to the exact sealed S3h retry preparation."""
from pathlib import Path
import datetime, hashlib, json, shutil
R=Path(__file__).parent
P=R.parent/'retry_fc306d330cc642499a52abbb53bae945'
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
E=ROOT/'Specification/AllenBradley/Evidence/AB_S3H_CANONICAL_PACED_RETRY_PREPARATION_2026-10-23'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_text())
v=json.loads((P/'retry_verification_01.json').read_text())
assert sha(E/'manifest.json')=='e0def2de1f626503858c1bb6fbbee27a755153d4fd7abe307c5950e84f5fb437'
assert m['preparedAcdSha256']==sha(P/'s3h_canonical.ACD').upper()=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
assert sha(P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe')==m['sessionExecutableSha256']
assert sha(P/'session/Program.cs')==m['sessionSourceSha256']
assert sha(P/'s3h_candidate_03.L5X')==m['sourceSha256']
assert len(v['sha256'])==159
for name,pin in v['sha256'].items(): assert sha(ROOT/name)==pin,name
for item in m['artifacts']: assert sha(E/item['path'])==item['sha256'],item['path']
assert sha(E.parent/m['report'])==m['reportSha256']
for name in ('authorization.json','deploy_attempt.json','backup.sha256','canonical_downloaded.L5X','genealogy_restored.L5X'):
    assert not (P/name).exists(),name
approval=json.loads((P/'authorization.template.json').read_text())
approval.update(CurrentOwnerApproved=True,ManualNormalizationAuthorized=True,AccessVectorsAuthorized=True,
    ConfigurationVectorsAuthorized=True,ApprovalQuestion='call_9b203bdff24848999469abe17a76ee4f:0',
    ApprovalAnswer='Approve this guarded paced S3h retry',ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    PreparationManifestSha256=sha(E/'manifest.json'),PreparationReportSha256=m['reportSha256'],RuntimeDirectory=R.as_posix())
assert not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
for path in (P/'authorization.json',R/'owner_session_approval.json'):
    with path.open('x',encoding='utf-8') as f: json.dump(approval,f,indent=2)
shutil.copyfile(P/'run_logged.py',R/'run_logged.py')
prior=R.parent/'runtime_6cf76ecb8785463ab372c202e79f03f2'
text=(prior/'candidate_then_restore.py').read_text()
assert text.count('prepare_5822102a73e348ec95ff7082959ef940')==1
assert text.count('call_ee9b48ca64a744a5a7221f84bf3615a1:0')==1
assert text.count('tooling_validation_01.json')==1
text=text.replace('prepare_5822102a73e348ec95ff7082959ef940',P.name)
text=text.replace('call_ee9b48ca64a744a5a7221f84bf3615a1:0',approval['ApprovalQuestion'])
text=text.replace('tooling_validation_01.json','initial_source_verification.json')
with (R/'candidate_then_restore.py').open('x',encoding='utf-8') as f: f.write(text)
with (R/'initial_source_verification.json').open('x',encoding='utf-8') as f:
    json.dump(dict(passed=True,capturedUtc=approval['ApprovedUtc'],sourceBindings=159,sha256=v['sha256'],
        sessionExecutableSha256=m['sessionExecutableSha256'],preparedAcdSha256=m['preparedAcdSha256']),f,indent=2)
print(json.dumps(dict(passed=True,sourceBindings=159,preparedAcdSha256=m['preparedAcdSha256'],
    approvalQuestion=approval['ApprovalQuestion'],controllerChanges=0)))

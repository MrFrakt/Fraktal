"""Record the current approved diagnostic scope against its sealed artifacts."""
from pathlib import Path
import datetime,hashlib,json,shutil
R=Path(__file__).parent;P=R.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
E=ROOT/'Specification/AllenBradley/Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_text());v=json.loads((P/'diagnostic_verification_01.json').read_text())
assert sha(E/'manifest.json')=='df6b5a589153b8d3c9fa0d41a09434942161461870dcf90f916fb6b289acde82'
assert sha(P/'s3h_canonical.ACD').upper()==m['preparedAcdSha256']=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
assert sha(P/'s3h_candidate_03.L5X')==m['sourceSha256']
assert sha(P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe')==m['sessionExecutableSha256']
assert sha(P/'session/Program.cs')==m['sessionSourceSha256']
assert len(v['sha256'])==159
for name,pin in v['sha256'].items():assert sha(ROOT/name)==pin,name
for name,pin in v['diagnosticBindings'].items():assert sha(P/name)==pin,name
for row in m['artifacts']:assert sha(E/row['path'])==row['sha256'],row['path']
assert sha(E.parent/m['report'])==m['reportSha256']
for name in ('authorization.json','deploy_attempt.json','backup.sha256','canonical_downloaded.L5X','genealogy_restored.L5X'):
 assert not (P/name).exists(),name
approval=json.loads((P/'authorization.template.json').read_text())
approval.update(CurrentOwnerApproved=True,ManualNormalizationAuthorized=True,AccessVectorsAuthorized=True,
 ConfigurationVectorsAuthorized=True,ReadTimingDiagnosticsAuthorized=True,
 ApprovalQuestion='call_b76d12f2f038411386f83c339fcd94e0:0',ApprovalAnswer='Approve this guarded S3h diagnostic session',
 ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),RuntimeDirectory=R.as_posix(),
 PreparationManifestSha256=sha(E/'manifest.json'),PreparationReportSha256=m['reportSha256'],DiagnosticBindings=v['diagnosticBindings'])
assert not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
for path in (P/'authorization.json',R/'owner_session_approval.json'):
 with path.open('x') as f:json.dump(approval,f,indent=2)
shutil.copyfile(P/'run_logged.py',R/'run_logged.py')
prior=R.parent/'runtime_a1ce558b0f284b888339550fad1e179e'
t=(prior/'candidate_then_restore.py').read_text()
for old,new in {
 'retry_fc306d330cc642499a52abbb53bae945':P.name,
 'call_9b203bdff24848999469abe17a76ee4f:0':approval['ApprovalQuestion'],
 "T/'fraktal_ab_s3h_fixture_execute.py'":"P/'diagnostic_fixture_execute.py'",
 }.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
with (R/'candidate_then_restore.py').open('x') as f:f.write(t)
with (R/'initial_source_verification.json').open('x') as f:
 json.dump(dict(passed=True,sourceBindings=159,sha256=v['sha256'],diagnosticBindings=v['diagnosticBindings'],
  sessionExecutableSha256=m['sessionExecutableSha256'],preparedAcdSha256=m['preparedAcdSha256'],sourceSha256=m['sourceSha256']),f,indent=2)
print(json.dumps(dict(passed=True,sourceBindings=159,diagnosticBindings=len(v['diagnosticBindings']),
 approvalQuestion=approval['ApprovalQuestion'],controllerChanges=0)))

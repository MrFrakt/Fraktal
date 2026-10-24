"""Bind the current retry instruction to the already approved genealogy recovery."""
from pathlib import Path
import datetime,hashlib,json,os,sys
R=Path(__file__).parent
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
OLD=Path('C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb')
P=OLD.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')
baseline='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert sha(original).upper()==baseline
pins=json.loads((OLD/'initial_source_verification.json').read_text())
for name,h in pins['sha256'].items():assert sha(ROOT/name)==h,name
for name,h in pins['diagnosticBindings'].items():assert sha(P/name)==h,name
assert sha(P/'s3h_canonical.ACD').upper()==pins['preparedAcdSha256']
prior=json.loads((P/'authorization.json').read_text())
assert prior['CurrentOwnerApproved'] and prior['ApprovalQuestion']=='call_b76d12f2f038411386f83c339fcd94e0:0'
assert 'hash-checked genealogy rollback' in prior['Scope']
assert not (P/'deploy_attempt.json').exists()
sealed=ROOT/'Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21'
manifest=json.loads((sealed/'manifest.json').read_text())
entry=next(row for row in manifest['artifacts'] if row['path']=='Session/capacity_review.json')
capacity=sealed/entry['path']
assert capacity.stat().st_size==entry['bytes'] and sha(capacity)==entry['sha256'].lower()
assert json.loads(capacity.read_text())['BaselineSha256']==baseline
with (R/'baseline_capacity.json').open('xb') as f:f.write(capacity.read_bytes())
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_live as live
import fraktal_ab_station as station
app=station.application()
preflight=json.loads((P/'preflight.json').read_text())
medium=live.FileMedium(live.live_directory(app,'601FC87B'))
assert {key:medium.read(key) for key in preflight['documents']}==preflight['documents'],'Saved five-document medium changed'
for label in ('empty_guard_01','recovery_build_01','recovery_authorization_tests_01'):
    assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0
authorization=dict(CurrentOwnerApproved=True,Serial='601FC87B',CanonicalSha256=pins['preparedAcdSha256'],
    EmptyGenealogyRecoveryAuthorized=True,FaultClearAuthorized=False,ClockSetAuthorized=False,
    CurrentUserInstruction='retry download on echo',
    ExistingSessionApprovalQuestion=prior['ApprovalQuestion'],
    ExistingSessionApprovalAnswer=prior['ApprovalAnswer'],
    Scope='Restore the already-approved hash-pinned genealogy image to twice-verified empty RemoteProgram Echo; normal SDK Run; existing five-document restore and 31 baseline checks; unchanged original preflight must pass before the approved fresh-backup/S3h diagnostic/download/rollback sequence.',
    ScopeBasis='Current owner download retry plus the unused session genealogy restoration/write authorization; recovery only on a verified empty controller, as qualified in S2. The original S3h preflight is unchanged.',
    CapturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    RecoverySourceSha256=baseline,
    ReadOnlySourceBindings=len(pins['sha256']),DiagnosticBindings=len(pins['diagnosticBindings']),
    CapacityEvidence='Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21/Session/capacity_review.json',
    SourceHashes={name:sha(R/name) for name in ('empty_guard.py','session/Program.cs','session/Recovery.csproj','session/bin/Debug/net8.0/win-x86/Recovery.exe')},
    UserRecoveryNotes=dict(file='echo_crash_re_2026-10-24.md',localFileLocated=False,
        suppliedFinding='libComms.dll NULL dereference on error-logging path before trace-context initialization; possible recurring I/O mismatch trigger',
        suppliedOperationalRule='Avoid hard kills; prefer natural shutdown; inspect controller dump folders after faults and before reboot. New dumps can slow service startup.',
        independentReportReviewPending=True))
with (R/'authorization.json').open('x') as f:json.dump(authorization,f,indent=2)
print(json.dumps(dict(prepared=True,emptyOnly=True,originalGenealogySha256=baseline,sourceBindings=len(pins['sha256']),
    authorizationTests=7,savedDocuments=len(preflight['documents']),controllerChanges=0)))

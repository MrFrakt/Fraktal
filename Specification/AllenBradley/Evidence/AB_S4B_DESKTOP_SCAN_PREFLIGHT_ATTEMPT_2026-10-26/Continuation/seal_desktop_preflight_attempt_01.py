from pathlib import Path
import datetime
import gzip
import hashlib
import json

R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
D=W.parent/'desktop_scan_01'
E=R/'Specification/AllenBradley/Evidence'
OUT=E/'AB_S4B_DESKTOP_SCAN_PREFLIGHT_ATTEMPT_2026-10-26'
REPORT=OUT.with_suffix('.md')
load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists() and not REPORT.exists()
result=load(D/'session_result.json')
assert result['candidateError'].startswith('JSONDecodeError:') and result['authorizationConsumed']
assert not (D/'deploy_attempt.json').exists() and not (D/'canonical_downloaded.L5X').exists()
assert load(D/'manual_initial.json')['controllerWrites']==0
assert all(load(D/(label+'_exit.json'))['exitCode']==0 for label in
    ('guard_initial','manual_initial','preflight_initial','backup','backup_audit','backup_access','guard_unchanged_01','preflight_unchanged_01'))
assert load(D/'task_monitor_ready.json')==dict(ready=True,readOnly=True,serial='601FC87B')
assert load(D/'task_monitor_exit.json')['exitCode']==0 and not result['dumpFiles']
assert load(D/'ready_before_01_exit.json')['exitCode']==1
report='''# S4b desktop/scan pre-download attempt — 2026-10-26

**The attempt stopped after its audited backup and before any download or
controller write. Genealogy is unchanged. A readiness-file race is reproduced
offline and corrected for the same unfinished approved scope.**

The current owner answered “Approve guarded S4b desktop/scan session” to
`call_6c35ecad4ba84714a17ec9b7b68f5ad4:0`, approving the
[sealed package](AB_S4B_DESKTOP_SCAN_PREPARATION_2026-10-26.md).
Fresh identity/service/listener/mode/fault/dump, MANUAL/idle/logout/document,
backup and SDK/access audits passed on Echo 601FC87B. MANUAL normalization
recorded zero controller writes. The monitor took one valid read-only sample.

The parent observed the ready file immediately after creation and before its
JSON writer closed/flushed it. The unguarded json.loads raised JSONDecodeError.
The helper then completed its correct message and shut down with zero writes.
There is no deploy_attempt marker, candidate read-back or download stage. No
Program/Run cycle, candidate fixture, desktop test or genealogy rollback ran.
The wrapper's genealogyRestored:false means no rollback was required, not that
genealogy was removed. Fresh read-only guard and original-preflight comparison
confirm Run, not faulted, unchanged MANUAL/idle/logout and document/policy state.
Baseline regressions were not repeated because no controller change occurred.

The failed wrapper's authorizationConsumed:true is retained as its single-use
attempt record. The current explicit instruction's download and 41/31 scope
has not been exercised. A fresh continuation directory will bind the readiness-
only correction to that same current instruction and unchanged image/write
scope; this is not authorization for another image or additional writes.

The offline partial-file workflow reproduces the failure against this sealed
parent. The correction waits for complete, typed, target-matching JSON within
the original 10/90-second readiness deadlines; wrong/dead helpers fail closed.
Both monitor and observer handoffs use one helper. No shipping HMI, PLC,
coherence/freshness profile, controller write vectors or fault/counter policy
changes. The failed logs and source bindings remain intact. No dumps, fault
clears, clock changes, power/vendor-state operations or Echo hard kills.
Nothing committed or pushed. Credentials and ACD binaries are excluded.
'''
with REPORT.open('x',encoding='utf-8') as stream:stream.write(report)
artifacts=[]
def archive(path,relative):
    raw=path.read_bytes(); expanded=None
    if path.suffix.lower() in ('.log','.l5x'):
        expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(target),**({'expandedSha256':expanded} if expanded else {})))
for path in sorted(D.rglob('*')):
    if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.relative_to(D).parts):continue
    if path.suffix.lower() not in ('.py','.json','.gz','.log','.txt','.sha256','.l5x','.cs','.csproj','.dart'):continue
    assert 'credential' not in path.name.lower()
    archive(path,'Runtime/'+path.relative_to(D).as_posix())
for name in ('authorize_desktop_scan_01.py','test_ready_workflow_01.py','seal_desktop_preflight_attempt_01.py'):
    archive(W/name,'Continuation/'+name)
for suffix in ('.log','_exit.json'):
    archive(W.parent/'retry_reader_01'/('authorize_desktop_scan_01'+suffix),'Continuation/authorize_desktop_scan_01'+suffix)
value=dict(schema='fraktal.ab.s4b-desktop-preflight-attempt',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    preparationManifestSha256=sha(E/'AB_S4B_DESKTOP_SCAN_PREPARATION_2026-10-26/manifest.json'),
    downloaded=False,controllerWrites=0,genealogyUnchanged=True,guardAndPreflightRecheckPassed=True,
    currentInstructionContinuationScopeUnchanged=True,credentialFilesArchived=False,acdBinariesArchived=False,
    committed=False,pushed=False,artifacts=artifacts)
with (OUT/'manifest.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
for row in artifacts:assert sha(OUT/row['path'])==row['sha256']
with (W/'sealed_desktop_preflight_attempt_01.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(passed=True,artifacts=len(artifacts),manifestSha256=sha(OUT/'manifest.json'),downloaded=False,controllerWrites=0),stream,indent=2)
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),downloaded=False,controllerWrites=0)))

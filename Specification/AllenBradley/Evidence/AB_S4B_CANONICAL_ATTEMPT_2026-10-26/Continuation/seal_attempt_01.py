"""Seal the failed qualification and verified rollback before changing code."""
from pathlib import Path
import datetime,gzip,hashlib,json,statistics
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01';E=R/'Specification/AllenBradley/Evidence'
OUT=E/'AB_S4B_CANONICAL_ATTEMPT_2026-10-26';REPORT=OUT.with_suffix('.md')
load=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
assert not OUT.exists() and not REPORT.exists()
session=load(D/'session_result.json');baseline=load(D/'baseline_regressions.json');final=load(D/'final_checks.json')
assert session['passed'] is False and session['genealogyRestored'] and session['rollbackError'] is None
assert session['authorizationConsumed'] and not session['dumpFiles']
assert len(baseline['rows'])==31 and all(row['passed'] for row in baseline['rows'])
assert final['passed'] and all(final['checks'].values()) and all(final['savedDocumentsEqual'].values())
assert not (D/'candidate_regressions.json').exists() and not (D/'dart_ready.json').exists()
dart=json.loads(gzip.decompress((D/'dart_qualification.json.gz').read_bytes()))
assert dart['passed'] is False and not dart['samples'] and not dart['configurationPages']
assert 'Unterminated Template name' in dart['error']
stages={p.name.removesuffix('_exit.json'):load(p)['exitCode'] for p in D.glob('*_exit.json')}
assert stages['qualification_run_01']==stages['candidate_regressions']==1
assert all(code==0 for name,code in stages.items() if name not in ('qualification_run_01','candidate_regressions'))
bindings=load(D/'source_bindings_02.json');changed=[]
for path,pin in bindings['sha256'].items():
    if sha(Path(path)).upper()!=pin:changed.append(path)
assert changed==[(D/'s4b_read_view.ACD').as_posix()],changed
assert load(D/'deploy_readback_exit.json')['exitCode']==0
original=Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')
assert sha(original).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
timing=load(D/'baseline_timing.json');samples=[row['values'] for row in timing['samples']]
summary=dict(passed=False,reason=dart['error'],serial='601FC87B',candidateWritesStarted=False,candidateCases=0,
    baselineCases=31,genealogyRestored=True,finalChecksPassed=True,originalDocumentsRestored=5,stageExits=stages,
    changedBoundFiles=changed,changedAcdReason='SDK Save during approved download; exported L5X read-back and access audit passed',
    baselineScanMedianUs=statistics.median(row['FRK_Press_HealthProbe.TaskLastScanUs'] for row in samples),
    baselineScanCumulativeMaxUs=max(row['FRK_Press_HealthProbe.TaskMaxScanUs'] for row in samples),
    overlaps=max(row['FRK_Press_HealthProbe.TaskOverlapCount'] for row in samples),
    authorizationConsumed=True,currentControllerChangesAuthorized=False,dumpFiles=[],faultClears=0,clockChanges=0,powerOperations=0,hardKills=0)
save(D/'runtime_summary_01.json',summary)
save(D/'owner_authorization_consumed_01.json',dict(serial='601FC87B',approvalQuestion='call_298845fc9dc04b9c89398259d6673bfa:0',
    ownerInstruction='Approve guarded S4b qualification',authorizationSha256=sha(D/'authorization.json'),
    sessionResultSha256=sha(D/'session_result.json'),authorizationConsumed=True,currentControllerChangesAuthorized=False))
report='''# S4b canonical qualification attempt — 2026-10-26

**Qualification failed during Dart Template discovery; genealogy rollback is verified.**
The observer failed before readiness and before candidate regression writes.
No S4b runtime, value, row-coherence, performance or desktop acceptance is claimed.

The owner answered “Approve guarded S4b qualification” to
`call_298845fc9dc04b9c89398259d6673bfa:0`, authorizing the scope sealed in the
[frozen-package preparation](AB_S4B_FROZEN_PACKAGE_PREPARATION_2026-10-26.md).
This approval is consumed. No further download/mode/tag-write session is authorized.

## Passed

- Fresh target/service/listener/identity checks: Echo 601FC87B, 1756-L81E
  v38.011, 127.0.0.1 slot 0; Run, Remote, not faulted.
- Initial MANUAL normalization made zero writes; logged out/idle; five saved
  documents equal live. Fresh preflight, backup, backup Save As log audit and
  baseline access audit pass.
- Prepared ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`
  downloaded and returned to Run. Source
  `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
  SDK log, exported L5X value/layout read-back and access audits pass. SDK Save
  changed the working ACD hash; the original prepared copy remains untouched.
- Pinned genealogy downloaded from a hash-checked copy; original ACD remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Restore SDK/access audits, original five host-document restoration,
  **31/31 baseline cases**, MANUAL cleanup, final checks and preflight pass.
- Final state: scanning, MANUAL/idle, logged out, not restoring, policy restored,
  five saved/live documents equal. No fault clears, clock changes, power or
  vendor-state operations, hard kills or dump files.

## Failed and skipped

The Dart observer reported **`OPC UA transport error: FormatException:
Unterminated Template name.`** No ready file was created. The wrapper stopped
the candidate fixture at that first failure and immediately entered its
approved rollback path. The failure report contains zero complete samples
and zero configuration pages; it does not identify the failing Template handle.

All **41 candidate cases** were skipped. Candidate all-path equivalence,
generic capture, native scan and desktop acceptance were not reached. The
rollback's separately authorized normalization used the existing LOGIN,
SET_MODE(MANUAL=1), LOGOUT frames; the 31 baseline regressions ran afterwards.

The failing parser and all bound sources are unchanged at this seal. Only the
working deployment ACD changed through SDK Save, as expected. Offline
2,336 AB /74 root /631 Flutter tests (12 skips), both v38 builds/read-backs,
Windows build and measured 65% Capacity remain preparation results.

## Next

Investigate the strict Template string parser using recorded native definition
bytes; add a reproduction and diagnostics, then rerun relevant offline gates.
The exact cause in this S4b image is not yet established. Do not suppress missing
names, infer station facts, loosen coherence/identity/access guards, or count
this failure as PLC acceptance. Any fresh guarded retry requires current
authorization under AGENTS.md §3a. S4–S7 and S3 physical I/O proof remain open.
No commit or push occurred. Credentials and ACD binaries are not archived.
'''
with REPORT.open('x',encoding='utf-8',newline='') as stream:stream.write(report)
artifacts=[]
for source in sorted(D.rglob('*')):
    if not source.is_file() or any(part in ('bin','obj','__pycache__') for part in source.relative_to(D).parts):continue
    if source.suffix.lower() not in ('.py','.json','.gz','.log','.txt','.sha256','.l5x','.cs','.csproj'):continue
    assert 'credential' not in source.name.lower()
    relative='Runtime/'+source.relative_to(D).as_posix();raw=source.read_bytes();expanded=None
    if source.suffix.lower() in ('.log','.l5x'):
        expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    artifacts.append(dict(path=relative,sha256=sha(target),bytes=len(raw),**({'expandedSha256':expanded} if expanded else {})))
for source in [W/'authorize_s4b_01.py',W/'authorize_s4b_01.log',W/'authorize_s4b_01_exit.json',W/'seal_attempt_01.py']:
    target=OUT/'Continuation'/source.name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(source.read_bytes())
    artifacts.append(dict(path=target.relative_to(OUT).as_posix(),sha256=sha(target),bytes=target.stat().st_size))
prep=E/'AB_S4B_FROZEN_PACKAGE_PREPARATION_2026-10-26/manifest.json'
save(OUT/'manifest.json',dict(schema='fraktal.ab.s4b-canonical-attempt',schemaVersion=1,date='2026-10-26',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),nativeAccepted=False,
    authorizationConsumed=True,currentControllerChangesAuthorized=False,approvalQuestion='call_298845fc9dc04b9c89398259d6673bfa:0',
    preparedAcdSha256=load(D/'authorization.json')['CanonicalSha256'],sourceSha256=load(D/'authorization.json')['SourceSha256'],
    preparationManifestSha256=sha(prep),candidateCases=0,baselineCases=31,genealogyRestored=True,originalHostDocumentsRestored=5,
    finalChecksPassed=True,dumpFiles=0,faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,artifacts=artifacts,
    credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False))
for row in artifacts:assert sha(OUT/row['path'])==row['sha256']
save(W/'sealed_attempt_01.json',dict(passed=True,nativeAccepted=False,genealogyRestored=True,baselineCases=31,
    artifacts=len(artifacts),manifestSha256=sha(OUT/'manifest.json'),authorizationConsumed=True))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),genealogyRestored=True,baselineCases=31,nativeAccepted=False)))

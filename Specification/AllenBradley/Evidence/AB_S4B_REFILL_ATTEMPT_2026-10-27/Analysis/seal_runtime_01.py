"""Seal only the recorded row-refill qualification after verified rollback."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;S=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence'
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=load(S/'runtime_summary_01.json');auth=load(S/'authorization.json')
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed']
assert q['authorizationConsumed'] and not q['currentControllerChangesAuthorized']
assert auth['ApprovalQuestion']=='call_a03c1071e32641f687cf1970bb701ef9:0'
assert auth['OwnerInstruction']=='Approve guarded S4b row-refill retry'
assert all(q[key]==0 for key in ('faultClears','taskCounterClears','clockChanges','powerOperations','hardKills'))
assert not q['dumpFiles']
prep=E/'AB_S4B_REFILL_PREPARATION_2026-10-27/manifest.json'
assert sha(prep)=='cb7ccb572576b28591233484ca404ea6416a3f8cfe28e5ee75a479aabad40750'
stamp=datetime.datetime.now().astimezone().strftime('%Y-%m-%d')
kind='RUNTIME' if q['nativeAccepted'] else 'ATTEMPT'
name=f'AB_S4B_REFILL_{kind}_{stamp}'
OUT=E/name;REPORT=OUT.with_suffix('.md')
assert not OUT.exists() and not REPORT.exists()
cases=load(S/'candidate_regressions.json') if (S/'candidate_regressions.json').is_file() else {}
busy=q['loginBusyWitness'];coverage=q['desktopCoverage'];trace=q.get('candidateTraceEpoch') or {}
part=q.get('partReadDiagnostics') or {};cip=q.get('cipPhaseTiming') or {}
started=load(S/'session_result.json')['stagesStarted']
skipped=[name for name in ('desktop_readonly','idle_equivalence','generic_acquire','candidate_timing') if name not in started]
flag=lambda value:'PASS' if value else 'OPEN / not accepted'
compact=lambda value:json.dumps(value,ensure_ascii=False,separators=(',',':'))
report=f'''# S4b bounded row-refill qualification — {stamp}

**Native acceptance: {flag(q['nativeAccepted'])}. Genealogy is restored.**
The [sealed preparation](AB_S4B_REFILL_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b row-refill retry”, question
`call_a03c1071e32641f687cf1970bb701ef9:0`. This exact-session authorization is
consumed; it grants no subsequent controller changes.

## Target and unchanged shipping inputs

- Echo **601FC87B**, **1756-L81E v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `{q['canonicalSha256']}`.
- Generated source `{q['sourceSha256']}`.
- Exact-image Capacity **2,066,212 used /1,079,516 available /3,145,728 total
  Blocks (65%)**; this does not establish physical-controller fit.
- **{q['sourceBindingsVerified']} frozen inputs** verify after execution; only
  the SDK-saved working ACD differs. Original prepared and genealogy ACDs remain
  unchanged. The prepared client changes only row scheduling. No shipping PLC/HMI
  source is edited during runtime execution.

The production reader retains four serial-pinned read-only CIP connections,
one outstanding request per socket and one connection through each complete
guarded row. Full walks refill completed slots immediately, with at most four active
rows and one slot waiter. Count dependencies and the final Status phase drain
the entire active window. A failure stops further dispatch once observed and
drains started rows before refusal; targeted reads remain serial. Logical primitive-array consumption governs the published tiers;
fully excluded arrays cause no cyclic read, all-consumed-slow arrays follow the
existing heartbeat, and explicit targeted reads retain their original proofs.
The response-processing clock starts at worker receipt and includes its queue
through the original source-age boundary. Source/leaf age and complete-sample
accounting, fast Good/expiry **1/3 s**, slow **7.5/15 s**, desktop **20 attempts /
one second**, row proofs and direct read-only policy remain unchanged.

## Transient proof and full comparisons

Session-only apparatus warms canonical BOOL and legacy DINT public scalar paths
before the original first login. Warm samples establish no accepted values.
Immediately after the original acknowledgement, both busy values are compared
under the existing entire-scan equal-even generation proof: fresh scan edge,
at most **100 polls/five seconds**. Both must be valid, equivalent and busy.
The inherited full comparison follows and retains its actual later state.
Its failure still stops the fixture. The witness is **one path**, explicitly
separate from the required **87 full pairs**, and is never counted as one.
No additional PLC writes are introduced. Original 41 cases, refusal checks,
policy/document restoration and cleanup remain required.

Independent witness replay: `{compact(busy)}`.
Full comparison phases and raw frames remain in the fixture and capture files.
Missing busy state, mismatch, invalid reply/type or counter, frozen/changed
generation or proof exhaustion does not pass. The earlier missed-transient
attempt remains sealed separately. No cause of that prior miss is inferred
from this session's outcome.

## Recorded results

| Gate | Recorded outcome |
|---|---|
| Candidate cases | **{q['candidateCases']}/41** passed; groups `{compact(q['caseGroups'])}` |
| Independent full raw-read replay | **{q['pairedCapturesReplayed']}/87** full pairs; {q['pairedMinimumPaths']}–{q['pairedMaximumPaths']} paths |
| Short busy witness | {flag(busy.get('passed'))}; counted separately |
| Concurrent Dart observer | **{q['observerSamples']}** samples: **{q['allGoodSamples']}** entirely Good, {q['samplesWithUncertainRows']} with Uncertain, {q['samplesWithBadRows']} with Bad |
| Observer completion | {flag(q['observerPassed'])} |
| Complete reader/configuration/acquisition | {flag(q['nativeReaderPassed'])} |
| Configuration | {q['configurationPages']} pages; {q['configurationScalarComparisons']} independent exact scalar/type comparisons |
| Idle equivalence | {q['idlePaths']} paths; {flag(q['idlePassed'])} |
| Generic acquisition | {q['genericValues']} values /{q['genericModules']} modules |
| Strict LIVE desktop | {flag(q['desktopAccepted'])}; {coverage['modules']} modules /{coverage['fieldbusNodes']} bus nodes /{coverage['views']} views |
| Final scan acceptance | {flag(q['scanReviewPassed'])} |
| Genealogy rollback | **31/31 baseline**, five original documents, all final/preflight checks |

Sample age (ms): `{compact(q.get('sampleAgeMs'))}`.
RPC duration (us): `{compact(q.get('rpcUs'))}`.
Maximum accepted guarded-row window (us): `{compact(q.get('maximumAcceptedRowWindowUs'))}`.
Observer error: `{q['observerError']}`.
Fixture error: `{cases.get('error')}`.
Parent candidate error: `{q['sessionCandidateError']}`.
Skipped workflow stages: `{compact(skipped)}`.

Every completed pair is independently decoded from raw controller reads and
compared against the migration oracle, including values and logical types.
The four-page **1,100-value** configuration gate uses post-fixture oracle
records/ReadServices; it does not compare Dart results to themselves. Complete
idle/generic gates require **5,407** paths/values and seven modules. A partial
fixture/short observer run does not establish full workload acceptance.
Payload-free refusals are never counted as Good; missing stages are skipped.

## Desktop, scan and diagnostics

Final scan: `{compact(q.get('candidateScan'))}`.
Candidate read-only TASK epoch: `{compact(trace)}`.
TASK monitoring starts before download at nominal 100 ms. Read errors during
download remain in the trace. Separately read TASK scalars/polling do not
isolate an exact scan/routine or host cause. No counters are cleared.

Desktop uses the shipping factory/repository/UI and real quality/source age,
requiring LIVE/nonempty/full semantic coverage at every capture. Independent
parent validation requires **seven modules, three bus nodes and 31 views**.
Captured-fixture substitutions are disabled. Empty/STALE coverage cannot pass.
Desktop detail: `{compact(coverage)}`.
Measured frontend refusal/age components, if recorded:
`{compact(q.get('desktopFreshnessDiagnostics'))}`.

Original Part requests, three-attempt limit, projection and result/error
propagation remain unchanged. Session-only tracing forwards reads once and
excludes Part payload/UID and PIN. Part diagnostic summary:
`{compact({key:value for key,value in part.items() if key!='rows'})}`.
The opt-in `fraktal.cip.trace=true` phase log records worker queue, manifest/
progress, acquisition/projection/age selection/path expansion, assembly and
SendPort delivery; default builds keep tracing disabled. Phase summary:
`{compact({key:dict(snapshots=value['snapshots'],deliveries=value['deliveries'],phases=value['phases']) for key,value in cip.get('streams',{}).items()})}`.
Timings include instrumentation and scheduling. Missing phase records and
particular host/network/PLC causes are not inferred. Raw stdout/JSONL, slowest
groups and every failed proof remain archived.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores all five exact original host documents, runs **31/31** baseline cases,
restores policy and MANUAL/idle/logout, verifies saved/live equality and every
final/preflight check. Baseline scan: `{compact(q['baselineScan'])}`.
The original genealogy ACD is never opened. No dumps, fault/TASK-counter clears,
clock changes, power/vendor-state operations or Echo hard kills occur.

The preparation binds **14 unchanged apparatus tests**, six unchanged
Part-trace tests, fresh SDK (zero warnings/errors), authorization/workflow/
readiness and read-only refusal gates, plus spec/contracts/strict consistency/
whitespace and **74 root tests**. Failed offline runs remain archived.
**668 HMI tests pass /12 skipped**, **56 trace-enabled focused tests**, analyzer,
Windows build and enforced lockfile. The identical **319-input mirror** differs
only in the planner and pool tests. Three new cases prove immediate refill,
failure draining and invalid-concurrency refusal. The old planner fails the
held-sibling counterexample; the correction passes. Recorded-wire replay keeps
**810 reads /237 groups /976 exact consumed values/types**, with no hidden
ByClass reads. These replay counts are not native latency evidence. SDK:
Flutter **3.47.5 /Dart 3.13.4**. All **373 PLC/gate bindings**, **2,339 AB tests**,
both v38 build/read-back/access/SDK gates and exact-image **65% Capacity**
likewise transfer. Credentials and ACD/SDK binaries are excluded; approved
inputs remain hash-bound. Runtime stage exits retain every failed/skipped gate.

S4 acceptance is limited to the results above. S5 gateway/Web/installer, S6
classified legacy migration/retirement/persistence/events/capacity, and S7
physical/CIP Security including real I/O remain. Persistence medium, per-station
gateway write posture, hardware and commit/push policy remain owner decisions.
V2/Part III remain inactive. Nothing is committed or pushed.
'''
def save(path,value):
    with path.open('x',encoding='utf-8',newline='') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
with REPORT.open('x',encoding='utf-8',newline='') as stream:stream.write(report)
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower(),path
    raw=path.read_bytes();expanded=None
    if path.suffix.lower() in ('.log','.l5x','.jsonl'):
        expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(target),
        **(dict(expandedSha256=expanded) if expanded else {})))
for path in sorted(S.rglob('*')):
    if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.relative_to(S).parts):continue
    if path.suffix.lower() not in ('.py','.json','.gz','.log','.txt','.sha256','.l5x','.cs','.csproj','.dart','.png','.jsonl'):continue
    archive(path,'Runtime/'+path.relative_to(S).as_posix())
for name in ('authorize_refill_session_01.py','authorize_refill_session_01.log',
    'authorize_refill_session_01_exit.json','echo_guard_approved_01.log','echo_guard_approved_01_exit.json',
    'prepare_runtime_analysis_01.py','inspect_cold_runtime_01.py','replay_pairs_01.py','replay_login_busy_01.py',
    'compare_cold_config_pages_01.py','analyze_cold_task_trace_01.py','peek_runtime_progress_01.py',
    'summarize_runtime_01.py','parse_startup_timing_01.py','analyze_part_reads_01.py','analyze_cip_timing_01.py',
    'seal_runtime_01.py'):
    archive(W/name,'Analysis/'+name)
save(OUT/'manifest.json',dict(schema='fraktal.ab.s4b-refill-runtime',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    preparationManifestSha256=sha(prep),nativeAccepted=q['nativeAccepted'],nativeReaderPassed=q['nativeReaderPassed'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],candidateCases=q['candidateCases'],
    pairedCapturesReplayed=q['pairedCapturesReplayed'],shortBusyWitness=busy,rowRefillCorrection=q['rowRefillCorrection'],observerSamples=q['observerSamples'],
    baselineCases=31,genealogyRestored=True,finalChecksPassed=True,authorizationConsumed=True,
    currentControllerChangesAuthorized=False,credentialFilesArchived=False,acdBinariesArchived=False,
    sdkBinariesArchived=False,artifacts=artifacts,committed=False,pushed=False))
for row in artifacts:assert sha(OUT/row['path'])==row['sha256']
save(W/'sealed_runtime_01.json',dict(passed=True,report=REPORT.as_posix(),manifestSha256=sha(OUT/'manifest.json'),
    artifacts=len(artifacts),nativeAccepted=q['nativeAccepted'],nativeReaderPassed=q['nativeReaderPassed'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],genealogyRestored=True))
print(json.dumps(dict(sealed=True,report=REPORT.name,artifacts=len(artifacts),nativeAccepted=q['nativeAccepted'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],genealogyRestored=True)))

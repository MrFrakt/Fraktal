"""Archive the actual cold-start/desktop outcome after verified genealogy rollback."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
S=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
q=load(S/'runtime_summary_01.json')
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed']
assert q['authorizationConsumed'] and not q['currentControllerChangesAuthorized']
assert load(S/'authorization.json')['ApprovalQuestion']=='call_297cd0f6497b4493909e0f524643c7c9:0'
assert all(q[key]==0 for key in ('faultClears','taskCounterClears','clockChanges','powerOperations','hardKills'))
assert not q['dumpFiles']
stamp=datetime.datetime.now().astimezone().strftime('%Y-%m-%d')
kind='RUNTIME' if q['nativeAccepted'] else 'ATTEMPT'
name=f'AB_S4B_COLD_DESKTOP_{kind}_{stamp}'
OUT=E/name
REPORT=OUT.with_suffix('.md')
assert not OUT.exists() and not REPORT.exists()
prep=E/'AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26/manifest.json'
assert sha(prep)=='5c2833f6a8b45759c5417da9a11536e9926a883412cc8c60e4ddbcb80b4acf26'
def save(path,value):
    with path.open('x',encoding='utf-8',newline='') as f:
        json.dump(value,f,indent=2,ensure_ascii=False)
        f.write('\n')
def flag(value):return 'PASS' if value else 'OPEN / not accepted'
scan=q['candidateScan']
coverage=q['desktopCoverage']
age=q.get('sampleAgeMs')
window=q.get('maximumAcceptedRowWindowUs')
scan_text=(f"Median **{scan['lastScanMedianUs']:g} us**, cumulative maximum **{scan['cumulativeMaxUs']} us**, "
    f"**{scan['overlaps']} overlaps** on the 10,000 us task.") if scan else 'Final candidate timing was not reached.'
first=q.get('candidateTraceEpoch')
trace_text=(f"The candidate trace contains {first['rows']} valid observations; maximum recorded TASK value "
    f"{first['maxTaskScanUs']} us, overlap count {first['maxOverlapCount']}. "
    f"First published probe sample {first['first']['values']['Samples']}, last {first['last']['values']['Samples']}.") if first else 'No complete candidate trace epoch is available.'
report=f'''# S4b cold-start and strict desktop qualification — {stamp}

**Native acceptance: {flag(q['nativeAccepted'])}. Genealogy is restored.**
The [sealed preparation](AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md) was
approved by the owner: “Approve guarded S4b cold-start/desktop session”,
question `call_297cd0f6497b4493909e0f524643c7c9:0`. This exact-image approval
is consumed. No later controller changes are authorized by this record.

## Target and immutable image

- Local Echo **601FC87B**, 1756-L81E **v38.011**, 127.0.0.1 slot 0.
- Prepared ACD `{q['canonicalSha256']}`.
- Generated source `{q['sourceSha256']}`.
- Studio offline Capacity: **2,066,212 used /1,079,516 available /3,145,728
  total Blocks (65%)**. Native physical-controller fit is not covered.
- All **{q['sourceBindingsVerified']} source/gate/image bindings** matched before
  execution. Post-run verification permits only the SDK-saved working ACD
  to differ; original prepared image and genealogy rollback pin stay unchanged.

## Actual results

| Gate | Recorded outcome |
|---|---|
| Candidate fixture | {q['candidateCases']} successful cases; groups in `runtime_summary_01.json` |
| Independent raw-record replay | {q['pairedCapturesReplayed']} paired captures |
| Concurrent Dart observer | {q['observerSamples']} samples; {q['allGoodSamples']} entirely Good, {q['samplesWithUncertainRows']} with Uncertain, {q['samplesWithBadRows']} with Bad |
| Observer completion | {flag(q['observerPassed'])} |
| Full reader/configuration/acquisition scope | {flag(q['nativeReaderPassed'])} |
| Read-only configuration | {q['configurationPages']} pages; {q['configurationScalarComparisons']} exact oracle scalar/type comparisons |
| Idle equivalence | {q['idlePaths']} paths; {flag(q['idlePassed'])} |
| Generic acquisition | {q['genericValues']} values /{q['genericModules']} modules |
| Strict live desktop | {flag(q['desktopAccepted'])}; {coverage['modules']} modules /{coverage['fieldbusNodes']} fieldbus nodes /{coverage['views']} views |
| Startup/workload scan | {flag(q['scanReviewPassed'])} |
| Genealogy baseline | **31/31**, original five documents and all final/preflight checks passed |

Sample age statistics (ms): `{json.dumps(age)}`. Maximum accepted per-row
window statistics (us): `{json.dumps(window)}`. Payload-free refusals are not
counted as Good; strict root identity/freshness and the 20-attempt/one-second
policy remain unchanged. Read-only configuration pages are compared to the
independent post-fixture oracle, not to their own Dart values.

## Startup and desktop scope

{scan_text} {trace_text}
The monitor reads fixed TASK scalars at nominal 100 ms from before download
through candidate timing and stops before rollback. Temporary download read
errors remain in the raw trace. Separately read scalars and polling bound the
observations; they do not identify an exact offending scan or routine/host cause.
No counters are cleared. This image defers only cold first-scan view formatting
behind invalid publication/full-buffer clearing; retained access masking stays
immediate. Native evidence covers this approved local Echo workload only.

Desktop acceptance uses the production factory/repository/UI with genuine
source quality/age. The helper requires LIVE, a nonempty complete module forest,
correct tab selection, seven modules, three bus nodes and 31 views before it
can succeed. The parent independently validates semantic coverage. Refresh logs,
forest transitions, screenshots, test stdout/stderr and any failure record are
retained. Captured-fixture substitutions are disabled in live mode.

Desktop detail: `{json.dumps(coverage,ensure_ascii=False)}`.
Candidate error, if any: `{q['sessionCandidateError']}`. Missing later stages
are skipped after the first failure, never inferred successful from older runs.
The complete stage exits and raw result are archived.

## Rollback, gates and next work

The runner downloaded a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restored the five exact original host documents, ran 31/31 baseline cases,
restored policy, normalized MANUAL/idle/logout and passed final checks and
preflight. Baseline scan: `{json.dumps(q['baselineScan'])}`. The original
genealogy ACD was not opened. No dumps, fault/TASK-counter clears, clock
changes, power/vendor-state operations or Echo hard kills occurred.

The preparation binds **2,339 AB tests, 74 root tests, both v38 builds and
read-backs, access/SDK audits, 15 byte-identical prior images and 65% Capacity**.
Shipping HMI code/dependencies are unchanged: pinned Flutter 3.47.5 /Dart
3.13.4, **647 passed /12 skipped**, analyzer/Windows/enforced-lockfile proof
remains bound. The standalone desktop helper has its own analyzer, 31-view
positive rendering replay, expected stale/empty refusal and six coverage tests.
Runtime execution changes no shipping source. Credentials and ACD/SDK binaries
are excluded from this archive; their approved binary inputs are hash-bound.

S5 gateway/Web/installer, S6 classified legacy-reader migration/retirement,
persistence/events and capacity reductions, and S7 physical/CIP Security
including real I/O remain. S4 acceptance is limited to the actual outcome above.
V2/Part III remain inactive target drafts. Nothing is committed or pushed.
'''
with REPORT.open('x',encoding='utf-8',newline='') as f:f.write(report)
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower(),str(path)
    raw=path.read_bytes()
    expanded=None
    if path.suffix.lower() in ('.log','.l5x','.jsonl'):
        expanded=hashlib.sha256(raw).hexdigest()
        raw=gzip.compress(raw,mtime=0)
        relative+='.gz'
    target=OUT/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(target),
        **(dict(expandedSha256=expanded) if expanded else {})))
for path in sorted(S.rglob('*')):
    if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.relative_to(S).parts):continue
    if path.suffix.lower() not in ('.py','.json','.gz','.log','.txt','.sha256','.l5x','.cs','.csproj','.dart','.png','.jsonl'):continue
    archive(path,'Runtime/'+path.relative_to(S).as_posix())
for name in ('authorize_cold_session_01.py','build_runtime_analysis_01.py','inspect_cold_runtime_01.py',
    'replay_cold_pairs_01.py','compare_cold_config_pages_01.py','analyze_cold_task_trace_01.py',
    'peek_runtime_progress_01.py','summarize_runtime_01.py','seal_runtime_01.py',
    'authorize_session_01.log','authorize_session_01_exit.json','echo_guard_approved_01.log',
    'echo_guard_approved_01_exit.json'):
    archive(W/name,'Analysis/'+name)
save(OUT/'manifest.json',dict(schema='fraktal.ab.s4b-cold-desktop-runtime',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    preparationManifestSha256=sha(prep),nativeAccepted=q['nativeAccepted'],nativeReaderPassed=q['nativeReaderPassed'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],candidateCases=q['candidateCases'],
    pairedCapturesReplayed=q['pairedCapturesReplayed'],observerSamples=q['observerSamples'],baselineCases=31,
    genealogyRestored=True,finalChecksPassed=True,authorizationConsumed=True,currentControllerChangesAuthorized=False,
    credentialFilesArchived=False,acdBinariesArchived=False,sdkBinariesArchived=False,artifacts=artifacts,
    committed=False,pushed=False))
for row in artifacts:assert sha(OUT/row['path'])==row['sha256']
save(W/'sealed_runtime_01.json',dict(passed=True,report=REPORT.as_posix(),manifestSha256=sha(OUT/'manifest.json'),
    artifacts=len(artifacts),nativeAccepted=q['nativeAccepted'],nativeReaderPassed=q['nativeReaderPassed'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],genealogyRestored=True))
print(json.dumps(dict(sealed=True,report=REPORT.name,artifacts=len(artifacts),nativeAccepted=q['nativeAccepted'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],genealogyRestored=True)))

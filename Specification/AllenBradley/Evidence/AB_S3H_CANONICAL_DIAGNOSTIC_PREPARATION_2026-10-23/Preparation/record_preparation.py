from pathlib import Path
import hashlib,json
P=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
R=P.parent/'runtime_a1ce558b0f284b888339550fad1e179e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bindings=json.loads((R/'source_verification_failed_01.json').read_text())['sha256'];assert len(bindings)==159
for n,pin in bindings.items():assert sha(ROOT/n)==pin,n
assert sha(P/'s3h_canonical.ACD').upper()==sha(P/'capacity_review.ACD').upper()=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
assert sha(P/'s3h_candidate_03.L5X')=='e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315'
name='AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23'
summary=f'''**Latest, 2026-10-23: active-workload S3h diagnostic session prepared;
current authorization pending.** The failed paced retry is sealed: 39 exact
independent replays, first HELD coherence failure, successful rollback and all
31 baseline regressions. Larger message requests do not offer a useful path:
4,000/4,002 bytes connect; 8,000/16,000/60,000 are refused. An immediate-send
event-loop prototype does not establish a reliable latency gain and is not
in the implementation. No production reader/observer/PLC source changed.

A separate guarded wrapper now records per-window and generation-read timing,
keeps the last attempted raw frames explicitly unaccepted, and reads the eight
existing native TASK mirror scalars after an acquisition failure, before the
inherited fixture cleans up. It preserves the exact original exception,
100-poll/five-second history, four sockets/one pending request, comparisons
and all existing 41 candidate vectors. Evidence compression/writes happen
after the proof. Timing calls/in-memory rows add small observer overhead;
the native result will be labelled as instrumented diagnostics. Four wrapper
tests pass, including authorization refusal and error/history preservation.

All 159 existing source bindings remain exact, so their 2,149 AB / 74 root
tests and exact-image two-target v38/79% Capacity proofs apply. A fresh C6
image/helper is ready; fresh read-only baseline checks pass. No new native
write is authorized or performed. Proposed scope is the same guarded backup,
C6 download, inherited candidate fixture with diagnostics, and hash-checked
genealogy rollback/31 baseline checks/final cleanup. Failure still stops the
fixture and triggers rollback; there is no extra retry loop or acceptance claim.
Read [diagnostic preparation](Evidence/{name}.md). V2 stays inactive;
fault clears, clock changes, commit and push remain excluded.

'''
for filename,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/filename;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: the paced S3h retry stops at active HELD coherence;',
             '**Earlier paced S3h retry stops at active HELD coherence;',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8')
t=t.replace('**Latest, 2026-10-23: the paced S3h retry stops at active HELD coherence;',
            '**Earlier paced S3h retry stops at active HELD coherence;',1)
p.write_text(t.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
d['approvedTraceabilityCorrection'].update(diagnosticPrepared=True,diagnosticPreparationEvidence='Evidence/'+name+'.md',
 diagnosticWorkspace=P.as_posix(),diagnosticControllerChangesAuthorized=False,diagnosticWrapperTests=4,
 diagnosticScope='unchanged fixture/proof plus wire timing and eight read-only TASK mirrors after failure; not a transport fix or acceptance claim')
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h active-workload diagnostic preparation — 2026-10-23

**S3h is incomplete. No new controller-changing operation is authorized or
performed.** The [paced native retry](AB_S3H_CANONICAL_PACED_RETRY_ATTEMPT_2026-10-23.md)
has 39 exact independently replayed comparisons, then a failed first HELD
capture: all 17 complete windows cross a scan boundary. Genealogy rollback,
strict read-back, 31 regressions and final readiness pass. Its approval is
consumed. Baseline timing proxies do not establish active-workload timing.

This preparation adds only a separate timing wrapper around the unchanged
fixture/observer. It records monotonic start/end times for each acquisition
and generation read, retains the last attempted frames labelled unaccepted,
and reads eight existing TASK mirror scalars immediately after a failed proof,
before inherited fixture cleanup. The exact original exception and attempt
history propagate unchanged. No extra attempt, comparison tolerance, cache,
packet omission, task-period change or fixture vector is introduced. Four
sockets retain one pending read each; 47 packets and 100 polls/five seconds
remain. Timing calls and bounded in-memory rows add observer overhead inside
the proof; all frame serialization/compression/file I/O follow its completion.
Instrumentation can affect timing, so results are diagnostic observations.

Read-only post-failure scalars are FRK_Press_CanonicalTiming.Scan,
LastScanUs, MaxScanUs, OverlapCount and FRK_Press_HealthProbe.Samples,
TaskLastScanUs, TaskMaxScanUs, TaskOverlapCount. They exist in this exact image
and are the same mirrors used by the stage's existing timing tool. A failed
diagnostic read cannot mask or replace the original proof failure. The wrapper
requires current exact-image approval plus ReadTimingDiagnosticsAuthorized.
It delegates every tag write to the inherited fixed-vector fixture.

| Gate | Result |
|---|---|
| Wrapper tests | Four pass: current authority required; successful proof unchanged/no added TASK reads; original failure/100 polls preserved; diagnostic read error does not mask failure |
| Existing AB/root suites | 2,149 / 74 pass, reused by all 159 unchanged source hashes |
| Source/image | Native source E83B9A2C…567315 and ACD C6B42327…5D7D9DC remain byte-identical; no production source changes |
| Both v38 build/read-back/access | Exact-image sealed proofs reused; current prepared read-back/access pass |
| Capacity | Exact-image automatic 79%: 2,501,720 used / 644,008 available / 3,145,728 total Blocks; no accepted S3h calibration entry |
| Helper | Fresh one-shot workspace and untouched C6 copy; .NET helper build passes |
| Baseline | Fresh read-only preflight/final checks pass: Run/not faulted/Remote/scanning, MANUAL/idle/logout, five saved/live documents and policy equal |
| Current native diagnostic | Not executed; approval template false |

Read-only transport experiments are retained. At 4,000/4,002-byte negotiated
sizes the first fragment is 3,988/3,990 bytes. Echo refuses 8,000, 16,000 and
60,000-byte requests. A prototype that sends the next read immediately after
the preceding response passes framing/ownership tests and exact immutable
payload checks, but its 100-sample median is 8,161.95 µs (maximum 17,016.90),
so no reliable gain is established and it is not adopted. None of these
experiments writes a tag, changes mode, clears a fault or changes a clock.

Prepared ACD SHA-256:
`C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC`.
Generated source SHA-256:
`e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315`.
The immutable genealogy original is never opened. ACD binaries and credentials
are not archived. Work folder: `{P.as_posix()}`.

Proposed current session: local Echo 601FC87B, 127.0.0.1 slot 0, v38.011;
guarded MANUAL normalization when needed, fresh backup, Program/download/Run
of the exact C6 image, five-document restore and the unchanged inherited 41
candidate checks with this read-only instrumentation. At the first failure
the fixture stops and rolls back, retaining timing/TASK/raw-frame diagnostics.
If all checks pass, existing idle/generic/sizes/scan steps still run. Then
hash-checked genealogy rollback, five-document restore, 31 baseline regressions,
MANUAL cleanup and final readiness/preflight checks. No new tag-write vector,
fault clear or clock change. AGENTS.md §3a requires current explicit approval
for this new session. It is a diagnostic run, not a promised acceptance retry.

Payload: [manifest]({name}/manifest.json). The 33 earlier canonical seals and
8,072 artifacts remain unchanged. V2 remains inactive; no commit or push.
'''
with (AB/'Evidence'/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
with (P/'source_bindings_01.json').open('x') as f:
 json.dump(dict(passed=True,projectSourceBindings=159,sha256=bindings,projectSourcesUnchanged=True,
  diagnostics={n:sha(P/n) for n in ('diagnostic_fixture_execute.py','test_diagnostic_fixture_execute.py')}),f,indent=2)
print(json.dumps(dict(passed=True,diagnosticPrepared=True,controllerChanges=0,currentOwnerApprovalPending=True)))

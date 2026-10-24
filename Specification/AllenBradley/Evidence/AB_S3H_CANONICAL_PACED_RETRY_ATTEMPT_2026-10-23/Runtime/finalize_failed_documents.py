from pathlib import Path
import json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
v=json.loads((R/'failed_session_closure_01.json').read_text());assert not v['stageAccepted'] and v['baselineRestored']
replay=json.loads((R/'partial_replay_01.json').read_text());assert replay['passed'] and replay['captures']==39
assert json.loads((R/'restore_readback_01.log').read_text())['Equivalent']
name='AB_S3H_CANONICAL_PACED_RETRY_ATTEMPT_2026-10-23'
summary=f'''**Latest, 2026-10-23: the paced S3h retry stops at active HELD coherence;
genealogy is restored.** All 39 Access/configuration captures compare and replay
exactly from native bytes and independently reconstructed owner/provider contexts.
The two Access and eight configuration cases pass, but the first HELD capture
fails before comparison: 100 polls contain 77 unchanged-even waits, six odd
polls and 17 complete read windows; every window crosses one scan boundary.
Pacing removed the earlier tight-poll starvation but did not establish active
workload timing. The 1,000 baseline proxy passes do not transfer to this active
HELD state. No path, type or value mismatch was observed in an accepted pair.

Candidate cleanup, hash-checked rollback, all 31 baseline regressions, strict
rollback read-back and final Run/not-faulted/Remote/scanning, MANUAL=1/idle/
logout/not-restoring, five saved/live documents and original policy/preflight
equality pass. All 159 sources remain unchanged; 2,149 AB / 74 root tests and
the exact-image compiler/79% Capacity proofs still apply. The current session
approval is consumed. No fault clear, clock change, commit or push occurred.

S3h remains incomplete. Complete inherited/active/traceability checks, generic
idle acquisition and candidate TASK timing were not reached. No accepted
Capacity calibration sample is added; V2 stays inactive. The next task is to
reduce and instrument active-workload acquisition latency, keeping the same
100-poll/five-second positive equal-even proof. Read
[paced retry attempt](Evidence/{name}.md). No further download is authorized.

'''
for filename,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/filename;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: paced S3h retry prepared; current authorization pending.**',
             '**Earlier paced S3h retry preparation (attempt completed above):**',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8')
t=t.replace('**Latest, 2026-10-23: paced S3h retry prepared; current authorization pending.**',
            '**Earlier paced S3h retry preparation (attempt completed above):**',1)
p.write_text(t.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
m=d['approvedTraceabilityCorrection'];m.update(runtimeAccepted=False,controllerChangesAuthorized=False,
 sessionAuthorizationConsumed=True,lastNativeAttempt='Evidence/'+name+'.md',lastNativeAttemptPassed=False,
 partialPairedCaptures=39,independentPartialReplays=39,baselineRestored=True,sourceBindings=159,
 retryPrepared=False,retrySessionConsumed=True,remainingNativeGates=[
 'active HELD acquisition latency within unchanged 100-poll/five-second proof',
 'complete 41 candidate checks and traceability coverage','final generic/idle acquisition and candidate scan',
 'successful complete native session with rollback'])
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h paced native retry — 2026-10-23

**S3h remains incomplete. Genealogy is restored.** The owner approved
`call_9b203bdff24848999469abe17a76ee4f:0`, “Approve this guarded paced S3h
retry”, on local Echo `601FC87B`, 127.0.0.1 slot 0, 1756-L81E v38.011.
The completed session consumes that authorization. No fault clear or clock
change occurred, and no further native session is authorized by it.

| Gate | Result |
|---|---|
| Fresh guards/preflight/backup | Pass, Save As SDK and baseline access audits |
| Original C6 image deployment | Program/download/Run; SDK log, strict source read-back/access and guards pass |
| Candidate Access/configuration | Two Access and eight configuration cases pass, 39 passing paired captures |
| Independent replay | All 39 snapshots re-decoded from native frames and reconstructed legacy/provider contexts; exact values/types with five D2 bounds |
| Capture path counts | {sorted(set(r['paths'] for r in replay['rows']))}; occupied host count and page window remain PLC-published |
| Passing capture polls | {replay['attempts']['minimum']}–{replay['attempts']['maximum']}, within 100 polls/five seconds |
| First HELD capture | PressRam, ST rendition; no same-scan proof, so comparison is refused |
| Failure history | 100 polls: 77 unchanged-even waits, six odd, 17 complete read windows; all 17 cross one scan boundary |
| Fixture matrix | Incomplete: zero inherited final rows; ten Access/config cases pass; planned 41 candidate cases unaccepted |
| Candidate cleanup / rollback | Restored inputs/policy, hash-checked genealogy copy, SDK log/access and strict sealed-reference read-back pass |
| Baseline | 31/31 regressions pass; five documents restored |
| Final checks | Run/not faulted/Remote/scanning; MANUAL=1/idle/logout/not restoring; saved/live documents and policy/preflight equal |
| Candidate idle/generic/TASK/complete traceability | Skipped after failure, remain open |
| Native sizes from accepted pairs | 133,744 root + 7,308 definitions + 16,616 alarm metadata = 157,668 bytes |
| Capacity | Exact-image automatic 79%: 2,501,720 used / 644,008 available / 3,145,728 total Blocks; not added as accepted calibration |
| Source/offline gates | All 159 sources unchanged during session; 2,149 AB / 74 root tests; both v38 build/read-back/access proofs reused by exact source/image hash |
| Fault clear / clock change / commit / push | None |

The one-millisecond unchanged-even wait prevented tight polling from consuming
nearly all attempts, and 39 comparisons pass. However, all 17 active HELD read
windows cross a scan boundary. The baseline proxy's 1,000 successes do not
establish timing on this active workload. This is a coherence/acquisition
failure; accepted captures show no value or type mismatch. No timing-cost
measurement is invented for the active state, because candidate TASK timing
was not reached. The cause needs active-workload instrumentation and transport
latency work before another acceptance retry is proposed.

The positive equal-even whole-scan proof, 100 polls/five seconds including
waits, four sockets with one outstanding read each, complete 47-packet byte
coverage, task period, source image, fixture stimuli and comparisons remain
unchanged. No extra native attempt or reduced validation was added. Candidate
and final baselines use the already approved fixed-vector scope only.

Prepared ACD SHA-256: `{v['preparedAcdSha256']}`.
Generated source SHA-256: `{v['sourceSha256']}`.
SDK-saved spent ACD SHA-256: `{v['sdkSavedAcdSha256']}`.
Fresh backup SHA-256: `{v['backupAcdSha256']}`.
The immutable genealogy original was hash-checked/copied, never opened.
Credentials and native ACD binaries are not archived.

Work folder: `{R.as_posix()}`. Payload:
[manifest]({name}/manifest.json). All earlier evidence remains sealed unchanged.
V2 is inactive; later S3 surfaces and S4–S7 remain open. No new download is
authorized. This failed run and all exact outputs are retained.
'''
with (AB/'Evidence'/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(passed=True,stageAccepted=False,baselineRestored=True,approvalConsumed=True,partialReplays=39)))

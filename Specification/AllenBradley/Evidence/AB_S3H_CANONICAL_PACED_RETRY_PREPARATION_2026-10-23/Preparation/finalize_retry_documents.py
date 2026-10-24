from pathlib import Path
import json,re
P=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
W=P.parent/'transport_ae4489870e334fefaf4d7d28580708cc'
proxy=json.loads((P/'scan_start_proxy_01.json').read_text());assert proxy['passed'] and len(proxy['samples'])==1000
found=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(W/'ab_suite_01.log').read_text());assert found and int(found[1])==2149
assert json.loads((P/'source_bindings_01.json').read_text())['passed']
assert json.loads((P/'final_readonly_01.json').read_text())['passed']
name='AB_S3H_CANONICAL_PACED_RETRY_PREPARATION_2026-10-23'
summary=f'''**Latest, 2026-10-23: paced S3h retry prepared; current authorization pending.**
The prior retry is sealed with genealogy restored and all 31 baseline checks
passing. Its failed capture spent 93/100 polls waiting for a fresh generation.
The observer now waits one millisecond after an unchanged even generation.
Every poll and wait remains inside the same 100-attempt/five-second gate;
the next iteration checks the deadline before another read. Closing positive
equal-even proof, four connections, one pending request each, all 47 packets,
post-window decoding, PLC image and candidate stimuli are unchanged.

The installed four-connection observer passes 1,000 consecutive read-only
baseline proxy captures in {proxy['attemptsObserved']['minimum']}–{proxy['attemptsObserved']['maximum']} polls.
These use the legacy scan counter and immutable payloads and do not establish
S3h canonical acceptance. An eight-connection experiment showed similar median
latency; it is retained as an experiment and is not shipped. All 2,149 AB tests
({found[2]} s), 74 root tests and strict cheap gates pass. The 159-file source
closure differs only in the pacing implementation and its test. Regeneration
is byte-identical to source E83B9A2C…567315 and ACD C6B42327…5D7D9DC, so the
existing two-target v38 compiler/read-back/access and 79% automatic Capacity
proofs apply. A fresh one-shot helper builds with zero warnings/errors.

Fresh read-only preflight/readiness checks pass on restored genealogy. No new
download, mode change or tag write is authorized or performed. The next native
scope remains fresh backup, this exact image, 41 candidate checks/read-only
equivalence and scan, genealogy rollback and 31 baseline checks/final cleanup.
Fault clears and clock changes remain excluded. S3h remains incomplete and V2
inactive; no commit or push. Read
[paced retry preparation](Evidence/{name}.md).

'''
for file,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/file;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: the guarded S3h retry failed the coherence gate;',
             '**Earlier guarded S3h retry failed the coherence gate;',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8')
t=t.replace('**Latest, 2026-10-23: the guarded S3h retry failed the coherence gate;',
            '**Earlier guarded S3h retry failed the coherence gate;',1)
p.write_text(t.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
m=d['approvedTraceabilityCorrection'];m.update(runtimeAccepted=False,controllerChangesAuthorized=False,
 retryPrepared=True,retryPreparationEvidence='Evidence/'+name+'.md',abTests=2149,sourceBindings=159,
 retrySourceBindings=159,unchangedEvenWaitSeconds=.001,qualifiedBaselineProxyCaptures=1000,
 retryWorkspace=P.as_posix(),allWaitingPollsWithinOriginalBudget=True)
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h paced retry preparation — 2026-10-23

The exact original S3h image is ready for a newly authorized local Echo session.
**No new controller-changing operation is authorized or performed. S3h is not
accepted.** The [previous retry](AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md)
is sealed: three exact pairs, coherence failure, verified genealogy rollback,
31 baseline regressions and final checks. Its approval is consumed.

Only the read-only observer pacing and its unit test change. After an unchanged
even generation, the observer waits one millisecond before the next iteration.
The wait counts toward the same five-second deadline; all polls count toward
the same 100 attempts. The next iteration checks the deadline before reading.
The positive equal-even closing proof, complete byte/path coverage, four sockets,
one outstanding request per socket, 47 native reads, post-window decoding, PLC
task period, source image and fixture stimuli are unchanged. Earlier stages
using default scheduling are unaffected. No budget, tolerance or cache changes.

| Gate | Result |
|---|---|
| AB suite by tools discovery | 2,149 pass in {found[2]} s |
| Root suites | 74 pass |
| Focused pacing test | Unchanged-even wait only; every poll retained; wait consumes original time budget |
| Spec/contracts/strict consistency/whitespace | Pass; exact logs archived |
| Source closure | 159 files; exactly pacing module and its test differ from the sealed failed retry |
| Installed observer proxy | 1,000 consecutive four-socket captures pass, original 100 polls/five seconds |
| Proxy attempt range | {proxy['attemptsObserved']['minimum']}–{proxy['attemptsObserved']['maximum']} polls |
| Proxy acquisition latency | min/median/max {proxy['latencyUs']['minimum']:.2f} / {proxy['latencyUs']['median']:.2f} / {proxy['latencyUs']['maximum']:.2f} µs |
| Proxy scope | Legacy scan counter over repeated immutable Access audit/data policy bytes; not canonical S3h acceptance |
| Byte/stream checks | All 47 response payloads exact; closing generation reads succeed; one pending request per connection |
| Native image | Exact original source E83B9A2C…567315 and ACD C6B42327…5D7D9DC; new regeneration/read-back/access pass |
| v38 / Capacity | Reused by exact image hash; both target build/read-back/access proofs; 2,501,720 / 644,008 / 3,145,728 used/available/total Blocks (79%) |
| Session helper | Fresh one-shot workspace; compile passes with zero warnings/errors |
| Current genealogy | Fresh read-only preflight/readiness pass; Run/not faulted/Remote/scanning, MANUAL/idle/logout, five saved/live documents and policy equal |
| Candidate native acceptance | Pending new current approval; 41 candidate + 31 baseline checks planned |

The four-socket paced prototype first passed 250 captures; the eight-socket
prototype passed 100 with similar median latency. Four sockets are retained.
Eight sockets are not in shipping code. The prototype initially failed to import
the repository-relative contract from a shallow work folder; extracting only
the scheduling function corrected the diagnostic harness. A fresh helper build
initially failed because --no-restore omitted its new assets file; a normal
restore/build then passed. All failed logs and executed prototype versions remain
archived. Neither diagnostic failure changed a controller.

ACD SHA-256: `C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC`.
Generated source SHA-256:
`e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315`.
The fresh image was copied from an untouched hash-checked review ACD; no spent
download image or immutable genealogy original was opened. ACD binaries and
credentials are not archived. Work folder: `{P.as_posix()}`.

Proposed session on local Echo `601FC87B`, 127.0.0.1 slot 0, v38.011:
guarded MANUAL normalization when needed; fresh backup; Program/download/Run;
five-document restore and 41 candidate checks with read-only comparisons,
traceability/decision/held/fault/sequence/reset/Access/config captures, sizes
and TASK timing; hash-checked genealogy rollback, five-document restore and
31 baseline regressions; MANUAL cleanup and final readiness/preflight checks.
Fault clears and clock changes remain excluded. AGENTS.md §3a requires current
explicit approval for a new session. V2 stays inactive; no commit or push.

Payload: [manifest]({name}/manifest.json). Earlier evidence remains unchanged.
'''
with (AB/'Evidence'/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(passed=True,retryReady=True,currentOwnerApprovalPending=True,controllerChanges=0)))

from pathlib import Path
import hashlib,json,re
P=Path(__file__).parent;W=P.parent/'transport_2eff7b66442a4322a987fb2f7812268b';ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
assert json.loads((W/'ab_suite_02_exit.json').read_text())['exitCode']==0
tests=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(W/'ab_suite_02.log').read_text());assert tests and int(tests[1])==2148
proxy=json.loads((P/'scan_start_proxy_01.json').read_text());assert proxy['passed'] and len(proxy['samples'])==20
binding=json.loads((P/'source_bindings_02.json').read_text());assert binding['sourceBindings']==159
pin=(P/'canonical.sha256').read_text().strip()
summary=f'''**Latest, 2026-10-23: S3h retry prepared; current session approval pending.**
The failed attempt remains sealed and genealogy remains restored. A qualified
read-only observer now multiplexes four sockets with one pending request each,
and starts acquisition on a newly completed generation. Every waiting poll
counts against the original 100 attempts/five seconds. The closing equal-positive-
even proof, complete byte coverage and post-window decoding are unchanged.
Twenty baseline timing-proxy captures pass in 4–32 polls, with identical bytes;
these are transport diagnostics, not S3h canonical acceptance.

All 2,148 AB tests ({tests[2]} s), 74 root tests and the focused transport/
scan-start tests pass. The source closure binds 159 files. Source L5X and ACD
are byte-identical to the original qualified S3h image: `{pin[:8]}...{pin[-7:]}`.
Both v38 build/read-back/access and automatic Capacity (79%) gates are reused
by exact hash. A fresh one-shot helper/workspace is ready; no retry controller
operation is authorized. Next requires current approval for backup, this exact
download, 41 candidate checks/read-only captures, genealogy rollback and 31
baseline checks. No fault clear, clock change, commit or push. V2 remains inactive.
Read [retry preparation](Evidence/AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23.md).

'''
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md'):
    p=AB/name;t=p.read_text(encoding='utf-8')
    anchor='**Latest, 2026-10-23: S3h native attempt stopped at the coherence gate;'
    assert t.count(anchor)==1;t=t.replace(anchor,summary+'**Earlier S3h native attempt stopped at the coherence gate;',1);p.write_text(t,encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8');t=t.replace('\n\n','\n\n'+summary,1);p.write_text(t,encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';data=json.loads(p.read_text());assert not data['active'];m=data['approvedTraceabilityCorrection']
m.update(runtimeAccepted=False,controllerChangesAuthorized=False,retryPrepared=True,
    retryPreparationEvidence='Evidence/AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23.md',
    retrySourceBindings=159,abTests=2148,rootTests=74,readTransport='four sockets, one outstanding read each, single multiplex owner',
    freshCompletedGenerationScheduling=True,allWaitingPollsWithinOriginalBudget=True)
p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h canonical retry preparation — 2026-10-23

The retry is prepared for local Echo `601FC87B`, 127.0.0.1 slot 0, v38.011.
**No retry download, mode change or tag write is authorized or performed.**
The [first native attempt](AB_S3H_CANONICAL_ATTEMPT_2026-10-23.md) remains
sealed: ten exact pairs, then a coherence timeout, successful rollback and
all 31 baseline regressions. Its authorization is consumed. S3h is incomplete.

Only the acceptance observer and tests change. One event loop owns four
prewarmed sockets, with at most one request outstanding per connection.
Responses must match their session and sequence; explicit zero sender context
matches measured Echo behavior. Partial sends/receives, framing, bounds,
write-service refusal, early EOF and close-on-error are covered. UDT decoding
and fragment reassembly still follow the closing generation sample.

Acquisition begins after observing a newly completed generation, avoiding a
late start in an already partly elapsed scan. All initial/waiting/odd polls
remain in the **same 100-attempt/five-second history**. The positive equal-even
closing proof, no-tolerance comparison, complete path/byte coverage, four
connections, task period, PLC source and regression stimuli are unchanged.
Default scheduling for earlier stages remains unchanged. No extra read budget,
retry loop, hidden field or stale-state cache was added.

| Gate | Result |
|---|---|
| AB discovery suite | 2,148 pass in {tests[2]} s |
| Root suites | 74 pass |
| Focused checks | Socket framing/ownership/EOF/refusal; four-owner proof/decode ordering; fresh-edge waits, unchanged attempt/time limits |
| Strict specification/contracts/consistency/whitespace | Pass; exact outputs archived |
| Native baseline byte qualification | 47 requests / four connections; 20 samples per mode; exact immutable fragment/MSP payloads and drained streams |
| Timing proxy | Twenty successful captures; 4–32 polls under 100/five seconds; acquisition median 7,891.45 µs, range 6,282.60–9,234.10 µs |
| Timing-proxy scope | Legacy counter over immutable baseline records; **not canonical S3h same-scan acceptance** |
| Repeated latency observations | Variable: first comparison medians 10,971.95 / 8,276.20 µs; direct installed-module comparison 9,660.75 / 9,523.30 µs. No guaranteed latency claim |
| Source bindings | 159 files; PLC generator, publisher and generic reader/manifest/acquirer unchanged |
| Native image | Exact original source and ACD hashes; compiler/read-back/access and automatic Capacity proofs remain applicable |
| Capacity | Exact-image reuse: 2,501,720 used / 644,008 available / 3,145,728 total Blocks (79%); no accepted calibration entry added |
| Retry workspace | Fresh one-shot helper compiles; original C6 image copied from its untouched review copy, not the spent download ACD |
| Current baseline | Fresh read-only readiness/preflight checks pass; five saved/live documents and policy match |
| S3h native retry | Pending new current authorization; planned 41 candidate + 31 baseline checks |

The experiments are retained. Pipelining multiple requests per connection
failed identifier matching and completion on Echo, and is not in the observer.
A TCP_NODELAY experiment did not establish a latency improvement and is not
used. An initial source-binding check stopped on LF/CRLF differences; normalized
source equality and direct qualification of the installed module correct the
check without changing wire validation. All failed probes/logs remain archived.

Approved native ACD SHA-256: `{pin}`.
Generated source SHA-256:
`e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315`.
Both are byte-identical to [the original preparation](AB_S3H_CANONICAL_PREPARATION_2026-10-23.md).
The native binaries remain local and are never archived; the immutable genealogy
original is never opened. Work folder: `{P.as_posix()}`.

Proposed scope: guarded MANUAL normalization when needed; fresh backup;
Program/download/Run of this exact image; five-document restore and 41 candidate
checks with complete read-only captures, equivalence/sizes/scan; hash-checked
genealogy rollback, five-document restore and 31 baseline regressions; MANUAL
cleanup/final checks. No added direct traceability writes, fault clears or clock
changes. AGENTS.md §3a requires current explicit approval for this new session.

Payload: [manifest](AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23/manifest.json).
V2 remains inactive. No commit or push. Physical/CIP Security and later stages
remain separate gates.
'''
with (AB/'Evidence/AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23.md').open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(passed=True,retryPrepared=True,controllerChangesAuthorized=False,abTests=2148,
    abSeconds=float(tests[2]),sourceBindings=159,preparedAcdSha256=pin)))

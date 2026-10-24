# S3h canonical retry preparation — 2026-10-23

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
| AB discovery suite | 2,148 pass in 270.165 s |
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

Approved native ACD SHA-256: `C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC`.
Generated source SHA-256:
`e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315`.
Both are byte-identical to [the original preparation](AB_S3H_CANONICAL_PREPARATION_2026-10-23.md).
The native binaries remain local and are never archived; the immutable genealogy
original is never opened. Work folder: `C:/work/fraktal-ab-s3h-20261023/retry_9d1da9a04d564b03bc2b176f5b17ea42`.

Proposed scope: guarded MANUAL normalization when needed; fresh backup;
Program/download/Run of this exact image; five-document restore and 41 candidate
checks with complete read-only captures, equivalence/sizes/scan; hash-checked
genealogy rollback, five-document restore and 31 baseline regressions; MANUAL
cleanup/final checks. No added direct traceability writes, fault clears or clock
changes. AGENTS.md §3a requires current explicit approval for this new session.

Payload: [manifest](AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23/manifest.json).
V2 remains inactive. No commit or push. Physical/CIP Security and later stages
remain separate gates.

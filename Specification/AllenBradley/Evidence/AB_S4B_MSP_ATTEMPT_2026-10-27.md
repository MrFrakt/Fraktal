# S4b read-only body-packet qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_MSP_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b body-packet qualification”, question
`call_2e3b8f619b2a46728c4e2e0627acc9c2:0`. This exact-session authorization is
consumed; it grants no subsequent controller changes.

## Target and unchanged shipping inputs

- Echo **601FC87B**, **1756-L81E v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Exact-image Capacity **2,066,212 used /1,079,516 available /3,145,728 total
  Blocks (65%)**; this does not establish physical-controller fit.
- **1081 frozen inputs** verify after execution; only
  the SDK-saved working ACD differs. Original prepared and genealogy ACDs remain
  unchanged. The prepared client batches only count/body reads between separately completed counters. MSP execution order is not assumed. No shipping PLC/HMI
  source is edited during runtime execution.

Fitting count/body reads use one bounded read-only MSP after the pre-counter
request completes and before the post-counter request starts. No counter is
folded into the packet. Reply services/types/handles/extents and both packet
budgets remain strict; only symbolic Read Tag Fragmented requests are allowed.
Large/data-dependent rows keep the original path. Unsupported/partial replies
fall back within the same attempt/window/deadline. Malformed responses refuse.
No intra-packet ordering or atomicity assumption is made.

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

Independent witness replay: `{"controllerAccess":false,"fullComparison":false,"fullPairsAdded":0,"passed":true,"recorded":true,"capturePassed":true,"paths":1,"generation":4170,"attempts":3,"valueEquivalent":true,"busyObserved":true,"manifestHash":"3B765353B71891ED750D331CE11B5DDCE7D1663A06837C4C1EB0FC90FA3346AA"}`.
Full comparison phases and raw frames remain in the fixture and capture files.
Missing busy state, mismatch, invalid reply/type or counter, frozen/changed
generation or proof exhaustion does not pass. The earlier missed-transient
attempt remains sealed separately. No cause of that prior miss is inferred
from this session's outcome.

## Recorded results

| Gate | Recorded outcome |
|---|---|
| Candidate cases | **41/41** passed; groups `{"rows":{"expected":31,"recorded":31,"passed":31},"s4bAccessRows":{"expected":2,"recorded":2,"passed":2},"s4bConfigRows":{"expected":8,"recorded":8,"passed":8}}` |
| Independent full raw-read replay | **87/87** full pairs; 4799–5407 paths |
| Short busy witness | PASS; counted separately |
| Concurrent Dart observer | **2851** samples: **2851** entirely Good, 0 with Uncertain, 0 with Bad |
| Observer completion | PASS |
| Complete reader/configuration/acquisition | OPEN / not accepted |
| Configuration | 4 pages; None independent exact scalar/type comparisons |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict LIVE desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Final scan acceptance | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, five original documents, all final/preflight checks |

Sample age (ms): `{"minimum":142.255,"median":209.959,"p95":259.133,"maximum":346.397}`.
RPC duration (us): `{"minimum":153455,"median":220433,"p95":270079,"maximum":397700}`.
Maximum accepted guarded-row window (us): `{"minimum":2990,"median":4767,"p95":6729,"maximum":9998}`.
Observer error: `None`.
Fixture error: `None`.
Parent candidate error: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-msp-20261027\\session_01\\run_logged.py', 'desktop_readonly', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-msp-20261027\\session_01\\desktop_readonly.py']' returned non-zero exit status 1.`.
Skipped workflow stages: `["idle_equivalence","generic_acquire","candidate_timing"]`.

Every completed pair is independently decoded from raw controller reads and
compared against the migration oracle, including values and logical types.
The four-page **1,100-value** configuration gate uses post-fixture oracle
records/ReadServices; it does not compare Dart results to themselves. Complete
idle/generic gates require **5,407** paths/values and seven modules. A partial
fixture/short observer run does not establish full workload acceptance.
Payload-free refusals are never counted as Good; missing stages are skipped.

## Desktop, scan and diagnostics

Final scan: `null`.
Candidate read-only TASK epoch: `{"epoch":1,"rows":7548,"first":{"row":337,"elapsedUs":34026430,"utc":"2026-10-28T01:44:31.413639+00:00","values":{"Samples":0,"TaskLastScanUs":0,"TaskMaxScanUs":0,"TaskOverlapCount":0}},"last":{"row":7884,"elapsedUs":794941367,"utc":"2026-10-28T01:57:12.311306+00:00","values":{"Samples":75625,"TaskLastScanUs":965,"TaskMaxScanUs":9002,"TaskOverlapCount":0}},"maxTaskScanUs":9002,"maxOverlapCount":0,"firstObservedOverlap":null}`.
TASK monitoring starts before download at nominal 100 ms. Read errors during
download remain in the trace. Separately read TASK scalars/polling do not
isolate an exact scan/routine or host cause. No counters are cleared.

Desktop uses the shipping factory/repository/UI and real quality/source age,
requiring LIVE/nonempty/full semantic coverage at every capture. Independent
parent validation requires **seven modules, three bus nodes and 31 views**.
Captured-fixture substitutions are disabled. Empty/STALE coverage cannot pass.
Desktop detail: `{"accepted":false,"modules":0,"views":0,"fieldbusNodes":0,"error":"Expected: LinkState:<LinkState.live>\n  Actual: LinkState:<LinkState.stale>\nafter-overview\n","link":"stale","localWriteRefusals":2,"fixtureClientWriteCalls":null,"nativeWireWriteCountMeasured":false}`.
Measured frontend refusal/age components, if recorded:
`{"passed":true,"readOnly":true,"controllerAccess":false,"observations":[{"sourceAgeUs":737967,"rpcUs":1107987,"transitUs":309690,"receivedAgeUs":1047657,"localProcessingUs":4066,"effectiveAgeUs":1051723,"fastGoodUs":1000000,"snapshotAwaitUs":1107964,"serviceDecodeUs":7,"validationUs":1,"responseProcessingMs":799.297,"excessUs":51723,"sourceAlreadyLate":false,"lateAtReceipt":true,"localProcessingCrossedBoundary":false}],"refusalReproduced":true,"interpretation":"Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred."}`.

Original Part requests, three-attempt limit, projection and result/error
propagation remain unchanged. Session-only tracing forwards reads once and
excludes Part payload/UID and PIN. Part diagnostic summary:
`{"passed":true,"readOnly":true,"controllerAccess":false,"tracePresent":true,"calls":218,"successfulCalls":218,"failedCalls":0,"attempts":226,"equalEvenHeaderAttempts":218,"failedCallRecords":[],"maxAttemptWindowUs":8390,"medianAttemptWindowUs":1651.5,"traceIncludesOverhead":true,"includesLiveAndHeldOracleReads":true,"causeIsolated":false,"interpretation":"Only recorded schema/revision equality/parity and timing are classified. No missing headers, payload integrity or host/publisher cause is inferred."}`.
The opt-in `fraktal.cip.trace=true` phase log records worker queue, manifest/
progress, acquisition/projection/age selection/path expansion, assembly and
SendPort delivery; default builds keep tracing disabled. Phase summary:
`{"observer":{"snapshots":2851,"deliveries":2851,"phases":{"queueUs":{"count":2851,"minimum":2,"median":10,"p95":19,"maximum":104},"manifestBeforeUs":{"count":2851,"minimum":701,"median":1255,"p95":1784,"maximum":26163},"progressProofUs":{"count":2851,"minimum":0,"median":1,"p95":1,"maximum":12391},"acquireUs":{"count":2851,"minimum":141572,"median":209505,"p95":258775,"maximum":364510},"manifestAfterUs":{"count":2851,"minimum":476,"median":912,"p95":1126,"maximum":16066},"projectionUs":{"count":2851,"minimum":1065,"median":1262,"p95":1777,"maximum":4399},"ageSelectionUs":{"count":2851,"minimum":32,"median":146,"p95":367,"maximum":856},"pathExpansionUs":{"count":2851,"minimum":5269,"median":6172,"p95":7400,"maximum":20681},"assemblyUs":{"count":2851,"minimum":83,"median":124,"p95":232,"maximum":801},"sendUs":{"count":2851,"minimum":194,"median":373,"p95":790,"maximum":2595}}},"desktop":{"snapshots":2,"deliveries":2,"phases":{"queueUs":{"count":2,"minimum":8,"median":25365.5,"p95":50723,"maximum":50723},"manifestBeforeUs":{"count":2,"minimum":1450,"median":1910.5,"p95":2371,"maximum":2371},"progressProofUs":{"count":2,"minimum":8,"median":7254.0,"p95":14500,"maximum":14500},"acquireUs":{"count":2,"minimum":472300,"median":608944.0,"p95":745588,"maximum":745588},"manifestAfterUs":{"count":2,"minimum":984,"median":1252.5,"p95":1521,"maximum":1521},"projectionUs":{"count":2,"minimum":4165,"median":4903.5,"p95":5642,"maximum":5642},"ageSelectionUs":{"count":2,"minimum":202,"median":306.0,"p95":410,"maximum":410},"pathExpansionUs":{"count":2,"minimum":10376,"median":14903.0,"p95":19430,"maximum":19430},"assemblyUs":{"count":2,"minimum":1126,"median":1768.5,"p95":2411,"maximum":2411},"sendUs":{"count":2,"minimum":915,"median":928.5,"p95":942,"maximum":942}}}}`.
Timings include instrumentation and scheduling. Missing phase records and
particular host/network/PLC causes are not inferred. Raw stdout/JSONL, slowest
groups and every failed proof remain archived.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores all five exact original host documents, runs **31/31** baseline cases,
restores policy and MANUAL/idle/logout, verifies saved/live equality and every
final/preflight check. Baseline scan: `{"lastScanMedianUs":99.0,"cumulativeMaxUs":1166,"overlaps":0}`.
The original genealogy ACD is never opened. No dumps, fault/TASK-counter clears,
clock changes, power/vendor-state operations or Echo hard kills occur.

The preparation binds **14 unchanged apparatus tests**, six unchanged
Part-trace tests, fresh SDK (zero warnings/errors), authorization/workflow/
readiness and read-only refusal gates, plus spec/contracts/strict consistency/
whitespace and **74 root tests**. Failed offline runs remain archived.
**685 HMI tests pass /12 skipped**, **73 trace-enabled focused tests**, analyzer,
Windows build and enforced lockfile. The identical **320-input mirror** changes
four existing source/test files and adds one test module. Sixteen batch cases and
the pool mutation case cover strict read-only packets, reverse execution, golden
values/types, partial/unsupported fallback, malformed refusal, count shrink and
original elapsed-window rejection. Recorded-wire replay uses **711 packets for
810 logical reads /237 groups /976 exact consumed values/types**, with no hidden
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

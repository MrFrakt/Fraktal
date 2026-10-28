# S4b bounded row-refill qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_REFILL_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b row-refill retry”, question
`call_a03c1071e32641f687cf1970bb701ef9:0`. This exact-session authorization is
consumed; it grants no subsequent controller changes.

## Target and unchanged shipping inputs

- Echo **601FC87B**, **1756-L81E v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Exact-image Capacity **2,066,212 used /1,079,516 available /3,145,728 total
  Blocks (65%)**; this does not establish physical-controller fit.
- **1079 frozen inputs** verify after execution; only
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

Independent witness replay: `{"controllerAccess":false,"fullComparison":false,"fullPairsAdded":0,"passed":true,"recorded":true,"capturePassed":true,"paths":1,"generation":5674,"attempts":6,"valueEquivalent":true,"busyObserved":true,"manifestHash":"3B765353B71891ED750D331CE11B5DDCE7D1663A06837C4C1EB0FC90FA3346AA"}`.
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
| Concurrent Dart observer | **3144** samples: **3144** entirely Good, 0 with Uncertain, 0 with Bad |
| Observer completion | PASS |
| Complete reader/configuration/acquisition | OPEN / not accepted |
| Configuration | 4 pages; None independent exact scalar/type comparisons |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict LIVE desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Final scan acceptance | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, five original documents, all final/preflight checks |

Sample age (ms): `{"minimum":191.435,"median":265.8085,"p95":337.691,"maximum":523.733}`.
RPC duration (us): `{"minimum":203236,"median":279403.0,"p95":351781,"maximum":543856}`.
Maximum accepted guarded-row window (us): `{"minimum":4309,"median":6549.0,"p95":8951,"maximum":9995}`.
Observer error: `None`.
Fixture error: `None`.
Parent candidate error: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-refill-20261027\\session_01\\run_logged.py', 'desktop_readonly', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-refill-20261027\\session_01\\desktop_readonly.py']' returned non-zero exit status 1.`.
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
Candidate read-only TASK epoch: `{"epoch":1,"rows":9770,"first":{"row":470,"elapsedUs":47364550,"utc":"2026-10-27T23:02:00.750669+00:00","values":{"Samples":0,"TaskLastScanUs":0,"TaskMaxScanUs":0,"TaskOverlapCount":0}},"last":{"row":10239,"elapsedUs":1032942237,"utc":"2026-10-27T23:18:26.328345+00:00","values":{"Samples":97852,"TaskLastScanUs":965,"TaskMaxScanUs":9003,"TaskOverlapCount":0}},"maxTaskScanUs":9003,"maxOverlapCount":0,"firstObservedOverlap":null}`.
TASK monitoring starts before download at nominal 100 ms. Read errors during
download remain in the trace. Separately read TASK scalars/polling do not
isolate an exact scan/routine or host cause. No counters are cleared.

Desktop uses the shipping factory/repository/UI and real quality/source age,
requiring LIVE/nonempty/full semantic coverage at every capture. Independent
parent validation requires **seven modules, three bus nodes and 31 views**.
Captured-fixture substitutions are disabled. Empty/STALE coverage cannot pass.
Desktop detail: `{"accepted":false,"modules":0,"views":0,"fieldbusNodes":0,"error":"Expected: LinkState:<LinkState.live>\n  Actual: LinkState:<LinkState.stale>\nafter-overview\n","link":"stale","localWriteRefusals":2,"fixtureClientWriteCalls":null,"nativeWireWriteCountMeasured":false}`.
Measured frontend refusal/age components, if recorded:
`{"passed":true,"readOnly":true,"controllerAccess":false,"observations":[{"sourceAgeUs":996563,"rpcUs":1610859,"transitUs":428567,"receivedAgeUs":1425130,"localProcessingUs":3015,"effectiveAgeUs":1428145,"fastGoodUs":1000000,"snapshotAwaitUs":1610825,"serviceDecodeUs":9,"validationUs":2,"responseProcessingMs":1183.292,"excessUs":428145,"sourceAlreadyLate":false,"lateAtReceipt":true,"localProcessingCrossedBoundary":false}],"refusalReproduced":true,"interpretation":"Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred."}`.

Original Part requests, three-attempt limit, projection and result/error
propagation remain unchanged. Session-only tracing forwards reads once and
excludes Part payload/UID and PIN. Part diagnostic summary:
`{"passed":true,"readOnly":true,"controllerAccess":false,"tracePresent":true,"calls":218,"successfulCalls":218,"failedCalls":0,"attempts":222,"equalEvenHeaderAttempts":218,"failedCallRecords":[],"maxAttemptWindowUs":10350,"medianAttemptWindowUs":1896.0,"traceIncludesOverhead":true,"includesLiveAndHeldOracleReads":true,"causeIsolated":false,"interpretation":"Only recorded schema/revision equality/parity and timing are classified. No missing headers, payload integrity or host/publisher cause is inferred."}`.
The opt-in `fraktal.cip.trace=true` phase log records worker queue, manifest/
progress, acquisition/projection/age selection/path expansion, assembly and
SendPort delivery; default builds keep tracing disabled. Phase summary:
`{"observer":{"snapshots":3144,"deliveries":3144,"phases":{"queueUs":{"count":3144,"minimum":2,"median":7.0,"p95":16,"maximum":308},"manifestBeforeUs":{"count":3144,"minimum":733,"median":1488.0,"p95":2196,"maximum":5801},"progressProofUs":{"count":3144,"minimum":0,"median":1.0,"p95":2,"maximum":10193},"acquireUs":{"count":3144,"minimum":190918,"median":265534.5,"p95":337140,"maximum":522573},"manifestAfterUs":{"count":3144,"minimum":566,"median":1018.0,"p95":1362,"maximum":8563},"projectionUs":{"count":3144,"minimum":1126,"median":1528.0,"p95":2595,"maximum":7826},"ageSelectionUs":{"count":3144,"minimum":34,"median":191.0,"p95":426,"maximum":5243},"pathExpansionUs":{"count":3144,"minimum":6034,"median":7764.0,"p95":10497,"maximum":43701},"assemblyUs":{"count":3144,"minimum":97,"median":179.0,"p95":371,"maximum":1767},"sendUs":{"count":3144,"minimum":204,"median":534.0,"p95":1202,"maximum":3320}}},"desktop":{"snapshots":2,"deliveries":2,"phases":{"queueUs":{"count":2,"minimum":23,"median":25421.0,"p95":50819,"maximum":50819},"manifestBeforeUs":{"count":2,"minimum":2376,"median":3650.5,"p95":4925,"maximum":4925},"progressProofUs":{"count":2,"minimum":11,"median":7358.0,"p95":14705,"maximum":14705},"acquireUs":{"count":2,"minimum":632835,"median":879278.5,"p95":1125722,"maximum":1125722},"manifestAfterUs":{"count":2,"minimum":1439,"median":1621.5,"p95":1804,"maximum":1804},"projectionUs":{"count":2,"minimum":2452,"median":3294.0,"p95":4136,"maximum":4136},"ageSelectionUs":{"count":2,"minimum":228,"median":429.5,"p95":631,"maximum":631},"pathExpansionUs":{"count":2,"minimum":14026,"median":16120.5,"p95":18215,"maximum":18215},"assemblyUs":{"count":2,"minimum":1414,"median":1546.0,"p95":1678,"maximum":1678},"sendUs":{"count":2,"minimum":508,"median":670.0,"p95":832,"maximum":832}}}}`.
Timings include instrumentation and scheduling. Missing phase records and
particular host/network/PLC causes are not inferred. Raw stdout/JSONL, slowest
groups and every failed proof remain archived.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores all five exact original host documents, runs **31/31** baseline cases,
restores policy and MANUAL/idle/logout, verifies saved/live equality and every
final/preflight check. Baseline scan: `{"lastScanMedianUs":99.0,"cumulativeMaxUs":1167,"overlaps":0}`.
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

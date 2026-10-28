# S4b transient login-busy witness qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_BUSY_WITNESS_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b busy-witness retry”, question
`call_2cc806825e344c5686ae76e262dae694:0`. This exact-session authorization is
consumed; it grants no subsequent controller changes.

## Target and unchanged shipping inputs

- Echo **601FC87B**, **1756-L81E v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Exact-image Capacity **2,066,212 used /1,079,516 available /3,145,728 total
  Blocks (65%)**; this does not establish physical-controller fit.
- **1079 frozen inputs** verify after execution; only
  the SDK-saved working ACD differs. Original prepared and genealogy ACDs remain
  unchanged. No shipping PLC/HMI source changes occur in this session.

The production reader retains four serial-pinned read-only CIP connections,
one outstanding request per socket and one connection through each complete
guarded row. Full walks use bounded cohorts/count barriers and Status-last
ordering. Logical primitive-array consumption governs the published tiers;
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

Independent witness replay: `{"controllerAccess":false,"fullComparison":false,"fullPairsAdded":0,"passed":true,"recorded":true,"capturePassed":true,"paths":1,"generation":4934,"attempts":6,"valueEquivalent":true,"busyObserved":true,"manifestHash":"3B765353B71891ED750D331CE11B5DDCE7D1663A06837C4C1EB0FC90FA3346AA"}`.
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
| Concurrent Dart observer | **2805** samples: **2805** entirely Good, 0 with Uncertain, 0 with Bad |
| Observer completion | PASS |
| Complete reader/configuration/acquisition | OPEN / not accepted |
| Configuration | 4 pages; None independent exact scalar/type comparisons |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict LIVE desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Final scan acceptance | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, five original documents, all final/preflight checks |

Sample age (ms): `{"minimum":202.042,"median":279.061,"p95":347.923,"maximum":520.648}`.
RPC duration (us): `{"minimum":214060,"median":290730,"p95":360612,"maximum":531519}`.
Maximum accepted guarded-row window (us): `{"minimum":4018,"median":6245,"p95":8605,"maximum":9998}`.
Observer error: `None`.
Fixture error: `None`.
Parent candidate error: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-busy-witness-20261027\\session_01\\run_logged.py', 'desktop_readonly', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-busy-witness-20261027\\session_01\\desktop_readonly.py']' returned non-zero exit status 1.`.
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
Candidate read-only TASK epoch: `{"epoch":1,"rows":8821,"first":{"row":375,"elapsedUs":37812588,"utc":"2026-10-27T18:46:57.266865+00:00","values":{"Samples":0,"TaskLastScanUs":0,"TaskMaxScanUs":0,"TaskOverlapCount":0}},"last":{"row":9195,"elapsedUs":927794591,"utc":"2026-10-27T19:01:47.248570+00:00","values":{"Samples":88493,"TaskLastScanUs":965,"TaskMaxScanUs":8994,"TaskOverlapCount":0}},"maxTaskScanUs":8994,"maxOverlapCount":0,"firstObservedOverlap":null}`.
TASK monitoring starts before download at nominal 100 ms. Read errors during
download remain in the trace. Separately read TASK scalars/polling do not
isolate an exact scan/routine or host cause. No counters are cleared.

Desktop uses the shipping factory/repository/UI and real quality/source age,
requiring LIVE/nonempty/full semantic coverage at every capture. Independent
parent validation requires **seven modules, three bus nodes and 31 views**.
Captured-fixture substitutions are disabled. Empty/STALE coverage cannot pass.
Desktop detail: `{"accepted":false,"modules":0,"views":0,"fieldbusNodes":0,"error":"Expected: LinkState:<LinkState.live>\n  Actual: LinkState:<LinkState.stale>\nafter-overview\n","link":"stale","localWriteRefusals":2,"fixtureClientWriteCalls":null,"nativeWireWriteCountMeasured":false}`.
Measured frontend refusal/age components, if recorded:
`{"passed":true,"readOnly":true,"controllerAccess":false,"observations":[{"sourceAgeUs":995517,"rpcUs":1377140,"transitUs":311554,"receivedAgeUs":1307071,"localProcessingUs":3489,"effectiveAgeUs":1310560,"fastGoodUs":1000000,"snapshotAwaitUs":1377100,"serviceDecodeUs":9,"validationUs":2,"responseProcessingMs":1066.586,"excessUs":310560,"sourceAlreadyLate":false,"lateAtReceipt":true,"localProcessingCrossedBoundary":false}],"refusalReproduced":true,"interpretation":"Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred."}`.

Original Part requests, three-attempt limit, projection and result/error
propagation remain unchanged. Session-only tracing forwards reads once and
excludes Part payload/UID and PIN. Part diagnostic summary:
`{"passed":true,"readOnly":true,"controllerAccess":false,"tracePresent":true,"calls":218,"successfulCalls":218,"failedCalls":0,"attempts":225,"equalEvenHeaderAttempts":218,"failedCallRecords":[],"maxAttemptWindowUs":15761,"medianAttemptWindowUs":1813,"traceIncludesOverhead":true,"includesLiveAndHeldOracleReads":true,"causeIsolated":false,"interpretation":"Only recorded schema/revision equality/parity and timing are classified. No missing headers, payload integrity or host/publisher cause is inferred."}`.
The opt-in `fraktal.cip.trace=true` phase log records worker queue, manifest/
progress, acquisition/projection/age selection/path expansion, assembly and
SendPort delivery; default builds keep tracing disabled. Phase summary:
`{"observer":{"snapshots":2805,"deliveries":2805,"phases":{"queueUs":{"count":2805,"minimum":2,"median":7,"p95":12,"maximum":131},"manifestBeforeUs":{"count":2805,"minimum":732,"median":1329,"p95":1765,"maximum":20451},"progressProofUs":{"count":2805,"minimum":0,"median":1,"p95":1,"maximum":10766},"acquireUs":{"count":2805,"minimum":201364,"median":278580,"p95":348153,"maximum":519743},"manifestAfterUs":{"count":2805,"minimum":535,"median":983,"p95":1200,"maximum":24405},"projectionUs":{"count":2805,"minimum":1095,"median":1370,"p95":2126,"maximum":3643},"ageSelectionUs":{"count":2805,"minimum":32,"median":150,"p95":297,"maximum":924},"pathExpansionUs":{"count":2805,"minimum":5713,"median":6941,"p95":8784,"maximum":33604},"assemblyUs":{"count":2805,"minimum":94,"median":152,"p95":287,"maximum":1273},"sendUs":{"count":2805,"minimum":210,"median":460,"p95":858,"maximum":3925}}},"desktop":{"snapshots":2,"deliveries":2,"phases":{"queueUs":{"count":2,"minimum":11,"median":25382.5,"p95":50754,"maximum":50754},"manifestBeforeUs":{"count":2,"minimum":2209,"median":2279.5,"p95":2350,"maximum":2350},"progressProofUs":{"count":2,"minimum":194,"median":6001.5,"p95":11809,"maximum":11809},"acquireUs":{"count":2,"minimum":477338,"median":744651.0,"p95":1011964,"maximum":1011964},"manifestAfterUs":{"count":2,"minimum":1171,"median":1312.0,"p95":1453,"maximum":1453},"projectionUs":{"count":2,"minimum":5053,"median":5656.5,"p95":6260,"maximum":6260},"ageSelectionUs":{"count":2,"minimum":255,"median":311.0,"p95":367,"maximum":367},"pathExpansionUs":{"count":2,"minimum":10680,"median":14718.5,"p95":18757,"maximum":18757},"assemblyUs":{"count":2,"minimum":822,"median":866.0,"p95":910,"maximum":910},"sendUs":{"count":2,"minimum":658,"median":792.5,"p95":927,"maximum":927}}}}`.
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

The preparation binds **14 new apparatus tests**, six unchanged Part-trace
tests, fresh SDK (zero warnings/errors), authorization/workflow/readiness and
read-only refusal gates, plus spec/contracts/strict consistency/whitespace and
**74 root tests**. Failed offline runs remain in the preparation archive.
Shipping inputs are identical to the tier/queue preparation: **665 HMI tests
passed /12 skipped**, 53 focused tests, analyzer/Windows/enforced lockfile,
identical **319-input** mirror, Flutter **3.47.5 /Dart 3.13.4**. These unchanged
results transfer by hashes. All **373 PLC/gate bindings**, **2,339 AB tests**,
both v38 build/read-back/access/SDK gates and exact-image **65% Capacity**
likewise transfer. Credentials and ACD/SDK binaries are excluded; approved
inputs remain hash-bound. Runtime stage exits retain every failed/skipped gate.

S4 acceptance is limited to the results above. S5 gateway/Web/installer, S6
classified legacy migration/retirement/persistence/events/capacity, and S7
physical/CIP Security including real I/O remain. Persistence medium, per-station
gateway write posture, hardware and commit/push policy remain owner decisions.
V2/Part III remain inactive. Nothing is committed or pushed.

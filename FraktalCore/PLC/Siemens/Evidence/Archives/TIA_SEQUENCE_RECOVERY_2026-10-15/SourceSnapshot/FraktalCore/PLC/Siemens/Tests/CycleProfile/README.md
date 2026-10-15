# Shared cycle profiling qualification

The selected Unit frame owns profiling through its existing sequence-view and
cycle-end boundaries. Projects record steps and finish cycles through the usual
shared helpers. MAIN gains no call. Parallel legs retain their own chart rows;
the cycle profiler records the main line.

The implementation publishes the last completed waterfall, per-step statistics,
work/wait class totals, rolling minimum and the Core-sized 60-cycle history.
Waterfall/stat arrays use the consumed sequence capacity, capped by Core's
MAX_PROFILE_STEPS. Private collection state is separate from readonly mirrors.
Durations use the wrapping monotonic clock; LDT start stamps retain nanoseconds
and keep synchronization quality false. Incomplete cycles are withdrawn on
mode exit, fault, abort and restore quiescence. Completed data survives ordinary
quiescence and mode changes; cold startup clears this volatile profile.

Completion is deferred until after the command kernel resolves the scan. A
finish marker followed by a kernel timeout cannot count as a completed cycle.
Command and step timing rows share one aggregation function.

`make_fixture.py` provides a small offline compiler gate. Its optional
`--existing-project` accepts only the isolated Cycle_Profile_Compiler project.
`make_runtime_fixture.py` adds deterministic timing cases and native Unit
integration controls to the LOAD_DB/diagnostic bench. The controls snapshot all
arguments when RequestSeq changes; clients write that sequence last. The late
timeout injection belongs solely to this test fixture.

`probe_web.py` checks native case results, first-scan zero-duration completion,
wait classifications, scope, privacy, mode/restore boundaries and the late
timeout. `probe_hmi.py` compares native values with the production gateway,
snapshot mapper and generic waterfall/trend widgets. The Web API discovers
occupied profiler history slots from LastCycle.CycleNo, follows growth/reset,
and leaves newly discovered rows excluded until the consuming read plan applies.

Run preparation/probes through `Tests/Access/with_credentials.ps1` with
`-ScriptFile`. Use fresh work/log directories, the approved unchanged driver,
compile with zero errors and warnings, verify native exports, then download in
a separate guarded plan to the preserved Fraktal simulator. The wired press
uses its own offline project. No physical press is commanded.

Baseline/degradation watching, gated statistics/OEE reset, complete sequence
freeze/resume policy and physical acceptance remain separate port gates.

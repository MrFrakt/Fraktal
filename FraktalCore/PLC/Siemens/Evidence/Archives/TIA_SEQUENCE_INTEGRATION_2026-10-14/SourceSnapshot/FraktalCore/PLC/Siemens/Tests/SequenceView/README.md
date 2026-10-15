# Shared sequence view qualification

Generator 0.17 supplies the Core 3.13 definitions, per-leg cursors, row history
and sparse annotations for an explicitly selected Unit. Capacities are bounded
by Core and allocated for deployed consumers. The owning frame starts/finishes
the scan and clears discovery on a committed mode change; sequence helpers
record visits, conditions and messages without an extra application call.

`make_fixture.py` extends the isolated config bench with synthetic view events
and the actual press sequence helpers. It commands no press plant. `probe_web.py`
qualifies fast visits, guards and guard changes, sub-chain cursor priority,
bounded rows/notes, authoritative marks when notes fill, reset and mode boundaries,
root isolation, privacy, readonly publication and STOP/RUN. The reset case first
raises a real blocking occurrence: chart marks alone do not open the reset gate.

Use `Tests/Access/with_credentials.ps1` with `-ScriptFile` pointing to these files.
Compile the generated package with zero errors/warnings before a separate guarded
download-only plan. Preserve every attempt under a new output path. The approved
driver and existing Fraktal simulator owner must be reused.

[Measured report](../../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_VIEW_2026-10-13.md)
records 122 native checks on the original LOCAL_RETAIN fixture.

`make_medium_fixture.py` combines the selected LOAD_DB consumers with these view
events. `probe_medium.py` checks the actual running-state quiesce service, then
STOP/RUN during an unavailable-medium restore barrier. Quiesce withdraws cursors
and CurrentStep while keeping row history; cold startup clears the volatile chart.
`probe_medium_regression.py` reruns the view outcomes after storage is ready.
These probes qualify shared services without a physical press.

`probe_hmi.py` starts an owned loopback gateway using the production Web API
session client and runs `HMI/test/live_tia_sequence_view_test.dart`. The opt-in
test uses the generic repository and chart, with static manifest definitions,
live cursors and deferred PLC history/notes. It records a screenshot and rows.
The wrapper supplies credentials through environment variables; each native
mutation checks the isolated simulator. Only this test's gateway stop file is
written; the persistent simulator keeper is preserved.

Complete diagnostic walks/profiling and physical process acceptance remain
separate work. See the [combined integration report](../../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md).

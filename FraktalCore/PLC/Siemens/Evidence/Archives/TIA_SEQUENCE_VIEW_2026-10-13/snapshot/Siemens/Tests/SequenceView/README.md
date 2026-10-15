# Shared sequence view qualification

Generator 0.16 supplies the Core 3.13 definitions, per-leg cursors, row history
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
records 122 native checks. This fixture selects the existing LOCAL_RETAIN config
profile; it does not repeat the LOAD_DB consumer gate. The separately compiled
press selects LOAD_DB and the view together. Native HMI hydration/rendering of
the new tables, diagnostic walks/profiling, combined restore-barrier behavior
and physical process acceptance remain separate work.

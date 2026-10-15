# Shared sequence diagnostics qualification

Generator 0.18 adds a private diagnostic snapshot for each deployed module under
a selected `sequence_view` Unit. Registry ownership and names derive from the
declaration; the compact registry and released Core types remain unchanged.
Owning frames capture canonical diagnostics after cyclic work and withdraw them
during persistence quiescence. Projects add no scheduling call.

`FRK_SeqCommand` identifies its target by registry index. The shared scoped walk
finds faults and held/wait reasons through nested composites, rejects foreign
roots, and preserves the originating first-out. EMs adopt child faults; Units
adopt the faults of awaited commands so a sequence can still own a recovery
branch. A handled failure publishes a warning without faulting the Unit.

The frame derives the longest awaited command guard unless the step supplies an
explicit guard. At expiry the main line publishes a LOW `Pending` diagnostic;
named Boolean waits identify the first false condition. Stalls create no fault
or blocking alarm. HELD retains the child's reason, disarms the generic stall,
and clears when its permit returns. Faults mark the responsible row before the
guard expires. Per-leg faults use their own row; main-line Pending stays scoped.
Shared command leases withdraw Execute and pulse Abort when a busy command is
released, preserving the Execute-low reset gap.

`make_fixture.py` combines the selected LOAD_DB/view bench with actual CM/EM
kernel commands and test-only synthetic step clocks. `probe_web.py` checks
first-out fields, scope, named stalls, timestamp stability, guard derivation,
HELD recovery, handled warnings, row marks and restart. No physical press is
commanded. The fixture uses writable controls; production work and Pending are
private/readonly respectively.

Run the fixture/probe through `Tests/Access/with_credentials.ps1` with
`-ScriptFile`. Generate into new directories, compile with zero errors/warnings,
then use a separate guarded download plan. Reuse the approved driver and the
existing Fraktal simulator owner. Save every attempt under a new log name.

Profiling, the complete sequence freeze/resume policy and physical process
acceptance remain separate gates. See the
[measured report](../../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14.md).

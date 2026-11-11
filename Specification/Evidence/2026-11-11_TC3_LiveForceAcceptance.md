# Native PLC and System Manager force acceptance — 2026-11-11

Owner requested live verification of the installed detector. Core **0.26.9.0** /
Modules **0.18.0.1**, unchanged from the
[preceding receipt](2026-11-11_TC3_MaintenanceDetector.json). Only the aggregate
acceptance harness and its documentation changed (IMPLEMENTATION_NOTES §178).
Follow [the repeatable procedure](../Guides/TC3_NATIVE_FORCE_ACCEPTANCE.md).

Target: isolated **UmRT_Default 192.168.1.6.1.1:851**, 3.1.4026.24. XAE's actual
target and loaded ProjectName were checked before control operations. No I/O
devices or physical mappings were configured. Native forces were applied through
the XAE/System Manager UI; no application override or status-bit injection was used.

| Live episode | Native PLC flag | Native I/O flag | Measured result |
|---|---|---|---|
| Unmapped ForceWitness forced TRUE | TRUE | FALSE | witness/demand TRUE, one reason-22 event, Healthy TRUE |
| PLC force held | TRUE | FALSE | one event, same slot and ring head |
| PLC unforce | FALSE | FALSE | witness/demand FALSE, event closed, duration **38,890 ms** |
| Unlinked software task input forced 1 | FALSE | TRUE | demand TRUE, one reason-22 event, Healthy TRUE |
| I/O force held | FALSE | TRUE | one event, same slot and ring head |
| I/O release | FALSE | FALSE | demand FALSE, event closed, duration **78,320 ms** |

Both events have LOW / SYSTEM / AUTO_RESET metadata, the registered localization
key and source `ForceAcceptance.SystemHealth`. The startup/pause timing events
already in the ring are separate; each force release adds exactly one closed
reason-22 row. All accepted phases were independently read over ADS.

The System Manager witness was one unlinked BOOL in a temporary **software-only
task image**, created through the documented Automation Interface. Releasing an
unlinked input leaves its value standing; Online Write 0 restored it before the
task was removed. Before/with/after configuration snapshots are retained. The
original one-task/no-device configuration was then activated again.

All three aggregate gates (initial harness, temporary task image, restored
configuration) compile cleanly and pass **355/355 in 54 suites**, with independent
exact-runner/inventory JUnit validation. Both lint profiles: 469 files clean;
strict consistency: zero errors/warnings. The prior five unaffected solution
checks and Press 9/9 result remain applicable: their authored inputs and both
installed library exports were verified unchanged. No additional library release.

Final independent checks: **Fraktal_Tests stopped**, runtime in Run mode, both
native force flags FALSE, witness/demand FALSE, no active maintenance event,
Healthy TRUE, boot autostart disabled, **one PlcTask, zero I/O devices**. XAE is
logged out. The temporary task is absent from the restored configuration.

The [SHA-256 receipt](2026-11-11_TC3_LiveForceAcceptance.json) binds 46 artifacts and
523 current source inputs; 476 authored PLC objects match
the isolated checkout byte-for-byte. It preserves the prior 522-source baseline
in a ZIP and verifies all 45 earlier artifacts unchanged. The initial observer
baseline with incorrectly decoded unused STRING tail bytes is kept local, not
exported; accepted live snapshots use first-NUL decoding. The corrected ADS state
helper and its initial unsupported-overload failure are retained.

Changes remain uncommitted and unpushed. User settings are unchanged. No physical
machine, NC, robot or electrical-output acceptance is claimed.

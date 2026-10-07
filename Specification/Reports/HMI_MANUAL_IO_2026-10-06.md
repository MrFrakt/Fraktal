# Manual-card I/O and Bosch indicators — 2026-10-06

The manual-command card now shows published physical I/O assigned to that exact
module. Inputs and Outputs are separate framed groups, with electrical tags
preserved in monospace and descriptions localized. Analog records show numeric
value/unit. Channel faults, diagnostics and forcing indications remain visible.
The rows are read-only; manual buttons retain their existing PLC release,
access, acknowledgement and hold-to-run behavior.

Like a Bosch uses small filled circular indicators with thin white arrows:
input down, output up; ON fills are light green `#91C64A` and light red `#E89690`;
OFF is gray `#D2D5D5`. The physical fieldbus view shares the same indicator.
The manual card has a white body and thin square signal-group frames. The
multicolor strip, semantic module icons and solid event-bar colors are preserved.
The final visuals were rendered and inspected at compact, medium and large
control sizes under `artifacts/hmi-manual-io-2026-10-06/preview-*.png`.

## Data ownership and demand

`ModulePath` is an exact identity join. Siblings, children and similarly prefixed
module names do not become extra signals. The physical topology remains the
source; neither device names nor command results manufacture I/O values.

The visible manual card requests its selected channel metadata/quality and the
owning bus ancestors' health. It excludes unrelated channel diagnostics and
the force capability from this read-only scope. Closing/hiding the card,
switching tabs/modules or changing the HMI root assignment withdraws demand.
The bus page remains an independent consumer; either may keep the scan active.
Requests and gate writes are deduplicated/serialized. An unassigned module does
not start a bus scan. Static ownership remains derived from the manifest/catalog.

Physical sample usability requires a present value, a true quality flag and
Good transport metadata for both. Bad or missing values/quality, unavailable
connection, unusable bus ancestry and nonfinite analog values cannot display a
healthy OFF. The LED uses a distinct neutral unavailable mark, with localized
status text/tooltip and semantic labels.

## Freshness timer defect found during verification

Two full-suite runs exposed timing edge cases; their logs remain in the task
artifacts. One missed a timing bound while the installer compiled concurrently.
Another left a stalled RPC's sample LIVE. Isolated reruns passed, so counts alone
were insufficient to dismiss it as scheduler load.

Inspection found that the early freshness callback returned without re-arming.
The Dart VM [timer implementation](https://github.com/dart-lang/sdk/blob/main/sdk/lib/_internal/vm/lib/timer_patch.dart)
uses integer milliseconds; the pinned local SDK has the same implementation.
A fractional remaining delay could therefore fire before the exact threshold.
The repository now re-arms an early callback and rounds the remaining delay up
to milliseconds. Budgets, expiry thresholds and command guards are unchanged.

A new test deliberately fires the first freshness timer 20 ms early while the
second RPC remains blocked. It requires LIVE → STALE → DOWN, empty withdrawn
data and refused commands before the RPC completes. Restoring the old early
return in the isolated checkout fails this test with only LIVE. The fixed
freshness suite passes all 22 tests. The negative test log is
`artifacts/hmi-manual-io-2026-10-06/timer-mutant.log`.

## Validation and delivery

The final test/analyzer and installer verification receipt is
`artifacts/hmi-manual-io-2026-10-06/delivery.json`. Testing/building uses the
canonical locked dependency set with Flutter 3.47.5 in the isolated checkout;
the user's original dependency lock remains byte-for-byte preserved.

Final acceptance: **552 tests passed, seven live-only tests skipped**, analyzer
clean, and strict consistency with zero errors/warnings. The refreshed installer
is `FraktalCore/HMI/build/gateway/installer/FraktalSetup.exe`, 51,245,056 bytes,
SHA-256 `f73377a618747ab244d8f3f71e168b04f50c1db17f9ca799792bd420b7810bab`.

Native Windows desktop, Web HMI, gateway and installer were rebuilt together.
Verification checks embedded CAB contents and both ZIPs against staged files,
native architectures/DLL loading, gateway help, Caddy and installer script syntax.
This task does not execute the installer or download a PLC.

The ready-to-copy [fresh-chat handover](../Guides/TC3_MISSING_FEATURES_HANDOVER_2026-10-06.md)
carries the current Core/Modules versions, native x32 IDE workflow, remaining
feature priorities, actual-target prerequisites and pending fresh clock runtime
acceptance. No historical TcUnit result is relabeled as a fresh clock pass.

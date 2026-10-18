# AB continuation after the TIA bench: 2026-10-18

This is a non-normative implementation/status record. It applies the
[TIA cross-binding lessons](../Reports/TIA_BENCH_CROSS_BINDING_LESSONS_2026-10-18.md)
and the owner's subsequent request to check native v38 overlap. The separate
[native-feature audit](AB_V38_NATIVE_FEATURE_AUDIT_2026-10-18.md) owns the native
reuse findings and next implementation order.

## Implemented

- **L1, active endpoint:** the connection owner supplies the display endpoint
  from the settings that created the repository. Settings shows it before login;
  disconnect remains administrator-only. URI credentials/query/fragment are
  omitted. Regression cases reconnect OPC UA, ADS, CIP and WSS to a different
  endpoint publishing the same root identity. Existing session disposal, retry
  cancellation, selected-Unit validation and credential ownership remain in the
  connection owner. Gateway-to-controller identity display is still open: a
  service URL alone does not identify its downstream controller.
- **L2, AB I/O acquisition:** each declared direction is read independently.
  A failed output read no longer discards a valid input sample. A channel needs
  its direction's sample and the fault word for Good quality. Missing/null data
  never becomes a Good zero; invalid output samples withdraw force capability.
  A complete sample still shows an existing forced-output warning when that
  channel is faulted; quality never erases that warning.
  Complete native samples retain the previous state mapping. Incomplete samples
  keep the offline node indication. The output source is documented as the
  controller process image, without electrical/applied-output claims.
- **AB gate repair:** `check_ab_spec.py` now matches the evidence already
  recorded in Part III: R0-R6 PASS, S15 PASS narrowed and S16 registered/PASS.
  It checks readiness evidence files and prevents removal of the R6 read-only
  qualifier and S15 scope qualifier. It does not promote any runtime claim.

No generator, declaration, library or controller program changed. Published
layouts and PLC memory needs are unaffected. These are client/gateway fixes;
native replacement work in the audit is not implemented or accepted yet.

## Validation

| Check | Result |
|---|---|
| Full AB tool discovery | **1,683 tests PASS**, 257.363 seconds |
| AB specification and frozen-contract gates | clean |
| Root specification/contract test suites | **39 tests PASS** |
| Consistency strict gate | **0 errors, 0 warnings** |
| Consistency tests | **35 tests PASS** |
| HMI targeted endpoint/reconnect tests | **9 tests PASS** |
| Full isolated HMI suite | **586 PASS, 12 environment-dependent skips** |
| HMI analyzer | no issues |
| Dependency resolution | `pub get --enforce-lockfile` passes; committed lock unchanged |
| Whitespace check | clean with CR-at-EOL allowed for the repository's byte-preserved CRLF files |

HMI checks used the installed **Flutter 3.47.2 / Dart 3.13.2**, also used in
the direct-CIP evidence, rather than the documented 3.47.5 pin. The isolated
copy preserves the HMI/PLC sibling layout required by the module-symbol inventory
test. An initial HMI-only copy failed that inventory lookup; after supplying
the actual sibling source directories, the complete suite passes. No assertion
or test was disabled to obtain the result.

The six added AB regressions exercise missing input/output/fault words,
failed reads returning null, force withdrawal, retained forced warnings and
outage/recovery. They preserve
the existing sibling-topology, electrical-identity and module cross-link checks.
They are projection/acquisition evidence, not a physical outage or native
MODULE-object acceptance run. L3 consumption measurements and L4/L5 multi-root
adapter/operator-transport qualification remain open.

## Next work

The [v38 audit](AB_V38_NATIVE_FEATURE_AUDIT_2026-10-18.md) puts native module
state and timing probes first, alarm-provider feasibility next, and the
target-specific transport comparison before expanding a second CIP projection.
The remaining traceability, host-event, line-mirror and optional profile work
continues through the completion plan after these native-reuse decisions.
No controller download or gateway deployment occurred in this change.

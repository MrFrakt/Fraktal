# Annunciating the CPU's maintenance demand (P8, 2026-11-11)

Owner decision after the [force-job spike](TIA_FORCE_JOB_SPIKE_2026-11-11.md):
annunciate in the PLC what the program can see of a TIA force job, the MAINT
LED, worded as what it is (maintenance demanded, a force job being one cause),
and keep the exact check (diagnostic-buffer event 16469) for commissioning.

## Core

- `E_Reason.CONTROLLER_MAINTENANCE_DEMANDED = 22`, Part I §8.8 System band
  (now `10–22`), registered in `reason_rationalization.json`: LOW, SYSTEM,
  **not shelvable** (a force job overrides the program and must stay visible),
  with action and consequence text. A binding raises it only where its platform
  reports a maintenance demand; TwinCAT and Allen-Bradley do not raise it.
- Operator text `std.system.controllerMaintenanceDemanded` (en, es).
- `tool/generate_reason_catalog.dart` regenerated its four derived artifacts:
  the HMI `reason_catalog.g.dart` and TwinCAT `PL_ReasonCatalog` (count 96 → 97)
  and `F_ReasonMetaByIndex` (one new branch). Its `--check` passes.
- TIA frozen contract **V3** = V2 plus that one entry (V1/V2 byte for byte),
  bound in Part IV; `check_tia_contracts` and its tests pass.

## TIA binding

- `FRK_S7HealthProbe` samples `LED(LADDR := "Local~Common", LED := 3)` once per
  scan; MAINT at 2 (lit) sets `FRK_HealthProbe.MaintenanceDemanded`.
- `FRK_S7MaintenanceCondition`, called by every root that carries health,
  raises one LOW/SYSTEM/AUTO_RESET condition event per root while the demand
  stands and closes it when it ends (the shared `FRK_ConditionEvent`).
- Native Operations suite +4 checks (112): one standing LOW system event with
  reason 22 and no blocking; raised once across repeated scans; shelving
  refused; closed when the demand ends.

## Measured

Full gate `TiaGate_P8Maint_20261111_01` (native and bench): **PASS**. 303 tool
tests; lint, consistency and contracts clean; press replay 286. Operations 0/0,
read-back 298/85/22, bench **112/112** (image `65f0a391…dc`); reusable modules
0/0, 305/93/18, **46/46**; PROFINET 0/0, 262/71/17, **5/5**. The saved `Fraktal`
instance read RUN with unchanged addresses before and after.

## Limits

- The wording cannot be exact: the program sees maintenance demanded, which a
  force job raises among other causes. A flashing MAINT (maintenance
  *required*) is not annunciated by this condition.
- The end-to-end path with a real force job was not repeated: the spike proved
  the LED sample on the CPU and the native suite proves the condition from it.
- TwinCAT: plc_lint passes in both profiles (469 files). This host has no
  TwinCAT XAE, so the TwinCAT compile/install gate did not run here; the Core
  change is one additive enum member and generator output. Its patch release
  (version step, build, install) belongs on the TwinCAT host.

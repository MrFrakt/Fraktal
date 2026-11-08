# S6 C5b3 remaining station-reading harnesses - offline qualification

This slice qualifies the migration of the six remaining station-reading HX
harnesses onto canonical CIP row and O10 surface reads, completing Increment 3
of C5b3:
1. `fraktal_ab_press_parity.py`
2. `fraktal_ab_phase1_execute.py`
3. `fraktal_ab_phase2_execute.py`
4. `fraktal_ab_phase3_execute.py`
5. `fraktal_ab_phase4_execute.py`
6. `fraktal_ab_s3_execute.py`

Parent commit `c2c0cdb87c66a9ebf6c88fe19f0212fd4f5bb0c1`. The owner authorizes
commit/push on main. No controller connection, download, tag write, mode change,
fault/TASK clear, clock, power, or vendor-state operation ran.

## Results

- **2,734 AB tests** (`ab_full_suite_01`), **36 root consistency tests**
  (`root_tests_01`), **12 focused tests** (`focused_tests_01`), **15 collapse
  tests** (`collapse_tests_01`), **339 canonical tests**, and the root spec,
  contract, and strict consistency gates pass.
- **Zero direct legacy calls or legacy imports** remain across all six migrated
  harnesses (`harness_census_01`):
  - `fraktal_ab_press_parity.py`: replaced direct `px.read_layout` for `CFG`
    with `views.surface(comm, "Cfg0", app=APP)` on the collapsed path,
    preserving the legacy fallback when `not app.canonical_collapse`.
  - `fraktal_ab_phase1_execute.py`: replaced direct `read_log` and `read_layout`
    calls with `views.read_alarm_log`, `views.read_release_report`,
    `views.step_conditions`, `views.unit_diagnostic`, `views.alarm_blocking`,
    `views.alarm_active_event`, and `views.header_valid`.
  - `fraktal_ab_phase2_execute.py`: replaced direct `read_document` calls with
    `views.sequence_step_summary`, `views.active_step_cursor`, and
    `views.sequence_annotations`.
  - `fraktal_ab_phase3_execute.py`: replaced direct `read_layout` and `document`
    lookups with `views.read_alarm_log`, `views.surface("Cfg0")`,
    `views.module_status`, `views.unit_diagnostic`, `views.module_diagnostic`,
    `views.step_conditions`, and `views.current_step_timed_out`.
  - `fraktal_ab_phase4_execute.py`: replaced direct catalogue and release-report
    document lookups with `views.numeric_key`, `views.module_diagnostic`,
    `views.module_catalog`, and `views.release_report_hmi`.
  - `fraktal_ab_s3_execute.py`: replaced direct `px.read_layout` with
    `views.read_health_probe`, which calls `px.read_flat` on the collapsed
    path and `px.read_layout` when not collapsed.
- All original check and wait predicates across Phases 1–4, Parity, and S3
  remain preserved verbatim.
- Zero PLC generator or declaration sources changed. All three collapsed L5X
  profiles regenerate byte-identically to their sealed C5b3 pins:
  - `fraktal_ab_genealogy_s6_collapse_demo`:
    `57FDB0BC88CF1D8E6F3D5F325B51F61DFD5C110CE5C795A6BE9871B26F5042FE`
    (**60% Studio Capacity**, 1,916,892 / 3,145,728 Blocks).
  - `fraktal_ab_press_s6_collapse_echo38`:
    `0E3E19A822B781EDEFCC38259DDA6F533D94624E66A68415DB20174DAD3AF7A0`
    (**54% Studio Capacity**, 1,726,208 / 3,145,728 Blocks).
  - `fraktal_ab_press_s6_shelving_echo38`:
    `D7FB6960255F48EDC9FF9288A625A903BE8A93BF2CE26D71353C0AA34D6A131D`
    (**54% Studio Capacity**, 1,726,244 / 3,145,728 Blocks).
- All 84 shipping HMI/Dart sources and both prepared runtime executables match
  C5b2's sealed bindings.
- Owner edits in `.vscode/settings.json`, `FraktalCore/PLC/Siemens/Tests/Manifest/README.md`,
  and `analysis_options.yaml` were verified byte-for-byte identical before and
  after (`unrelated_before.json`, `unrelated_after.json`) and remain excluded.

## Canonical View Ownership

- **1-based index consistency**: Station-level browse paths for sequence steps,
  step conditions, active cursors, annotations, catalogues, and release reports
  use canonical 1-based indexing (`Conds[1..4]`, `SequenceSteps[1..N]`,
  `ActiveSteps[1..L]`, `Catalog[1..2]`, `Reasons[1..N]`). Helpers in
  `fraktal_ab_fixture_reads.py` query CIP leaf rows directly under scan-domain
  coherence, eliminating client-side document synthesis.
- **Scan-coherent timeout and status queries**: `CurrentStepTimedOut` and
  module `Status` (`TypeKey`, `DisplayNameKey`, `State`, `FaultActive`) resolve
  directly via canonical CIP browse paths without requiring mock or fallback
  projections.
- **Fail-safe fallback retention**: Where legacy baselines are executed
  (`not app.canonical_collapse`), all six harnesses retain their original
  `read_layout` / projection branches untouched until WP6.7 baseline switch.

## Provenance and Failed Runs

- `bootstrap_01.py`: failed on abbreviated 10-char commit hash vs 40-char full
  SHA. In accordance with the append-only rule, `bootstrap_01.log` and
  `bootstrap_01_exit.json` are preserved. `bootstrap_02.py` succeeded against
  `c2c0cdb87c66a9ebf6c88fe19f0212fd4f5bb0c1`.
- `check_ab_spec_01`: failed on path argument (`FraktalCore/PLC/Allen-Bradley/tools/check_ab_spec.py`
  instead of `tools/check_ab_spec.py`). Preserved in `check_ab_spec_01.log` and
  `check_ab_spec_01_exit.json`. `check_ab_spec_02` succeeded.

## Remaining and Next

All station-reading harnesses, shared runners, the standalone press launcher,
and Part/genealogy acquisition in C5b3 are now fully migrated and qualified
offline.

Remaining:
1. **C5c**: Frame/staged endpoint retirement and V6.12 publication.
2. **C6 / C7**: Canonical integration and baseline switch.
3. **Native S6-Q**: Live controller qualification after C7 on Echo.
4. **WP6.7**: Final deletion of retired legacy runtime and import census.
5. **Specification activation**: Part III standard release.
Physical S7 remains deferred under O2.

[Payload and hashes](AB_S6_COLLAPSE_C5B3_HARNESSES_OFFLINE_2026-11-07/artifact_manifest.json)
binds all gate logs, exit records, and checks.

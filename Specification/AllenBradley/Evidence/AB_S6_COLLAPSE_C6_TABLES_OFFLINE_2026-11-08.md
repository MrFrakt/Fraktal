# S6 C6 legacy published tags to None and eight V5 tables retired — offline qualification

This slice qualifies Increment C6 of the Allen-Bradley canonical collapse (WP6.6):
retiring legacy published tags (`FRK_{app.name}_Unit`, `FRK_{app.name}_Chart`) and
eight V5 manifest tables (`FRK_{app.name}_MfHeader`, `Roots`, `Modules`, `Nameplates`,
`Fields`, `Operations`, `Rationalization`, `OptionalProfiles`) from the public external
surface of collapsed profiles by setting `ExternalAccess="None"`, retaining
`FRK_{app.name}_MfLocalization` and `FRK_{app.name}_MfWriteCapabilities` as `Read Only`,
preserving 100% byte-identity on uncollapsed baseline profiles, and validating pre-collapse
schema identity across all five gated declarations with zero uncovered and zero unused
differences.

Parent commit `0d4474a6d36e22ef3f24bf7bf4c16a5d454bc95f`. The owner authorizes commit/push on
main. No controller connection, download, tag write, mode change, fault/TASK clear, clock,
power, or vendor-state operation ran. Echo execution remains deferred to S6-Q after C7
under standing O3.

## Results

- **Schema Identity Gate (10/10 passed across 5 declarations)**:
  `test_fraktal_ab_schema_identity.py` passes all 10 tests across all 5 gated declarations
  (`schema_identity_01` in 480.267s) with zero uncovered and zero unused differences:
  - `fraktal_ab_genealogy_s6_host_demo`: 0 differences against pre-collapse recorded surface.
  - `fraktal_ab_press_canonical_echo38`: 0 differences against pre-collapse recorded surface.
  - `fraktal_ab_genealogy_s6_collapse_demo`: exact declared differences match, covering all
    C6 tag and type retirements.
  - `fraktal_ab_press_s6_collapse_echo38`: exact declared differences match.
  - `fraktal_ab_press_s6_shelving_echo38`: exact declared differences match.
- **Dedicated C6 Unit Tests (2/2 passed)**:
  `test_fraktal_ab_collapse_c6.py` (`test_collapse_c6_01` in 32.9s) asserts that:
  - Collapsed profiles (`press_s6`, `press_shelving`, `genealogy_s6`) set
    `ExternalAccess="None"` on `FRK_{app.name}_Unit`, `FRK_{app.name}_Chart`,
    `FRK_{app.name}_MfHeader`, and the seven retired manifest table tags (`Roots`,
    `Modules`, `Nameplates`, `Fields`, `Operations`, `Rationalization`, `OptionalProfiles`).
  - Collapsed profiles retain `ExternalAccess="Read Only"` on `FRK_{app.name}_MfLocalization`
    and `FRK_{app.name}_MfWriteCapabilities`.
  - Uncollapsed baseline profiles (`press_canonical`, `genealogy_host`) retain
    `ExternalAccess="Read Only"` across all manifest tags and Unit/Chart tags.
- **Dart Manifest Verification (2/2 passed)**:
  `flutter_test_01` (`cip_host_services_manifest_test.dart`) and `flutter_test_v612`
  (`cip_collapse_v612_manifest_test.dart`) pass clean with exit code 0.
- **Root Consistency and Contracts**:
  - `check_consistency.py --strict`: 0 errors, 0 warnings across inventory, localization,
    parity, readsurface (`check_consistency_01`).
  - `check_ab_spec.py`: clean (`check_ab_spec_01`).
  - `check_ab_contracts.py`: clean (`check_ab_contracts_01`).
  - `tools.test_check_consistency`: 36 tests passed in 2.399s (`root_tests_01`).
- **Profile Measurements**:
  - `fraktal_ab_genealogy_s6_collapse_demo`: SHA-256 `6057D1EA79E8034106C7F0ACB5EC4ABDC979C9EF0D326B1130A20B5F90998B5A`,
    5,939,631 bytes, 72 routines, 53,970 ST tokens.
  - `fraktal_ab_press_s6_collapse_echo38`: SHA-256 `32C48BA5606291199C66D685DD4C68BC7426CB85C945AD2AAA4700A7980A7C40`,
    5,448,374 bytes, 66 routines, 46,868 ST tokens.
  - `fraktal_ab_press_s6_shelving_echo38`: SHA-256 `3802DE1991638AFD74B95F7A4ECE4DCE49F849AAA3FE91F692ED5F145DBF23C3`,
    5,448,594 bytes, 66 routines, 46,890 ST tokens.
  - Routines and ST token counts remain token-identical to C5c.
- **Full Allen-Bradley Test Suite (2,744/2,744 passed)**:
  `ab_full_suite_01` ran `python -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools -t FraktalCore/PLC/Allen-Bradley/tools`
  in 2,628.267s: all 2,744 tests passed clean (`OK`, exit code 0).
- **Protected Files**:
  Owner edits in `.vscode/settings.json`, `FraktalCore/PLC/Siemens/Tests/Manifest/README.md`,
  and `analysis_options.yaml` were verified byte-for-byte identical before and after
  (`unrelated_before.json`, `unrelated_after.json`) and remain excluded.

## Surface and Table Retirement Architecture

- **Private working buffers**:
  Setting `ExternalAccess="None"` on `FRK_{app.name}_Unit` and `FRK_{app.name}_Chart`
  encapsulates the legacy Unit context and sequence chart inside controller execution,
  removing them from external CIP discovery and read surfaces while preserving internal
  routine bindings and scan semantics without logic disruption.
- **Retirement of Eight V5 Manifest Tables**:
  V5 tables `MfRoots`, `MfModules`, `MfNameplates`, `MfFields`, `MfOperations`,
  `MfRationalization`, `MfOptionalProfiles`, and the header tag `MfHeader` are set to
  `ExternalAccess="None"` on collapsed profiles. This eliminates all fine-grained
  member and row diffs from the public external surface while allowing internal controller
  routines (such as `_identity()` in `fraktal_ab_shelving.py`) to access them without
  causing undefined-symbol compiler diagnostics.
- **Retained Public Tables**:
  `FRK_{app.name}_MfLocalization` and `FRK_{app.name}_MfWriteCapabilities` are kept with
  `ExternalAccess="Read Only"` to preserve canonical text localization resolution and
  write capability discovery.

## Provenance and Append-Only Logs

All executions and measurements are recorded in `C:/work/fraktal-ab-c6-control-20261108/`:
- `test_collapse_c6_01.log` & `_exit.json`: Dedicated C6 unit tests (passed).
- `schema_identity_01.log` & `_exit.json`: 10 schema identity tests across 5 declarations (passed).
- `root_tests_01.log` & `_exit.json`: Root consistency tests (passed).
- `check_consistency_01.log` & `_exit.json`: Strict consistency check (passed).
- `check_ab_spec_01.log` & `_exit.json`: AB spec check (passed).
- `check_ab_contracts_01.log` & `_exit.json`: AB frozen contracts check (passed).
- `flutter_test_01.log` & `_exit.json`: Host services manifest Dart test (passed).
- `flutter_test_v612.log` & `_exit.json`: V6.12 manifest Dart test (passed).
- `measure_profiles_01.log` & `_exit.json`: Image size and token count measurements.
- `ab_full_suite_01.log` & `_exit.json`: Full AB test suite (2,744 passed in 2,628.267s).
- `unrelated_before.json` & `unrelated_after.json`: Protected file identity verification.

## Remaining and Next

C6 is complete:
1. **Increment C7**: R5: a production declaration selects one AUTO rendition.
2. **Native S6-Q**: Live controller qualification on Echo after C7 under standing O3.
3. **WP6.7**: Final deletion of retired legacy runtime and import census.
4. **WP6.8**: Specification documents and active contract transition.

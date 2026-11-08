# S6 C7 R5 production single-rendition selection — offline qualification

This slice qualifies Increment C7 of the Allen-Bradley canonical collapse (WP6.6):
fulfilling requirement **R5** ("A production declaration selects one AUTO rendition (ST, SFC or LD).
Acceptance declarations keep all three for the parity gate.") without wire layout or logic disruption.

Parent commit `0d075e61e12dbfe1aa23cf6378e99a2245b78b82`. The owner authorizes commit/push on
main. No controller connection, download, tag write, mode change, fault/TASK clear, clock,
power, or vendor-state operation ran. Echo execution remains deferred to S6-Q after C7
under standing O3.

## Results

- **Schema Identity Gate (10/10 passed across 5 declarations)**:
  `test_fraktal_ab_schema_identity.py` passes all 10 tests across all 5 gated declarations
  (`schema_identity_01`) with zero uncovered and zero unused differences:
  - `fraktal_ab_genealogy_s6_host_demo`: 0 differences against pre-collapse recorded surface.
  - `fraktal_ab_press_canonical_echo38`: 0 differences against pre-collapse recorded surface.
  - `fraktal_ab_genealogy_s6_collapse_demo`: exact declared differences match.
  - `fraktal_ab_press_s6_collapse_echo38`: exact declared differences match.
  - `fraktal_ab_press_s6_shelving_echo38`: exact declared differences match.
- **Dedicated C7 Unit Tests (4/4 passed)**:
  `test_fraktal_ab_collapse_c7.py` (`test_collapse_c7_01` in 246.8s) asserts that:
  - Production declarations (`press_demo`, `press_echo38`, `station_template`) select
    exactly one rendition for AUTO and each chain (`not auto.multi_rendition`).
  - Production declarations emit no `FRK_{app.name}_RenditionSelect` tag in controller tags,
    `writable_inputs`, or `harness_only_tags`.
  - Acceptance declarations (`press_s6`, `press_shelving`, `genealogy_s6`) retain all three
    renditions (`ST`, `SFC`, `LD`) for the parity gate and emit `RenditionSelect`.
  - Selecting one rendition on collapsed press saves 4 routines (66 -> 62), reduces L5X code
    size by 96,719 bytes (within the planned 60–120 KB range), and eliminates 3,313 ST tokens
    (46,868 -> 43,555).
  - Any single rendition among ST, SFC, or LD validates and generates cleanly.
- **Dart Manifest Verification (2/2 passed)**:
  `flutter_test_01` (`cip_host_services_manifest_test.dart`) and `flutter_test_v612`
  (`cip_collapse_v612_manifest_test.dart`) pass clean with exit code 0.
- **Root Consistency and Contracts**:
  - `check_consistency.py --strict`: 0 errors, 0 warnings across inventory, localization,
    parity, readsurface (`check_consistency_01`).
  - `check_ab_spec.py`: clean (`check_ab_spec_01`).
  - `check_ab_contracts.py`: clean (`check_ab_contracts_01`).
  - `tools.test_check_consistency`: 36 tests passed (`root_tests_01`).
- **Profile Measurements**:
  - `fraktal_ab_genealogy_s6_collapse_demo`: SHA-256 `6057D1EA79E8034106C7F0ACB5EC4ABDC979C9EF0D326B1130A20B5F90998B5A`,
    5,939,631 bytes, 72 routines, 53,970 ST tokens.
  - `fraktal_ab_press_s6_collapse_echo38`: SHA-256 `32C48BA5606291199C66D685DD4C68BC7426CB85C945AD2AAA4700A7980A7C40`,
    5,448,374 bytes, 66 routines, 46,868 ST tokens.
  - `fraktal_ab_press_s6_shelving_echo38`: SHA-256 `3802DE1991638AFD74B95F7A4ECE4DCE49F849AAA3FE91F692ED5F145DBF23C3`,
    5,448,594 bytes, 66 routines, 46,890 ST tokens.
  - `fraktal_ab_press_s6_production_echo38` (R5 single-rendition LD): SHA-256 `8AA06AFEEAEE71FA077CEDDBD091E2DD0041820DCA1B5101011266FC28B43CAF`,
    5,351,655 bytes, 62 routines, 43,555 ST tokens.
  - R5 Savings: 96,719 bytes, 4 routines removed, 3,313 ST tokens removed.
- **Full Allen-Bradley Test Suite (2,748/2,748 passed)**:
  `ab_full_suite_01` ran `python -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools -t FraktalCore/PLC/Allen-Bradley/tools`
  in 2,858.712s: all 2,748 tests passed clean (`OK`, exit code 0).
- **Protected Files**:
  Owner edits in `.vscode/settings.json`, `FraktalCore/PLC/Siemens/Tests/Manifest/README.md`,
  and `analysis_options.yaml` were verified byte-for-byte identical before and after
  (`unrelated_before.json`, `unrelated_after.json`) and remain excluded.

## Surface and Rendition Architecture

- **Requirement R5 Compliance**:
  - In production declarations, each mode's cycle graph is carried in the author's chosen
    language (`press_demo` and `press_echo38` select LD; `station_template` selects ST).
    Because `multi_rendition` is false, `multi_chains(app)` is empty and no
    `FRK_{app.name}_RenditionSelect` tag is generated. The single routine is called directly
    without runtime conditional branching.
  - In acceptance declarations, all three renditions (`ST`, `SFC`, `LD`) are retained so the
    rendition-parity gate (`fraktal_ab_press_parity.py`) can cycle through each language on
    the soft controller and verify bitwise and behavioral identity across scan boundaries.
- **Zero Surface Differences for Acceptance Declarations**:
  Because acceptance declarations retain all three renditions, no tags or types are removed
  from the gated acceptance surfaces. The schema-identity gate passes with zero uncovered
  and zero unused differences.

## Provenance and Append-Only Logs

All executions and measurements are recorded in `C:/work/fraktal-ab-c7-control-20261108/`:
- `test_collapse_c7_01.log` & `_exit.json`: Dedicated C7 unit tests (passed).
- `schema_identity_01.log` & `_exit.json`: 10 schema identity tests across 5 declarations (passed).
- `root_tests_01.log` & `_exit.json`: Root consistency tests (passed).
- `check_consistency_01.log` & `_exit.json`: Strict consistency check (passed).
- `check_ab_spec_01.log` & `_exit.json`: AB spec check (passed).
- `check_ab_contracts_01.log` & `_exit.json`: AB frozen contracts check (passed).
- `flutter_test_01.log` & `_exit.json`: Host services manifest Dart test (passed).
- `flutter_test_v612.log` & `_exit.json`: V6.12 manifest Dart test (passed).
- `measure_profiles_01.log` & `_exit.json`: Profile size, routine, and token measurements.
- `ab_full_suite_01.log` & `_exit.json`: Full AB test suite (2,748 passed in 2,858.712s).
- `unrelated_before.json` & `unrelated_after.json`: Protected file identity verification.

## Remaining and Next

With Increment C7 qualified, the offline collapse increments (C0–C7) of WP6.6 are complete:
1. **Native S6-Q**: Live controller qualification on Echo under standing authorization O3
   (collapsed genealogy-S4b image, dedicated shelving acceptance image, then normal collapsed press image).
2. **WP6.7**: Final deletion of retired legacy runtime (RT/MO) and import census.
3. **WP6.8**: Specification documents and active contract transition.

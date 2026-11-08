# S6 C5c Frame/staged endpoint retirement and V6.12 - offline qualification

This slice qualifies Increment C5c of the Allen-Bradley canonical collapse (WP6.6):
retiring the legacy Frame ingress and staged request endpoints from collapsed profiles,
publishing manifest wire schema minor 12 (V6.12), updating generic Python and Dart
readers to enforce empty services while retaining host services, and validating
external surface schema identity across all five gated declarations.

Parent commit `08882bcd4d5071d5731ba3df8725c8211eaffac0`. The owner authorizes
commit/push on main. No controller connection, download, tag write, mode change,
fault/TASK clear, clock, power, or vendor-state operation ran.

## Results

- **2,742 AB tests** (`ab_full_suite_02` passed in 2,535.982s), **36 root tests**
  (`root_tests_01` passed in 4.519s), **8 dedicated collapse tests**
  (`test_v612_03`), **2 Dart manifest tests** (`flutter_test_01`, `flutter_test_v612`),
  **10 schema identity tests across 5 declarations** (`schema_identity_01` in 457.517s),
  and the root spec, frozen contract, and strict consistency gates (0 errors, 0 warnings) pass.
- **V6.12 Wire Protocol**:
  - `COLLAPSE_MINOR = 12`, `COLLAPSE_HEADER = HOST_HEADER`.
  - Manifest header sets `ServicesCount = 0`, `ServicesCapacity = 0`, and the `Services`
    member table is empty (`Services = []`).
  - `HostServiceBindings` from V6.11 is retained in full.
  - Generic Python reader (`fraktal_ab_canonical_reader.py`) and Flutter/Dart client
    (`cip_manifest.dart`) updated to decode minor 12 and enforce that `Services` is empty.
- **Retirement of Frame and Legacy Staged Endpoints** on collapsed profiles (`app.canonical_collapse=True`):
  - In `fraktal_ab_mailbox.py`: `ConfigSet`, `Frame`, and `ConfigProvider` UDT members
    are omitted from `FRK_T_{app.name}HmiRequestV4`. Frame data types and frame tags
    are omitted.
  - `request_tag_name(app)` (`FRK_{app.name}_HmiRequest`) is retired from the public
    read/write surface and set to private working buffer (`ExternalAccess="None"`).
  - In `fraktal_ab_config_provider.py`: `services(app)` returns `[]`.
  - In `fraktal_ab_canonical_commands.py`: `wipe_transport(app)` omits Frame words wipe.
    `ingress(app)` streamlines to direct `{commit_tag(app)}` handling without legacy
    Frame decoding or collision logic.
- **Schema Identity**:
  - Uncollapsed baseline profiles (`fraktal_ab_genealogy_s6_host_demo`,
    `fraktal_ab_press_canonical_echo38`) remain byte-identical with zero diffs.
  - Collapsed profiles pass with zero uncovered and zero unused differences:
    - `fraktal_ab_genealogy_s6_collapse_demo`: SHA-256 `7DBF0F40112F6B12409398FFA85B6EE47326A8EF5DEA3BE80305E2F7E49231BC`,
      5,939,681 bytes, 72 routines, 53,970 ST tokens.
    - `fraktal_ab_press_s6_collapse_echo38`: SHA-256 `5D0C329D6A1CA51DE519B4B4DE161A6C1996EB53BB76AE94FB7500305601C726`,
      5,448,424 bytes, 66 routines, 46,868 ST tokens.
    - `fraktal_ab_press_s6_shelving_echo38`: SHA-256 `36D9572B2E198A97B7A34AD9B89B7797F7024A4BD682A8A46952CA57DBB50C18`,
      5,448,644 bytes, 66 routines, 46,890 ST tokens.
- **Protected Files**:
  Owner edits in `.vscode/settings.json`, `FraktalCore/PLC/Siemens/Tests/Manifest/README.md`,
  and `analysis_options.yaml` were verified byte-for-byte identical before and after
  (`unrelated_before.json`, `unrelated_after.json`) and remain excluded.

## Ingress and Service Retirement

- **Private working buffer**: In collapsed profiles, `FRK_{app.name}_HmiRequest` is
  no longer write-accessible to external clients (`ExternalAccess="None"`). All command
  ingress routes through the canonical command commit tag (`FRK_{app.name}_CoreCommandCommit`)
  and payload structure (`FRK_{app.name}_CoreCommandPayload`) introduced in C5a under O11.
- **Streamlined transport wipe**: Command payload and sample argument buffers
  (`Secret`, `TextValue`) continue to be wiped upon execution, but legacy frame word
  loops (`Frame.Words`) are completely eliminated from the generated ST logic.
- **Additive V6.12 schema**: Minor 12 formalizes the transition from PLC-side staged
  request handling to canonical gateway-mediated transactions while maintaining full
  backward compatibility with V6.11 host service bindings (`HostServiceBindings`).

## Provenance and Failed Runs

In accordance with the append-only rule, all attempts and diagnostics in
`C:/work/fraktal-ab-c5c-control-20261107/` are sealed and preserved:
- `schema_identity_baseline`: Failed due to CLI argument structure in `run_logged.py`.
  Preserved in `schema_identity_baseline.log` and `_exit.json`.
- `schema_identity_baseline_02`: Failed due to flat import resolution without directory
  cwd. Preserved in `schema_identity_baseline_02.log` and `_exit.json`.
- `dart_test_01`: Failed because root HMI uses Flutter test runner rather than standalone
  Dart test runner. Preserved in `dart_test_01.log` and `_exit.json`. Corrected in
  `flutter_test_01` (passed).
- `test_v612_01`: Failed on header validation when injecting `ServicesCount` without
  member in test fixture. Corrected in `test_v612_02` (passed).
- `ab_full_suite_01`: Ran 2,742 tests; exactly one test failed (`test_the_press_emits_the_scan_bindings_its_live_reader_requires`
  in `test_fraktal_ab_fixture_observation.py` asserting old minor `'11'` instead of `'12'`).
  Updated assertion to `'12'`; `test_fixture_obs_01` passed, and `ab_full_suite_02`
  passed all 2,742 tests clean.

## Remaining and Next

C5 is complete with C5c:
1. **C6 / C7**: Canonical integration and baseline switch.
2. **Native S6-Q**: Live controller qualification on Echo after C7 under O3.
3. **WP6.7**: Final deletion of retired legacy runtime and import census.
4. **WP6.8**: Specification documents and active contract transition.

# S6 C5b3 standalone canonical press launcher - offline qualification

This slice qualifies the standalone canonical press launcher
(`fraktal_ab_press_canonical_execute.py`) migration onto canonical/O10 views,
isolated seed-manifest commissioning (`fraktal_ab_harness_seed.record`), and
MO-free `PressRun` execution for `fraktal_ab_press_s6_collapse_echo38` and
`fraktal_ab_press_s6_shelving_echo38`. It is not the exit of C5b3 or C5.
Parent `0730d3feb4ee8877c0e63ad31710a73ad7c11644`. The owner authorizes
commit/push on main. No controller connection, download, tag write, mode change,
fault/TASK clear, clock, power or vendor-state operation ran.

## Results

- **2,722 AB tests** (`ab_full_suite_02`), **85 root tests** (`root_tests_01`),
  **82 focused checks** (`focused_tests_03`) and the root spec, contract and
  strict consistency gates pass.
- All original check and wait predicates are preserved:
  - `fraktal_ab_press_canonical_execute.py`: all **10 original `check` messages**
    (15 total after adding isolated-medium and seed-manifest verification) and
    all **6 `wait` predicates** match verbatim.
  - `PressRun` AST is **byte-identical to the C3 baseline** (`fixtures/press_predicates_c3.json`),
    retaining `px.read_module(self.comm, 'PressRam')` (which already routes to
    `fixture_reads.read_module(..., app=APP)` under C5a).
  - The **`0.75` s hold sleep bound** is preserved verbatim.
- Static AST reachability across all **6 migrated runners** (`fraktal_ab_press_canonical_execute.py`,
  `fraktal_ab_tower_execute.py`, `fraktal_ab_part_execute.py`,
  `fraktal_ab_genealogy_execute.py`, `fraktal_ab_resource_execute.py`,
  `fraktal_ab_text_resource_execute.py`) reports **0 unguarded collapsed-reachable
  legacy/MO calls**; 27 legacy/MO calls remain strictly inside `not app.canonical_collapse`,
  `not collapsed`, or `paired_run` branches until WP6.7.
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
- All **84 shipping HMI/Dart sources** and both prepared runtime executables
  (`fraktal_gateway.exe` `11AE9906D53A58BEA59B301F28213DD0BF835FA9497514E612344C646F4E3200`,
  `fraktal_host_adapter.exe` `D3A681CDD066FA0F39E2368EA2CF6D868A95DC893B8A19560CE1AE30F475391B`)
  match C5b2's sealed `runtime_bindings_01.json`, reusing its 44 Dart tests,
  analyzer, locked dependencies and host builds by hashes.

## Standalone authorization, isolated seeding, and MO-free execution

- **Exact-image authorization without MO.** Standalone `authorize(path, pin)`
  validates that `CurrentOwnerApproved is True`, `MailboxOrTagWritesAuthorized is True`,
  `Serial == '601FC87B'`, `CanonicalSha256 == pin`, and `FaultClearAuthorized` and
  `ClockSetAuthorized` are both explicitly `False`. Non-hex pins, wrong serials,
  missing flags or truthy clear/clock flags are refused immediately with
  `FixtureRefused('current exact-image press authorization required')` without
  importing or invoking `fraktal_ab_s3k_fixture_execute`.
- **Isolated seed-manifest commissioning.** `seed_medium(run)` on the collapsed path
  enforces that `ISOLATED_SEED_ENV` is set, verifies that no pre-existing
  `FRAKTAL_HARNESS_HOST_SEED*` or `<dir>_seed.json` or live store files exist
  (`'isolated press medium must start empty'`), reads `expected_documents` from
  the published V6.8 `ConfigView`, validates `views.revision(...) == epoch`,
  writes each document into `FileMedium(directory / 'live')`, records
  `<dir>_seed.json` via `harness_seed.record(...)`, exports `FRAKTAL_HARNESS_HOST_SEED`
  and its SHA-256, and records `pressMedium` evidence.
- **Seeded document equivalence.** Over the emitted V6.8 `ConfigView` of
  `fraktal_ab_press_s6_collapse_echo38` and `fraktal_ab_press_s6_shelving_echo38`,
  the 5 seeded live documents (`Press.station`, `Press.line`, `Press.model1`,
  `Press.model2`, `Press.model3`) match the invariant headers and record payloads
  of legacy `fraktal_ab_live.documents` byte-for-byte.
- **Environment cleanup.** `isolate_medium(output, canonical_collapse=True)`
  and `main` manage the isolated directory lifecycle, popping `ISOLATED_SEED_ENV`
  and `FRAKTAL_HARNESS_HOST_SEED*` in `finally`, even if inner argument parsing
  or runner initialization rejects.
- **MO-free PressRun execution.** `main` routes collapsed execution directly to
  `live.main` with `run_type_factory=lambda _out: PressRun`, schema
  `fraktal.ab.press-collapse-fixture`, and `exercise_rows=press_rows`. Full end-to-end
  simulation exercises all 23 rows (two leading rows + seven core cases in each of
  ST, SFC and LD: `OK`, `handled_NOK`, `HELD_resume`, `abort`, `mode_change`,
  `adopted_fault`, `single_reset_restart`), verifying zero MO (`TypedRun`, `PairedRun`,
  `s3k`) invocation, and verifying `restored=True`, `policyRestored=True`,
  `originalMediumUnchanged=True`, and `liveDocumentsVerified=True`.

## Retained failed runs

All failed preparation and gate runs remain sealed in `Gates/` and
`Investigation/`:

- `focused_tests_01` hit `KeyError: 'Unit_ErrorSource'` in `test_fraktal_ab_press_launcher_canonical.py`
  because the mock collapsed controller's `private_value` dictionary did not include
  all 19 Unit fields declared in `FIXTURE`. Corrected in `focused_tests_02` (74/74 passed)
  by looking up declared fixture fields dynamically and defaulting non-essential
  observation slots to 0.
- `ab_full_suite_01` passed 2,721 of 2,722 tests and caught one failure:
  `test_fraktal_ab_fixture_reads.NativeViews.test_press_walk_and_canonical_case_predicates_are_unchanged_from_c3`
  failed because `PressRun.held` line 94 had been edited from
  `px.read_module(self.comm, 'PressRam')` to `self.module('PressRam')`. Since
  `px.read_module` is already `partial(fixture_reads.read_module, app=APP)` under C5a,
  restoring the line preserved exact C3 AST identity. `focused_tests_03` (82/82),
  `verify_launcher_gates_02` (all passed, including C3 AST identity check), and
  `ab_full_suite_02` (2,722/2,722) all passed.

## Remaining and next

Next in C5b3 are the remaining station-reading HX harnesses:
1. `fraktal_ab_press_parity.py` (ST/SFC/LD AUTO graph trace parity);
2. `fraktal_ab_phase1_execute.py` (alarm log, step conditions, diagnostics);
3. `fraktal_ab_phase2_execute.py` (§3.13 flow chart);
4. `fraktal_ab_phase3_execute.py` (reasons, watchdog, rollup);
5. `fraktal_ab_phase4_execute.py` (manual commands, collision interlocks, release reports);
6. `fraktal_ab_s3_execute.py` (read-only GSV health probe).

(`fraktal_ab_s9_mutations.py`, `fraktal_ab_s9_read_execute.py`, and
`fraktal_ab_s9_write_execute.py` test the Python gateway/projection subject itself
and retire with RT/MO in WP6.7; `fraktal_ab_mailbox_execute.py` speaks the
`fraktal.opcua.gateway.v1` WebSocket protocol directly with zero legacy station reads).

Then C5c removes Frame/staged endpoints and publishes V6.12; C6/C7, native S6-Q,
final deletion/import census and specification activation follow. Physical S7
remains deferred under O2. Owner edits in `.vscode/settings.json`, the Siemens
Manifest README and root `analysis_options.yaml` remain untouched and excluded.
No credentials are archived.

[Payload and hashes](AB_S6_COLLAPSE_C5B3_LAUNCHER_OFFLINE_2026-11-07/artifact_manifest.json)
(`5922148E5BFE3633670270A56BF28BEB811D8E228814EA355B624DDEB89BBF01`) bind
sources, outputs and retained failures. L5X/ACD/EXE artifacts remain private
and hash-bound.

# S6 C5b3 shared runner and disconnect lifecycle - offline qualification

This slice qualifies the shared inherited runner (`fraktal_ab_tower_execute`,
`fraktal_ab_part_execute`, `fraktal_ab_genealogy_execute`,
`fraktal_ab_resource_execute`, `fraktal_ab_text_resource_execute`), canonical
`SignalTower` acquisition, seed-manifest preservation across image revisions,
and the explicit disconnect/phase ownership boundary. It is not the exit of
C5b3 or C5. Parent `6865e75fd4e224bd917c9874acc4dfd58d23d84f`. The owner
authorizes commit/push on main. No controller connection, download, tag write,
mode change, fault/TASK clear, clock, power or vendor-state operation ran.

## Results

- **2,716 AB tests** (`ab_full_suite_02`), **85 root tests**, **71 focused
  tests** (`focused_tests_04`) and the root spec, contract and strict
  consistency gates pass.
- All original check and wait predicates are preserved:
  - `fraktal_ab_tower_execute.py`: all **5 original `check` messages** (7 total
    after adding isolated-medium/seed checks) and all **8 `wait` predicates**
    match, retaining the full **`disconnected = 3.2` s** quiet interval and the
    **`not expired['SignalTower/TestActive'] and elapsed < 4.0`** expiry bound.
  - `fraktal_ab_part_execute.py`: all **25 `check` predicates and 11 `wait`
    predicates** match.
  - `fraktal_ab_genealogy_execute.py`: all **3 `check` predicates** match;
    `ACCEPTED_DECLARATIONS` accepts `fraktal_ab_genealogy_demo` and
    `fraktal_ab_genealogy_s6_collapse_demo` by default while honoring an
    explicit `expected_declaration`.
- Static AST reachability across all **5 migrated runners** reports **0
  unguarded collapsed-reachable legacy calls**; 20 legacy calls remain strictly
  inside `not app.canonical_collapse` branches until WP6.7.
- Zero PLC generator or declaration sources changed. All three collapsed L5X
  profiles regenerate byte-identically to their sealed C5b3 pins:
  - `fraktal_ab_genealogy_s6_collapse_demo`:
    `57FDB0BC88CF1D8E6F3D5F325B51F61DFD5C110CE5C795A6BE9871B26F5042FE`
    (prepared ACD `7A7B7619A5E5C7D850C93CD968685249E7B502459E9E6DDC0923B19324FFC335`,
    **60% Studio Capacity**, 1,916,892 / 3,145,728 Blocks).
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

## Lifecycle, preservation and disconnect ownership

- **Canonical `SignalTower` view.** `views.signal_tower(comm, app=app)` reads
  `<root>/MachineState` and `<root>/SignalTower/{Red,Amber,Green,Blue,White,Horn,TestActive}`
  under one scan-counter row proof, rejecting out-of-domain `MachineState`
  values or non-boolean lamp leaves. Replayed over the sealed S6 native capture,
  it matches the legacy projection exactly; this is a replay of accepted bytes,
  not a new native session.
- **Seed-manifest authority and cross-revision preservation.**
  `read_seed_files` in `fraktal_ab_harness_host.py` is extracted as the single
  validation owner (O9) shared by `seed_store` and `seed_documents`, checking
  manifest SHA-256, schema/serial/root, `STORE_FILE` whitelist, symlink and
  containment bounds, the 16 MiB budget and per-file SHA-256s without touching
  the original directory. `compare_seed_documents` in
  `fraktal_ab_harness_documents.py` verifies invariant header metadata (`set`,
  `root`, `kind`, `model`, `records`) and every record payload excluding `rev`
  against post-restore `expected_documents`, recording `previousRevisions` and
  `currentRevision`.
- **O11 write scope and explicit connection phases.** Collapsed `Guarded`
  restricts `allowed` to `frozenset(gen.externally_writable(app))` (forbidding
  direct CIP writes to `HmiRequest` or `ConfigSet`) and sets `allowed = frozenset()`
  when `writable=False`. Before `LAMP_TEST`, `exercise` opens a separate
  read-only `observer` (`comm.open_observer()`) and warms its S1 discovery once.
  `comm.close_phase()` closes the primary session and its owned `GatewayLease`
  and `HostLease`; zero traffic crosses either connection during the complete
  `3.2` s disconnect sleep; `observer` then reads the expired `SignalTower` row
  within `elapsed < 4.0` s and closes in `finally`. `comm.open_new_phase()`
  starts a fresh guarded phase (and fresh isolated `HostLease` when live
  documents were active) without ever restarting or clearing a latched
  `ProcessLease` failure. If an assertion fails while `_phase_closed is True`,
  `execute_fixture`'s `finally` opens phase 2 (refusing if any lease had a
  latched failure) so controller state, access policy and logout still restore,
  and checks `originals_unchanged()` and `host_docs.ready()`.
- **Portable `HostEvents` verification.** Collapsed `Run` routes `command`,
  `unit`, `module`, `set`, `begin`, `held` and `verify_sink` through `views`
  and declaration-free `fraktal_ab_host_cursor.Cursor` without `px.APP`
  import-order coupling.

## Retained failed runs

All failed preparation and gate runs remain sealed in `Gates/` and
`Investigation/`:

- `inspect_runner_facts_01` called a nonexistent `gen.program_routines` helper;
  `inspect_runner_facts_02` inspected `app.fixture_observation` directly.
- `focused_tests_01` hit `TypeError` on `Mock` iteration in
  `Guarded.check_owned_leases` and attached a test-double gateway lease during
  read-only S1 bind; `focused_tests_02` used `Service=2` instead of
  `SERVICES['HostEvents']` in `FakeRowReader`. Both were fixed before
  `focused_tests_03` passed (68/68).
- `verify_runner_gates_01..04` corrected AST line sorting, `ast.With` handling,
  nested-function guard propagation and positional `fraktal_ab_generate.py`
  arguments; `verify_runner_gates_05` checked `shippingSources` instead of
  `sources` in C5b2's `runtime_bindings_01.json`, corrected in
  `verify_runtime_sources_01` and `verify_runner_gates_06` (84 sources).
- `ab_full_suite_01` passed 2,715 of 2,716 tests and caught one error in
  `test_fraktal_ab_phase6_sets_execute`: `getattr(comm, '_phase_closed', False)`
  evaluated truthy on an unconfigured `unittest.mock.Mock`. Checking
  `is True` in `views._session` and `tower.execute_fixture` resolved it without
  weakening any phase or lease guard; `inspect_ab_suite_01` hit a Windows
  cp1252 console print on `\ufffd` and was replaced by UTF-8 JSON
  `inspect_ab_suite_02`. Fresh `focused_tests_04` (71/71), `freeze_tools_02`,
  `verify_runner_gates_06` and `ab_full_suite_02` (2,716/2,716) all pass.

## Remaining and next

Next in C5b3 is the standalone canonical press launcher
(`fraktal_ab_press_canonical_execute.py`), followed by the remaining
station-reading HX harnesses (`fraktal_ab_press_parity.py`,
`fraktal_ab_phase1_execute.py` through `fraktal_ab_phase4_execute.py`, and
`fraktal_ab_s3_execute.py`; the three `fraktal_ab_s9_{mutations,read_execute,write_execute}.py`
Python-gateway subjects retire with RT/MO, and `fraktal_ab_mailbox_execute.py`
speaks the gateway WebSocket protocol directly). Then C5c removes Frame/staged
endpoints and publishes V6.12; C6/C7, native S6-Q, final deletion/import census
and specification activation follow. Physical S7 remains deferred under O2.
Owner edits in `.vscode/settings.json`, the Siemens Manifest README and root
`analysis_options.yaml` remain untouched and excluded. No credentials are
archived.

[Payload and hashes](AB_S6_COLLAPSE_C5B3_RUNNER_OFFLINE_2026-11-07/artifact_manifest.json)
(`B43B30703E18292E3794E23021084300B5A9B94DF997795F9B4B84983ABB9192`) bind
sources, outputs and retained failures. L5X/ACD/EXE artifacts remain private
and hash-bound.

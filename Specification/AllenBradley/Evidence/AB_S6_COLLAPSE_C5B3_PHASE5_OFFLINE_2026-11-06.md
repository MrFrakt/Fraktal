# S6 C5b3 Phase 5 metrics and reports - offline qualification

Work started on 2026-11-06; final gates completed on 2026-11-07
(America/Mexico_City). UTC process times are retained in the receipts.

The Phase 5 metrics, OEE, profiler, command-timing, state-flag, system-health
and run-style harness (`fraktal_ab_phase5_execute.py`) passes offline on
canonical CIP rows and O10 private observations. Parent `7b793c516bc48bb50ae5b2337e99b8ab63e001bd`. The
owner authorizes commit and push on main. No controller connection, download,
tag write, mode change, fault/TASK clear, clock, power or vendor-state
operation ran.

## Results

- **2,696 AB tests** by discovery from tools, **85 root tests**, **62 focused
  Phase 5/policy/capture/document/schema checks**, **27 native-capture replay
  and storage checks**, and all root gates pass.
- **All 21 Phase 5 `px.row(...)` predicates and all 16 wait predicates** are
  preserved without weakening tolerances, logical operators or value checks.
  Direct legacy projection and layout calls in `fraktal_ab_phase5_execute.py`
  drop from **18 to 0**.
- **O10 grows from 102 to 141 private facts (+39)** across `Unit`, `Door`,
  `PartSlide`, `PartPresentSensor`, `PressRam`, `Profiler`, `AlarmActive`,
  `AlarmRing` and `Oee`, shared by `fraktal_ab_press_s6_collapse_echo38` and
  `fraktal_ab_press_s6_shelving_echo38` (`FRK_T_PressFixtureV2_2A276D94`). All 39 new
  facts replay across all **86 accepted native press captures**; canonical
  metric/report views (`oee_card`, `machine_summary`, `run_style_offer`,
  `profiler_summary`, `timing_row`, `alarm_ring_entry`, `state_flags` and
  `system_health`) match the native projection across all 86 capture pairs.
- **Both v38 press profiles build and read back** on `EchoController` and
  `PhysicalController` and pass SDK, native access and default audits:
  - Normal press (`fraktal_ab_press_s6_collapse_echo38`): **54%** Studio
    Capacity (**1,726,208 used / 1,419,520 available / 3,145,728 Blocks**,
    **+13,004 used** versus prior C5b3 press). Prepared source SHA-256
    `0E3E19A822B781EDEFCC38259DDA6F533D94624E66A68415DB20174DAD3AF7A0`; prepared ACD SHA-256
    `B2E1648624D4BAB46A1E8300492EDC962D6C292AAF7F843C823CDDC957439353`.
  - Shelving acceptance profile (`fraktal_ab_press_s6_shelving_echo38`):
    **54%** Studio Capacity (**1,726,244 used / 1,419,484 available / 3,145,728
    Blocks**, **+13,004 used** versus prior C5b3 shelving profile, **+36**
    versus the normal press). Prepared source SHA-256
    `D7FB6960255F48EDC9FF9288A625A903BE8A93BF2CE26D71353C0AA34D6A131D`; prepared ACD SHA-256
    `A7016651DB9655265F1999954C16EB8C596743FE668E03E246A06E57203EA574`.
- **Exact token and schema proof:** after removing the 39 appended O10 copy
  statements (+552 ST tokens) in `FRK_Press_CopyFixtureObservation` and
  normalizing C4c's code-derived AOI signatures (`FRK_M_CylinderR8C4633CD7D0Rev`,
  `FRK_U_Press_CountV1R8C4_C4C17B3C23`), V5 localization key renumbering and
  four equivalent text-pool slices, all **66 routines** match the prior C5b3
  sources token-for-token (`125,551 -> 126,103` ST tokens on the normal press;
  `125,560 -> 126,112` on the shelving profile). Between the two profiles, **65
  routines are identical** and `FRK_Press_ScanHealth` differs only by the 9
  tokens of `FRK_Press_SystemHealth.Bad[2] := 1;`. Public schema, initial
  values and all three derived manifest hashes match between both press
  profiles and pass the pre-collapse schema-identity gate with zero uncovered
  differences or unused declarations.
- **Genealogy (`fraktal_ab_genealogy_s6_collapse_demo`) is byte-identical** to
  its sealed C5a source (`07C771DF2BEBAAD59CE33611579F70ACFE92B76BB0A658783A761614E36DB417`),
  reusing its hash-bound v38 builds, read-backs and 60% Studio Capacity.
  Shipping HMI/Dart sources (84 files) and both prepared runtime executables
  match the committed C5b2 bindings, reusing its 44 Dart tests.

## Ownership and scope

In collapsed images (`canonical_collapse=True`), C1/R3 removes `TimCount`,
`TimLast`, `TimMin`, `TimMax` and `TimAvg` from module contexts because the
cylinder AOI writes directly to its canonical leaf `Timing.Rows[0..1]`.
`fraktal_ab_fixture_reads.py` therefore exposes `TimCount` and `TimLast` on
cylinder surfaces (`Door`, `PartSlide`, `PressRam`) as canonical public aliases
backed by `{module}/Timing/Rows[1..2]/Count` and `Last` under the same scan
proof, while `Busy`, `DoneCount`, `OutImm_Extended`, `OutImm_Held` and
`RunCount` on cylinders, `OutImm_Value` on `PartPresentSensor`, and `HoldRun`,
`Issued` and `StepPending` on `Unit` are observed through O10. Because C4c
derives AOI parameter/local classification from `fixture_observation`, observing
those five cylinder fields promotes them from `Local` to `Output` parameters on
the cylinder AOI and updates the derived C4 signature hashes and V5 field
tables; `fraktal_ab_phase5_execute.py` resolves refusal diagnostic keys from
the deployed PLC command table (`views.numeric_key`) rather than generator-side
ordinals.

Canonical `SupportedRunStylesPublished` on the PLC root uses a 0-based lower
bound (`0..2`), whereas the legacy Python projection indexed it `1..3`;
`views.run_style_offer` handles each representation without changing the case
assertion. `views.state_flags` validates `StateFlagCount` before and after
reading the active rows, and `down_time_row` brackets its canonical OEE read
with `read_oee` so `DownMs` remains paired with the native `Epoch`, `DownS` and
`DownRemUs` sample counter.

Phase 5's `health_rows` requires both the published `SystemHealth` facet and a
standing reason-21 (`CONTROLLER_METRICS_UNAVAILABLE`) warning in `AlarmActive`
with `Blocking == 0`. That precondition is satisfied by
`fraktal_ab_press_s6_shelving_echo38` after its second health sample, while
`fraktal_ab_press_s6_collapse_echo38` preserves the platform exclusion
(`require_controller_metrics=False`). Dedicated executed-ST tests in
`test_fraktal_ab_phase5_canonical.py` prove both behaviors offline. In S6-Q,
Phase 5's `health_rows` runs during the dedicated shelving acceptance phase or
with its precondition explicitly accounted, while the normal press keeps its
platform exclusion.

## Failed runs and remaining work

All failed control runs are retained in the sealed evidence:
- The first three `run_logged.py` invocations passed full paths and `--` as the
  label/command arguments; `run_logged.py` rejected the non-alphanumeric label
  before opening a log file.
- `generate_press_01`, `generate_shelving_01` and `generate_genealogy_01`
  invoked the declaration modules directly instead of `fraktal_ab_generate.py`,
  producing empty logs and causing `layout_proof_01`, `token_proof_01` and
  `genealogy_reuse_01` to fail with `FileNotFoundError`.
- After generating the L5X files in `*_02`, `layout_proof_02` assumed the 39
  new facts were appended at the tail of the flat UDT rather than grouped per
  surface in declaration order, and `token_proof_02` indexed `DECLARATIONS`
  directly for `fraktal_ab_press_s6_collapse_echo38` instead of `.get(...)`.
  Corrected `layout_proof_03`, `token_proof_03` and `genealogy_reuse_02` pass.
- `root_tests_01` passed `-t .` to `unittest discover -s tools`, which requires
  `tools/__init__.py`; `root_tests_02` omits `-t .` and runs all 85 root tests.

The updated source inventory (`next_hx_inventory_01.json`) confirms **0 direct
legacy calls across 21 row sites** in `fraktal_ab_phase5_execute.py`, leaving
3 direct legacy calls in `fraktal_ab_part_execute.py`, the genealogy wrapper
(`fraktal_ab_genealogy_execute.py`), inherited runners and the standalone
canonical press launcher (`fraktal_ab_press_canonical_execute.py`). Frame and
staged-service retirement with V6.12 follow in C5c, then C6/C7, native S6-Q,
final deletion/census and specification activation. Under O2, hardware-only S7
acceptance remains deferred without a date as a declared exclusion.

Owner edits in `.vscode/settings.json`, the Siemens Manifest README and root
`analysis_options.yaml` are preserved and excluded. No credentials are archived.

[Payload and hashes](AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06/artifact_manifest.json) bind source inputs,
outputs and failures. ACD/L5X/EXE artifacts remain private and hash-bound.
See the [working notes](../AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md)
and [plan](../AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

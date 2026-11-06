# S6 WP6.6 C4a — The O10 fixture observation, and no S3h frame

Prepared 2026-11-05; final gates and sealing completed 2026-11-06, America/Mexico_City. Entry commit `8e74160c6`, with the
uncommitted working tree. No controller was contacted. Design: the
[collapse review](../AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) and
plan decision O10.

## What changed

- **`fraktal_ab_fixture_observation.py`.** An acceptance declaration names,
  in `Application.fixture_observation`, the private facts its harnesses
  assert, per surface (`Unit`, `Chart` or a module).
  - *Validation* refuses it without the collapse, an unknown surface, a
    member the surface does not hold (so a fact with a canonical home, such
    as the Unit's mode since C2) and a repeat.
  - *Emission* is one flat UDT, `FRK_T_<Root>FixtureObservationV1`, with
    members `<surface>_<member>`, and its tag `FRK_<Root>_FixtureObservation`,
    which is Read Only.
  - *Writer.* `FRK_<Root>_CopyFixtureObservation` writes it each scan. The
    canonical publication calls it after its own writes, immediately before
    the generation's closing increment. The copy therefore lies inside the
    generation's odd window, and one even generation read before and after
    proves it together with the canonical rows. It never enters the
    manifest.
  - *Placement, corrected.* Source 11 called the copy from the scan plan,
    after that close. A reader could then see one unchanged even generation
    around a fixture still being written, so no proof would cover it. Review
    against O10's "under the same generation counter" found this while
    source 11's gates were running. Source 12 moves the call, and a test now
    pins the copy's caller, its line just before the close, and that nothing
    else writes the structure.
- **The press collapse** (`fraktal_ab_press_s6_collapse_echo38`) observes 29
  facts, taken from the read sites of `fraktal_ab_press_execute` and from
  PressRam's hold in `fraktal_ab_press_canonical_execute`:

  | Surface | Facts |
  |---|---|
  | Unit | 16: `Aborted`, `Complete`, `CycleCount`, `DecisionId`, `Error`, `ErrorID`, `ErrorSource`, `ModeSwitches`, `OrderFail`, `Par_TaskPeriodMs`, `ReportedCount`, `ReportedReason`, `ReportedSource`, `Running`, `SchemaVersion`, `StartLatched` |
  | Chart | 4: `LastMs[32]`, `StallReason`, `StepCursor`, `Visited[32]` |
  | Door | 5: `DoneCount`, `Error`, `Execute`, `ManualCmd`, `OutImm_Pos` |
  | PartSlide | 2: `ErrorID`, `Execute` |
  | TwoHand | 1: `OutImm_Armed` |
  | PressRam | 1: `OutImm_Held` |

  The harness also reads four facts that have a canonical home since C1/C2:
  the Unit's mode, step and scrap count, and PartSlide's state. They are not
  observed; C4b reads them from the canonical rows.
- **Both collapse declarations drop the S3h frame**
  (`canonical_observation_period_ms=0`). It copied the legacy contexts the
  collapse removes.
- **The genealogy collapse declares no fixture yet.** Its candidate-case
  harnesses' private facts are accounted when they migrate, as O10 requires.

## Results

**Source 11, superseded.** Its preparation passed with all exits 0: genealogy
`E25317EC…368F`, press `4B0E8592…AC91`, ACD `5FE46467…9D7E`, Capacity
1,921,584 blocks. Its code check (`Investigation/c4a_routines_01.py`,
`Gates/c4a_routines_01.json`) passed: against source 10, the only changes were the
frame block leaving `ScanCanonical` and, for the press, the fixture routine and its JSR
in the main routine. The check's first version assumed the frame was a routine of its
own; it failed on `ScanCanonical`, where the frame block lives, and was extended to
recognize exactly that block, and its first output was deleted. Its ST tokens are in
`Gates/st_tokens_01.json`. Gate run 01 (`Investigation/run_gates_01.py`) was stopped
after its first three gates had passed (the source binding, `dart analyze` and the
gateway's Dart tests) and while the focused Python suite was running, when the
placement defect above was found; `Gates/focused_python_01.log` is that partial log.
It wrote no summary.

**Source 12** (`Gates/Prepare/`, prepared in `C:/work/fraktal-ab-s6-host-20261104/prepare`), all exits 0:
- **Images:** genealogy collapse `E25317EC…368F`, press collapse `216E09BB…CBA4`.
  The BOOL-operand gate is clean for both. The genealogy declares no fixture, so its
  image is source 11's unchanged.
- **Legacy branch:** the V6.11 genealogy and the press candidate regenerate
  byte-identically to source 07 (`B9A37972…EAC0` and
  `91236742…0F54`).
- **Builds:** both collapsed images build, read back equivalent and pass the
  SDK log audit (the genealogy on both v38 targets, the press on Echo).
- **Access audit:** the genealogy's nested access audit passes on both targets
  (`audit_access_06`: `audit_access_05`, with its frame check guarded by
  whether the frame is enabled).
- **ACD and Capacity:** ACD `703EB692…A5C7`, read-back equivalent. Capacity is
  1,921,584 of 3,145,728 blocks (61%), a verified fit:
  304,228 blocks under source 10. That is the S3h frame and its copy block
  leaving, more than the capacity plan's 174-220 K estimate for the frame (a
  plus-or-minus 30% estimate, which this exceeds).
- **Scan-risk proxy** (`Gates/st_tokens_02.json`): the genealogy's ST tokens
  fall from 130,968 to 130,418, and the press's from
  97,749 to 97,513. The press adds the fixture routine and
  loses the frame block.

**The code check** (`Investigation/c4a_routines_02.py`, `Gates/c4a_routines_02.json`)
compares every program routine and AOI of source 10 with source 12, token by token.
- **Genealogy:** 71 routines, only `ScanCanonical` changed: the frame block
  removed, and nothing gained.
- **Press:** one routine added, the fixture copy. `ScanCanonical` lost the frame
  block and gained one line, the copy's JSR, immediately before the generation's
  closing increment. The main routine is unchanged.
- **Both:** no other difference.

`Investigation/run_gates_02.py` (`Gates/gate_summary_02.json`), all exits 0:
- **Sources:** 11 files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway, and its 44 tests pass, none skipped.
- **Focused Python:** 338 tests with ResourceWarnings raised as errors, none skipped.
  `test_fraktal_ab_fixture_observation` (8) covers:
  - validation;
  - the emitted copy, executed against random sources;
  - the structure being Read Only and outside the manifest;
  - the copy's place inside the generation window;
  - the frame's absence, and the genealogy's lack of a fixture.
- **Schema identity:** both collapse declarations hold their pre-collapse
  surfaces (34 declared changes for the genealogy, 36 for the press), every
  one used. The canonical tree is unchanged.
- **Full AB discovery:** 2,557 tests in 1,556 s, none skipped. All 415 tool
  sources are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates are clean.

## Boundary

Nothing reads the structure yet: C4b migrates the press harnesses onto it and
the canonical rows, with the offline gate on their predicates. Native proof
is S6-Q's.

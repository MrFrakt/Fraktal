# S6 WP6.6 C2 — The canonical root stores what the publication copied (R8)

2026-11-05, America/Mexico_City. Entry commit `5271bd5e2`, with the
uncommitted working tree. No controller was contacted. Design: the
[collapse review](../AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) §3–§4.

## What changed

Behind the S6-Q opt-in `canonical_collapse`
(`fraktal_ab_genealogy_s6_collapse_demo`, `fraktal_ab_press_s6_collapse_echo38`):

- **Eight members move to their canonical paths.** Each was copied every
  scan, unconditionally, from the Unit context or the chart:

  | Member | Canonical path |
  |---|---|
  | `Unit.Mode` | `ModeActivePublished` |
  | `Unit.Step` | `CurrentStep.StepNo` |
  | `Unit.DecisionAnswer` | `Decision.Default` |
  | `Unit.GoodCount` | `GoodCount` |
  | `Unit.ScrapCount` | `NokCount` |
  | `Unit.ReworkCount` | `ReworkCount` |
  | `Unit.RunStyle` | `RunStyle` (the application paces) |
  | `Chart.CurrentStepMs` | `CurrentStepElapsed` |

  Each member's declared initial value and its path's initial data are 0
  on both sides.
- **Kept.** Three copies are conditional and keep their own storage:
  - the step's expected time (zeroed, then set only while a step is selected);
  - the active-step row's elapsed time (only while the cursor matches);
  - the per-step last durations (slot-mapped into history rows).
- **How** (`fraktal_ab_collapse.rename_storage`, run once by `generate()`):
  - The pass rewrites only code: each `Line` and `Text` CDATA, so ST, SFC
    and ladder.
  - Controller-scope names change everywhere. Inside the Unit AOI and the
    part AOI, `Ctx.` and `Chart.` members move to `Root.`; every other AOI's
    `Ctx` is its own module's and is left alone.
  - The pass refuses to return text that still names a moved member.
  - The four copy sites emit nothing.
- **Signatures.** The Unit and part AOIs take the canonical root as `Root`.
  Their names take `R8`, which also corrects C1: it had changed the Unit
  AOI's parameter types without renaming it. The Unit context and chart
  types take `C2` names.

## Results

**Source 09** (`Gates/Prepare/`, prepared in `C:/work/fraktal-ab-s6-host-20261104/prepare`), all exits 0:
- **Images:** genealogy collapse `23FB5124…2960`, press collapse `AD851CC8…558D`.
  The BOOL-operand gate is clean for both.
- **Legacy branch:** the V6.11 genealogy and the press candidate regenerate
  byte-identically to source 07 (`B9A37972…EAC0` and
  `91236742…0F54`).
- **Builds:** the genealogy collapse builds, reads back equivalent, and
  passes the SDK log audit and its nested access audit on both v38 targets.
  The press collapse builds, reads back equivalent and passes the SDK log
  audit on Echo.
- **ACD and Capacity:** ACD `5C2C416E…8D85`, read-back equivalent. Capacity is
  2,229,924 of 3,145,728 blocks (70%), a verified fit:
  568 blocks under source 08.
- **Scan-risk proxy** (`Gates/st_tokens_01.json`): the genealogy's ST tokens
  rise from 131,508 to 131,706, and the press's from
  98,319 to 98,487. A canonical path is longer than the
  context member it replaces (`Press.CurrentStep.StepNo` against
  `FRK_Press_Unit.Step`), and the part calls pass the root.

**The rename proof** (`Investigation/c2_rename_proof_01.py`,
`Gates/c2_rename_proof_01.json`) compares each source 08 image with its
source 09 image, every program routine and AOI, token by token. It applies to
the C1 side exactly the changes C2 intends:
- the very rename pass C2 runs;
- dropping the copies it makes redundant;
- taking out the added `Root` arguments and the R8 names.

Every remaining difference must be explained, and none is left:
- **Genealogy:** 71 routines. 183 literals are localization keys
  that the two images' own tables renumber exactly (C2 removes eight
  field-path keys, and later keys shift). 8 are offsets into the constant
  text pool, whose bytes match at both offsets; the pool shrinks from
  17,129 to 17,033 bytes with those keys' text.
- **Press:** 62 routines, 181 renumbered literals and 10 pool offsets.
- **Both:** zero differences, and the Unit and part AOIs' parameters are
  C1's plus `Root`.

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`), all exits 0:
- **Sources:** 12 files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway, and its 44 tests pass, none skipped.
- **Focused Python:** 329 tests with ResourceWarnings raised as errors, none skipped.
  `test_fraktal_ab_collapse` adds the rename's scoping, the contexts' content,
  the AOIs' `Root` and the absence of any moved name or copy in the image. The
  C1 parity and the legacy pins still pass.
- **Schema identity:** both collapse declarations hold their pre-collapse
  surfaces, with 37 declared changes each (16 for C2), every one used. The
  canonical tree is unchanged.
- **Full AB discovery:** 2,548 tests in 1,519 s, none skipped. All 413 tool
  sources are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates are clean.

## Boundary

The collapsed images compile and read back on both v38 targets (the press on
Echo); native behaviour is S6-Q's. No routine read these canonical paths
before C2 (they were written only by the copies), so publishing them as the
storage changes no value any reader sees, only their address.

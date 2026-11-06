# S6 WP6.6 C1 — Each type AOI publishes its own canonical leaf (R3)

2026-11-05, America/Mexico_City. Entry commit `b10934f18`, with the
uncommitted working tree. No controller was contacted. Design: the
[collapse review](../AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) §3–§4.

## What changed

- **`fraktal_ab_collapse.py`** owns the collapse. `Application.canonical_collapse`
  turns it on, and validation accepts it only on the S3k publication.
  - Two new S6-Q declarations set it:
    `fraktal_ab_genealogy_s6_collapse_demo` (from the V6.11 genealogy) and
    `fraktal_ab_press_s6_collapse_echo38` (from the press S3 exit candidate).
    They inherit their predecessors' documents unchanged, since C1 changes no
    editable value.
  - Every other declaration keeps the legacy branch, byte for byte, until
    WP6.7.
- **The collapsed type AOI** (`FRK_M_<Type>R3`, plus `Rev` with owner
  revisions) takes its context (`FRK_T_<Type>CtxR3`), its canonical leaf
  `Leaf`, its module's header revision `Revision` and `Scan`. It writes the
  leaf directly:
  - `ExecState` is an AOI local, published as `Leaf.Status.State`. Under
    owner revisions it is published as the publication did: on the first scan
    or on a change, opening the header revision, which the publication still
    closes once at its end.
  - `Leaf.Status.FaultActive` is the module's `Error`.
  - Command timing accumulates in `Leaf.Timing.Rows`, for catalogued
    ordinals only: exactly the rows the copy layer published.
- **The context** loses `OutImm_ExecState` and the five `Tim*` arrays.
  `Error` stays: it is the shared §6.1 handshake the Unit and every type read.
- **The publication** no longer writes module state or `FaultActive`
  (`ScanCanonical`) or copies timing rows (`CanonicalDiagnostic`), and its
  diagnostic cache drops the timing counts it no longer compares.
- **The V5 field list**, the operand catalogue, the rendition condition check
  and the scope fence all follow the collapsed context.

## Results

**Source 08** (`Gates/Prepare/`, prepared in `C:/work/fraktal-ab-s6-host-20261104/prepare`), all exits 0:
- **Images:** genealogy collapse `E03CA618…0578`, press collapse `2C0A2991…F9B8`.
  The BOOL-operand gate is clean for both.
- **Legacy branch:** the V6.11 genealogy and the press candidate regenerate
  byte-identically to source 07 (`B9A37972…EAC0` and
  `91236742…0F54`).
- **Builds:** the genealogy collapse builds, reads back equivalent, and
  passes the SDK log audit and its nested access audit (`audit_access_04`)
  on both v38 targets. The press collapse builds, reads back equivalent and
  passes the SDK log audit on Echo. `S:FS` inside an AOI compiles on both.
- **ACD and Capacity:** ACD `0E1E78EA…EC18`, read-back equivalent. Capacity is
  2,230,492 of 3,145,728 blocks (70%), a verified fit:
  4,556 blocks under source 07.
- **Scan-risk proxy** (`Gates/st_tokens_01.json`): the genealogy's ST tokens
  fall from 132,477 to 131,508. Programs lose
  1,248 tokens of per-instance copy, and the AOIs gain
  279, once per type. The press falls from
  99,190 to 98,319.

**Run 01 failed** (`Gates/gate_summary_01.json`, kept as recorded) on one
root test, `test_the_read_surface_stays_on_the_reference_station`. The
consistency gate puts the AB tools on the path only within a scope, and the
generator imported the new collapse module lazily, after it:
`ModuleNotFoundError: No module named 'fraktal_ab_collapse'`. The generator
now imports it at module level, as it does its other collaborators. Both
collapsed images still regenerate byte-identically to source 08. Every other
gate in run 01 passed, the full AB suite included.

`Investigation/run_gates_02.py` (`Gates/gate_summary_02.json`), all exits 0:
- **Sources:** 15 files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway, and its 44 tests pass, none skipped.
- **Focused Python:** 324 tests with ResourceWarnings raised as errors, none skipped.
  - `test_fraktal_ab_collapse` runs every library type's legacy and collapsed
    bodies side by side for 400 scans under each of three seeded random input
    streams. After every scan the leaf equals what the copy layer published
    from the legacy context, and every member both contexts keep agrees.
  - It also checks the emitted image (signatures, calls, no copy, no
    in-scan reader of a module leaf) and the two legacy images' exact
    hashes.
- **Schema identity:** both collapse declarations hold their pre-collapse
  surfaces, with 21 declared changes each, every one used. The canonical
  tree is unchanged.
- **Full AB discovery:** 2,543 tests in 1,429 s, none skipped. All 413 tool
  sources are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates are clean.

## Boundary

The collapsed images compile and read back on both v38 targets (the press on
Echo); native behaviour is S6-Q's. The capacity saving is the first slice:
the copy layer for six modules was small, and the large R3/R8 savings the
capacity plan estimates come with the contexts and the V5 tables (C3, C6).
The S3h observation frame copies the R3 contexts, so a harness decoding it
must use the collapsed layout; C4 replaces the frame with O10's structure.

# S6 WP6.6 C3 — Each module context is its AOI instance (R8)

2026-11-05, America/Mexico_City. Entry commit `d28e309a0`, with the
uncommitted working tree. No controller was contacted. Design: the
[collapse review](../AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) §3–§4.

## What changed

Behind the S6-Q opt-in `canonical_collapse`
(`fraktal_ab_genealogy_s6_collapse_demo`, `fraktal_ab_press_s6_collapse_echo38`):

- **The context is the instance.** Each module context member is an Input
  parameter of the type AOI (`FRK_M_<Type>R8[Rev]`), not required and not
  passed in calls. The instance tag `FRK_<Root>_Inst<Name>` therefore holds
  the module's state, and the context tags `FRK_<Root>_Ctx<Name>` and their
  types go.
- **The body.** The AOI body names its members directly: `Execute`, not
  `Ctx.Execute`.
- **References.** Every program reference names
  `FRK_<Root>_Inst<Name>.<member>` (`fraktal_ab_collapse.rename_contexts`,
  code only, refusing any leftover). The Unit AOI takes each instance as an
  InOut of that instance's AOI type, and reads and writes its parameters as
  before.
- **Initial values, as a download carries them.**
  - A type's declared initial values are its parameters' `DefaultData`.
  - An instance's own values (its speed, timeout and task period) are its
    tag's Decorated initial data: `EnableIn`, `EnableOut`, `Scan`, then each
    member. That is the form Studio itself exports an AOI instance in.
- **The calls** pass the instance, the leaf, the header revision and the
  scan count; the context argument is gone.
- **The S3h frame** no longer copies module contexts. C4 replaces the frame
  with O10's structure.
- **Not yet.** No local tags and no member deleted. C4 narrows the parameters
  once O10's structure says which facts a harness still needs.

## Results

**Source 10** (`Gates/Prepare/`, prepared in `C:/work/fraktal-ab-s6-host-20261104/prepare`):
- **Images:** genealogy collapse `F28C550F…B6BB`, press collapse `97B2187E…6272`.
  The BOOL-operand gate is clean for both.
- **Legacy branch:** the V6.11 genealogy and the press candidate regenerate
  byte-identically to source 07 (`B9A37972…EAC0` and
  `91236742…0F54`).
- **Builds:** both collapsed images build, read back equivalent and pass the
  SDK log audit (the genealogy on both v38 targets, the press on Echo).
  Studio accepts AOI-typed InOut parameters. In the read-back, each instance
  tag keeps its own initial values and each parameter its default.
- **Access audit, run twice.** `audit_access_04` exited 1 on both targets,
  because it expects the S2 record's public tags, which include the six
  context tags C3 removes ("declared public but not present").
  `audit_access_05`, the same audit without them, passes on the same
  read-backs (`prepare_candidate_10b`).
- **ACD and Capacity:** ACD `50786CF9…2A4D`, read-back equivalent, taken from the
  same source bytes. Capacity is 2,225,812 of 3,145,728 blocks
  (70%), a verified fit: 4,112 blocks under source 09.
- **Scan-risk proxy** (`Gates/st_tokens_01.json`): the genealogy's ST tokens
  fall from 131,706 to 130,968, the AOIs by
  660 (a member is one token, not `Ctx.` and a name). The press falls from
  98,487 to 97,749.

**The proof** (`Investigation/c3_proof_01.py`, `Gates/c3_proof_01.json`)
compares each source 09 image with its source 10 image, every program routine
and AOI, token by token. It applies to the C2 side exactly the changes C3
intends:
- the very context rename C3 runs;
- bare member names in the type AOIs;
- the dropped context argument;
- the dropped frame copies.

No numeric literal may differ. The genealogy (71 routines) and the
press (62) show zero differences, and every module AOI's parameters are
C2's minus `Ctx`, plus one Input per context member.

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`), all exits 0:
- **Sources:** 8 files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway, and its 44 tests pass, none skipped.
- **Focused Python:** 330 tests with ResourceWarnings raised as errors, none skipped.
  `test_fraktal_ab_collapse`:
  - runs the C1 parity against the flat parameter set;
  - checks each AOI's members as Input parameters, each instance tag's
    initial values, and that no context tag or type remains;
  - checks the Unit AOI's instance-typed InOuts.
- **Schema identity:** both collapse declarations hold their pre-collapse
  surfaces, with 36 declared changes each, every one used. The canonical
  tree is unchanged.
- **Full AB discovery:** 2,549 tests in 1,479 s, none skipped. All 413 tool
  sources are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates are clean.

## Boundary

The collapsed images compile and read back on both v38 targets (the press on
Echo); native behaviour is S6-Q's. Every member stays readable and writable
through its instance tag, and that tag is `ExternalAccess="None"`, as it was
before, so no client gains access to any of them.

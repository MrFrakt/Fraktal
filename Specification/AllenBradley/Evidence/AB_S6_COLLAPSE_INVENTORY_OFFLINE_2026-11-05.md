# S6 WP6.6 C0 — Context inventory and the schema-identity gate

2026-11-05, America/Mexico_City. Entry commit `6898dfb87`, with the
uncommitted working tree. No controller was contacted, and no generator output
changed. The design these results feed is the
[collapse review](../AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md).

## Context data flow

`Investigation/context_dataflow_01.py` generated both S6-Q declarations in
memory: `fraktal_ab_genealogy_s4b_owner_demo` and
`fraktal_ab_press_canonical_echo38`. It followed every Unit, chart and module
context member through the emitted ST and ladder, AOIs included. Inside an AOI,
a context is the parameter of its type. The result is
`Investigation/context_dataflow_01.json`, with the writers, readers,
canonical targets and harness facts of each of the 320 members:

| Class | Genealogy | Press |
|---|---:|---:|
| private | 108 | 109 |
| input | 80 | 80 |
| output | 62 | 61 |
| shared | 30 | 30 |
| published | 24 | 24 |
| unused | 16 | 16 |

- **Same members.** Both declarations have the same 320 members. Only
  `PressRam.OutImm_Pos` is classed differently: output in the genealogy,
  private in the press.
- **Copies.** 94 members are copied exactly somewhere in the publication. 28
  of them fill a published canonical leaf, in 41 assignments.
- **Harness facts.** 125 members carry a harness fact from the
  [HX accounting](AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03.md).
- **Never written.** 19 members are read but written by no routine. They are
  declared constants.

**Method limits.** The classifier matches member references by text:
- an ST write is a reference followed by `:=`;
- a ladder write is the destination of an output or move instruction;
- a whole context passed to an AOI is followed through that AOI's parameter.

A whole-structure copy is not attributed to members. A scan of the emitted
`COP`, `CPS`, `MOV` and `FLL` calls finds eight, all reads: the S3h
observation frame `CPS`es the Unit, the chart and each of the six module
contexts into `FRK_Press_ObservationFrame`. Every member is therefore also
read by that frame. The frame exists for the harnesses, whose facts are
counted separately, and increment C4 removes it. No routine writes a whole
context.

## The gate

`fraktal_ab_schema_identity.py` records an image's external surface from the
generated L5X. That is every tag a client can reach, with its decoded initial
data, and every type those tags reach. Two surfaces are compared path by path.
Each difference must be declared, with the change it permits and the plan item
that makes it. A declaration that covers nothing also fails.

The baselines were recorded from the tree at `6898dfb87`, into
`tools/fixtures/schema_identity/`. Each has an empty `.declared.json`:

| Declaration | Published tags | Types | Tag fingerprint | Type fingerprint |
|---|---:|---:|---|---|
| `fraktal_ab_genealogy_s6_host_demo` | 94 | 155 | `1FD8D3DE…3BB7` | `B5BB8DC4…73BA` |
| `fraktal_ab_press_canonical_echo38` | 78 | 128 | `8C61386A…FD77` | `1EF08FB1…BC20` |

The genealogy fixture's `LegacyContentHash` is `0DBD9CEA8EE6BC59`. Its first
six hex digits are the configuration revision that set documents carry.

`test_fraktal_ab_schema_identity` checks:
- extraction and comparison over a synthetic image (9 cases);
- both declarations regenerating their recorded surface exactly.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`), all exits 0:
- **Sources:** 8 files bound: text files with their line endings, and the
  two gzip fixtures by hash, untracked at HEAD.
- **Gate tests:** `test_fraktal_ab_schema_identity` passes 10 tests in 105 s,
  with ResourceWarnings raised as errors, none skipped.
- **Full AB discovery:** 2,526 tests in 1,322 s, none skipped. All 406
  module hashes are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates are clean.

`Investigation/run_doc_gates_02.py` (`Gates/gate_summary_02.json`) ran after
O12's text was corrected in the review and the plan. It rebinds every source
and reruns the root, specification, frozen-contract and strict consistency
gates, all exits 0. Only those two Markdown files changed since run 01, so run
01's full suite stands.

## Boundary

This increment changes no generator output and no wire contract. Its
fixtures are the reference every later collapse increment is compared with.
The native discovered-path comparison remains S6-Q's.

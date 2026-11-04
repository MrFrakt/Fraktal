# S6 HX harness coupling accounting — offline

2026-11-03/04, America/Mexico_City. Entry commit `2c5f9b2c9` (main after the
`feature/generic-cm-phase0` merge), with the uncommitted S6 working tree. A
read-only analysis for WP6.2 under O10. No controller is contacted, and no
tool, generator or PLC source changes.

## Method

`Investigation/hx_fact_accounting_02.py` covers the 24 HX modules that census
[classification 03](../AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json) marks
`migrate-canonical-reads`. It generates the canonical copy layer of both S6-Q
declarations, `fraktal_ab_genealogy_s4b_owner_demo` and
`fraktal_ab_press_canonical_echo38`, each in its own process. Both are stage 13.
Their 320 context members split into 14 exact copies, 8 zero/nonzero
equivalents and 298 with no canonical copy. Per harness it records three
couplings:

- **context facts:** keys subscripted or fetched with `.get` that name a Unit,
  chart or module context member, plus weaker literal-only matches;
- **runtime reads:** APIs used from `fraktal_ab_projection`/`fraktal_ab_gateway`,
  through any alias or from-import;
- **legacy commands:** `px.command`/`px.manual`/`command_writes`, or the runtime
  `MailboxWriter`. All of these write the legacy Frame/Sequence ingress that
  WP6.6 removes (S3k wire draft).

Version 01 (`hx_fact_accounting_01.*`) recorded context facts only and is kept.
Two earlier 01 attempts failed with tool errors (a syntax error, then sorting
dicts) before writing any output.

## Results

| Coupling | Harnesses |
|---|---:|
| Private context facts; none uses exact copies only | 15 |
| Python projection reads | 16 |
| Legacy-ingress commands (plus `press_canonical_execute`, inherited) | 15 (+1) |
| ...of which through the runtime `MailboxWriter` | 4 |
| No coupling of their own (inherit through helpers, or already migrated) | 6 |

Module-member names are attributed to every surface that declares them, so
the per-declaration union (125 non-exact entries each) overstates module rows.
Per-module precision needs data flow when WP6.6 defines the O10 structure.
`s9_read_execute` and `s9_mutations` measure or mutation-test the Python
gateway and projection themselves. Their subject retires with RT, so they
have no station read to move. Commands through an inherited `self.command` are
not attributed statically; `press_canonical_execute` is the known case.

## Consequence

No context-reading harness can migrate onto canonical reads alone. All 15 join
O10 in WP6.6. Independently, 16 harnesses command through the Frame ingress,
including the S6-Q genealogy cases (`part_execute`) and press rows. The only
typed-ingress writer is the Dart client's (WP5.1). No Python command path for
the harnesses after WP6.6 is assigned in the plan. The
[reader review](../AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md)
records the question for the owner.

## Gates and boundary

The analysis only reads sources and generates ST in memory. No gate is
affected. Native, collapse, retirement and S6 exit claims are unchanged. Payload
hashes are in `artifact_manifest.json`, whose own hash is given in the review.

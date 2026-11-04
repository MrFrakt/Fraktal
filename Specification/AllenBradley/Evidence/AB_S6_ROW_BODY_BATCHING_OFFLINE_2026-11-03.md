# S6 row-body batching and press fact accounting — offline

2026-11-03, America/Mexico_City. Entry commit `8cd2060f1`, with the uncommitted
S6 working tree recorded on 2026-11-02. This is a third WP6.2 checkpoint. It is
not S6 exit, a live harness acceptance or a native measurement. No controller
read, write, download, mode, fault-clear, clock or power operation runs here.

## Row-body batching

`fraktal_ab_canonical_live.py` replaces its per-leaf read callable with a body
that plans, sends and parses. `PacketBody` serves the wire and `LeafBody` the
offline replay. A row's leaves and deduplicated occupancy counts are planned
once, before the first counter read. Packets are sent between the separately
completed counter reads. Replies are validated after the proof closes, on every
attempt. A malformed reply from a torn attempt therefore refuses rather than
retrying. The deadline is checked between packets. Planning precedes the source
timestamp's I/O and counts toward age and the one-second deadline. It never
counts toward a proof window.

The bounds are the Dart `cip://` ones: 64 embedded Read Tag services, at most
4,000 connection bytes, and at least 500. Both directions include the
connected sequence count. A lone leaf keeps the plain request. A leaf that
cannot fit alone refuses at planning. Proof, attempt, window and freshness
limits are unchanged. A packet is not treated as atomic.

A pylogix-encoding fake controller answers plain and MSP requests from the
sealed S5 bytes, accepts only read services and enforces the connection size
both ways. Every owner's complete occupied row replays exactly at 4,002 and 500
bytes. MSP status/count/offset/embedded-status/type/handle/extent defects
refuse. The mutation check is archived as `mutate_batching_01.py`. Earlier
scratch runs were not logged to files; their outcomes are recorded here. The
first was invalid apparatus: the cwd shadowed the mutants and a stripped
environment hid pylogix. After correction, one mutant (65-read cap) survived,
because the test compared against the module's own constant. The test now pins
Dart's literal 64. The gated run then catches all four mutants.
Two first-draft test mistakes are also recorded: a guessed nonexistent path
(`Status/Diagnostic/Severity`) and a duplicate check keyed on the fake's
physical symbols, which merges seven packed-BOOL leaves. Neither is a reader
defect.

## Press fact accounting

`press_fact_accounting_01.py` checks that it accounts for every declared
layout member subscripted by `fraktal_ab_press_execute.py`. It then classifies
each fact against the copy layer generated for
`fraktal_ab_press_canonical_echo38` (stage 13). Of 33 facts, 4 are exact
canonical copies and 2 are zero/nonzero equivalents (`FaultActive`). The other
27 have no canonical copy. Eleven of 15 rows mix the two classes in one atomic
legacy read. The [reader review](../AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md)
states the resulting owner decision. No press harness code changes.

## Gates

`Investigation/run_gates_01.py` ran every gate sequentially into create-only
`Gates/` records; `gate_summary_01.json` binds the exits:

- 35 focused tests pass with ResourceWarnings as errors; 27 before, 8 new.
- Mutation check: four of four mutants caught; the original passes.
- Full AB discovery: **2,405 tests pass** (896 s). All 385 Python module hashes
  are unchanged during the run.
- 74 root tests, the AB specification and frozen-contract gates, and strict
  consistency (0 errors, 0 warnings) pass.
- The S9 canonical Dart replay passes all 124 cases. Its decoder does not
  import the changed module; it is rerun for completeness.
- The accepted S5 source regenerates byte-identically
  (`979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162`). Both
  v38 targets pass fresh builds, readbacks and SDK-log audits. No genealogy ACD
  is opened.

The run overlapped the documentation edits. The specification, contract,
consistency and root gates are therefore rerun on the final text as `_02`.
The HMI is unchanged and is not rerun; its prior result remains 802 passed/12
skipped.

## Boundary

Echo was not contacted. Native batching latency, row timing and workload
equivalence remain unmeasured. Other HX migrations, WP6.3 replay, host services,
collapse, retirement, S6-Q and V2 activation remain. S6 has not exited; nothing
is committed under O1. Physical S7 remains deferred.

Payload manifest SHA-256: D7B411DE30C00F5D63867A3063A74920BCF85D9FB134BBC433A9C71E2A96B107
(51 entries, including the four changed source/document files). The three
generated/readback L5X files are not archived. They were moved to
`C:/work/fraktal-ab-s6-20261103/Build/`, with hashes in
`Gates/excluded_build_outputs_01.json`. No credentials, ACD, binaries or caches
are archived. Earlier evidence is unchanged.

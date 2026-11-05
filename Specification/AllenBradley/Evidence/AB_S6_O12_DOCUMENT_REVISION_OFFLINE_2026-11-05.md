# S6 WP6.6 C0b — The configuration document revision (O12)

2026-11-05, America/Mexico_City. Entry commit `a3e80ef54`, with the
uncommitted working tree. No controller was contacted. This implements owner
decision O12 (option A, approved 2026-11-05) as the increment before C1; see
the [collapse review](../AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) §5.

## Why it comes first

The configuration revision every set and live document carries was the first
six hex digits of the V5 manifest content hash, and that content lists every
context member. Removing one, as C1 does, would have moved every
declaration's revision and refused every saved document.

## What changed

- **`fraktal_ab_document_revision.py`** owns the revision.
  - `identity(app)` hashes the root, the set schema and, for each editable
    value, its configuration kind, its record's schema version, write key,
    value kind and dimension.
  - Ranges, write levels, ordinals and order stay out: the controller checks
    the first two at load and resolves keys itself.
  - `revision(app)` is the identity's first six hex digits.
- **Every document producer and the guard use it:**
  - set documents (`fraktal_ab_sets.values_document`) and live documents
    (`fraktal_ab_live`);
  - the V6.11 host staging and export snapshots (`fraktal_ab_host_sets`);
  - the revision guard (`accepted_revisions`);
  - the canonical `LegacyContentHash`, so `configRev = LegacyContentHash[:6]`
    holds for the Dart adapter unchanged;
  - the Python host-event source key.
- **Unchanged:** the V5 header's `ConfigRevision` and the V5-build capability
  tokens of the legacy Frame and staged paths. Part III ties the former to the
  V5 content, and C5 and C6 remove both.
- **Predecessors.** `decl.ConfigPredecessors(identity, revisions)` is the
  declaration field `config_predecessors`, excluded from declaration equality.
  - Each in-tree declaration names its own entry in
    `fraktal_ab_pre_collapse_revisions.json`. That is the record written at
    `a3e80ef54`, moved out of `fixtures/` because production reads it, and
    refused if its SHA-256 changes.
  - A build honours its predecessors only while its identity is the one they
    were saved under. `decl.validate` refuses a declaration that still claims
    them after its values change meaning.
  - The station template claims its own only in its default form; a line
    changes its values.
- **The host bench** (`fraktal_ab_host_bench_server.py`) stamps a
  predecessor document with `saved_revision(<declaration>)`: the revision a
  document saved by that declaration's pre-collapse build carries.
- **The recorder** (`fraktal_ab_config_revisions.py`) and its test are
  removed. After C0b they would record the new revision, not the
  pre-collapse one. A station outside the tree runs them at `a3e80ef54`.

## Rejected on the way

The first form unioned the recorded revisions of every in-tree declaration
with the same identity. All 26 press-family declarations share one identity,
so every press image, the L24ER press's included, would have carried a
197-term guard instead of 5 terms. It would also have accepted documents only
another demo ever saved. That form was never committed.

## Results

**Source 07** (`Gates/Prepare/`, prepared in `C:/work/fraktal-ab-s6-host-20261104/prepare`):
- **Images:** genealogy V6.11 `B9A37972…EAC0` and press canonical
  `91236742…0F54`. The BOOL-operand gate is clean for both.
- **Builds:** the genealogy builds, reads back equivalent and passes the SDK log
  audit on both v38 targets, and so does the press on Echo. The genealogy's
  nested access audit passes on both targets.
- **One misapplied audit:** `access_press_EchoController_07` exited 1.
  `audit_access_03` is written for the V6.11 genealogy and expects its
  host-service ingress, which the press image does not have; it is the wrong
  audit for that image, not a finding. C0b changes no access: the
  schema-identity gate below shows every published tag's and member's access
  unchanged for both declarations.
- **ACD and Capacity:** `prepare_candidate_07b` ran the steps the first script
  skipped on the same source bytes. ACD `A46A1C7D…802E`, read-back
  equivalent. Capacity is 2,235,048 of 3,145,728 blocks
  (71%), a verified fit: 120 blocks over source 06, the guard's third group.
- **Guards:** genealogy 122 → 123 accepted revisions (three nested groups,
  longest line 2,272 characters, within the 2,284 v38 has built); press
  canonical 6 → 7; press demo 5 → 6.
- **Still the committed image:** after the bench fix below, the genealogy
  source regenerates byte-identically to `B9A37972…EAC0`. The fix touches a
  test server and an unemitted lookup, never the generator's output.

**Run 01 failed** (`Gates/gate_summary_01.json`, kept as recorded). One Dart
gateway test failed. `documents saved by the build without host services are
restored` expected the predecessor document's revision to differ from the
build's. The host bench rendered that document through the new revision,
which by design no longer moves without host services. The bench now stamps
it with the V6.10 declaration's recorded pre-collapse revision
(`saved_revision`), which is what such a document actually carries, and the
test passes unchanged. Every other gate in run 01 passed.

`Investigation/run_gates_02.py` (`Gates/gate_summary_02.json`), all exits 0:
- **Sources:** 47 files bound with their line endings, 2 deletions recorded.
- **Dart:** `dart analyze` is clean for the gateway, and its 44 tests pass, none skipped.
- **Focused Python:** 281 tests with ResourceWarnings raised as errors, none skipped. This
  includes the schema-identity gate: both recorded surfaces are unchanged with
  nothing declared, and only the derived hashes move (`LegacyContentHash`
  `6F3F8CDA9A8F6B59` for both).
- **Full AB discovery:** 2,534 tests in 1,137 s, none skipped. All 409 tool
  sources are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates are clean.

## Boundary

The new guards compile: the genealogy's on both v38 targets and the press
canonical image's on Echo. The L24ER v33 press (`fraktal_ab_press_demo`) is
not built here, because this host has only Logix Designer v37 and v38. Its
guard grows from 5 terms to 6, which `_conjunction` emits as two
parenthesized groups of at most five. That is within v33's five-chained-term
limit, but no v33 compiler has seen it.

Native acceptance, including a restore of documents saved before C0b, is
S6-Q's.

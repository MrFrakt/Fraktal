# S6 WP6.4 — V6.11 list, current export and import, offline

2026-11-04, America/Mexico_City. Entry commit `2c5f9b2c9`, with the
uncommitted S6 working tree. This follows the
[set-service record](AB_S6_HOST_SET_SERVICE_OFFLINE_2026-11-04.md), which stays
unchanged. All eight configuration-set operations now travel over V6.11, as
the [wire draft](../AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md)
records under "List", "Current export" and "Import". It makes no native
claim. No controller or Echo session was used, and no image was written to a
file or downloaded. Nothing was committed.

## What changed

- `fraktal_ab_host_sets.py` serves all eight set kinds:
  - **List:** a PRESENT job on ConfigProvider. The catalog is buffered entry
    by entry and published whole, with the accepted answer, in one scan.
  - **Current export:** the transaction runs and audits when the command
    arrives. Only an accepted one parks. Its PRESENT job publishes the
    snapshot, and the host's rendered header line is published with the
    answer.
  - **Import:** each piece parks a FETCH job carrying it in `JobText`. The
    host's parse names the set, and on commit counts its records. An
    accepted commit opens the STORE job.
- The interim refusal key `config_set_operation_unavailable` and its mailbox
  hook are deleted. `CommandOperations` publishes every set kind supported,
  with nothing to stage.
- `test_fraktal_ab_host_sets.py` grows from 28 to 37 tests. The new ones cover:
  - the whole-catalog publication, never a part;
  - an empty store;
  - four malformed catalogs, each abandoned with the published catalog kept;
  - an unreadable store, refused and audited;
  - the current export's rendering, its two failures, and a refused export
    that never asks the host;
  - pieces under the broker's `(import)` placeholder, the commit's STORE job
    with its piece wiped, and an unparseable piece refused and audited by name.

`Gates/source_bindings_02.json` binds the 12 sources, the wire draft, the plan
and the review, and checks each keeps its HEAD line endings.

## Gate results

**Run 01 failed** (`Investigation/run_gates_01.py`, `Gates/gate_summary_01.json`).
Every gate passed except the mutation gate. Of 27 mutants, 26 were killed. One survived:
the current export's line-count check (`Total` against the snapshot's
count). Its test sent a count of 99, and the generic ingress refuses any count
over 64 before the service sees the chunk. So the controller's own check was
never reached. The defect was in the test, not the routine. Run 01's outputs
stay as recorded.

The test now sends the real record count plus one, inside the ingress's
bounds. A single-mutant check confirmed that the mutant then fails one test.
Then the full sequence ran again.

**Run 02** (`Investigation/run_gates_02.py`, `Gates/gate_summary_02.json`,
all exits 0):

- **Focused:** 66 tests, with ResourceWarnings raised as errors: the 37 set-service tests
  and the 29 earlier host-service tests.
- **Mutations:** `mutate_host_sets_02.py` mutates one emitted line at a time,
  as before. The unmutated text passes all 37 tests, and each of 27 mutants
  fails at least one. Those are the 19 earlier mutants, re-anchored where the
  emitted lines changed, and 8 new ones:
  - the catalog publication, the repeated-name check and the record-kind
    bound;
  - the current export's park and its line-count check;
  - the import piece transport and the import commit's STORE job;
  - the unreadable store's audited refusal.
- **Full AB discovery:** 2,478 + 9 = 2,487 tests pass (934 s), with all 394
  Python module hashes unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

## Boundary

The bench executes emitted ST against emitted initial data in the model; the
native claims of the earlier records stay open. Still open:
- the LiveDocuments keep and restore jobs, without which the opt-in refuses
  live documents;
- the host adapter (WP6.5);
- WP6.6's removal of the legacy staged and provider endpoints, both v38
  builds, exact-image Capacity and scan, and S6-Q.

S6 has not exited, and nothing is committed under O1.

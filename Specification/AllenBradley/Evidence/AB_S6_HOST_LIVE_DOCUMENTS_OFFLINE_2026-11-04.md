# S6 WP6.4 — V6.11 LiveDocuments keep and restore, offline

2026-11-04, America/Mexico_City. Entry commit `2c5f9b2c9`, with the
uncommitted S6 working tree. This follows the
[set-operations record](AB_S6_HOST_SET_OPERATIONS_OFFLINE_2026-11-04.md), which
stays unchanged. The LiveDocuments jobs are now implemented, as the
[wire draft](../AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md)
records under "LiveDocuments", so the V6.11 opt-in accepts the press as
declared, live documents included. Every host service's PLC side is now in
place offline. It makes no native claim. No controller or Echo session was
used, and no image was written to a file or downloaded. Nothing was
committed.

## What changed

- `fraktal_ab_host_sets.py`:
  - host-opened jobs on service 3;
  - **keep**: a snapshot of the station, the line or model *n*, closed by the
    host's receipt, and preempted by an operator's set command;
  - **restore**: one document, opened only while restoring and under the set
    gate, which resumes as a **silent owner pass**;
  - `Restoring` and `SessionPermits` published in the reply.

  The fetch's chunk handling is factored out to serve both fetch and restore.
  The emitted service, entry and presentation routines and the typed-ingress
  routine are byte-identical for stations without live documents.
- `fraktal_ab_mailbox.py` keeps a silent pass's verdict before the previous
  answer is put back. `fraktal_ab_canonical_config.py` publishes a keep
  failure as `ConfigPersist.Failed`. `fraktal_ab_host_services.py` lifts the
  opt-in's refusal of live documents. All three changes are under the opt-in.
- `test_fraktal_ab_host_sets.py`: its station takes a bench context, so the
  live suite shares it. Its declaration test now checks the live variant's
  LiveDocuments row under the set gate.
- `test_fraktal_ab_host_live.py` (11 tests) runs the press as declared, from a
  downloaded, restoring image. It covers:
  - **Restore:** a model bank then the station, through silent passes that
    move no operator sequence, acknowledgement or answer, audited under 0.
    Also a lost document raised with the station answer, a refused document
    returning its verdict while the restore continues, and a model the
    catalog lost, created under its code.
  - **Refusals:** a restore is refused outside a restore and without the
    gate, and a parked operator command holds one off. A host that stops
    mid-document runs no transaction at all.
  - **Keep:** one document's values with the receipt settling or failing the
    keep, and a model bank's values. No keep while restoring or for a
    document the station lacks, and an operator's set command preempts a keep.

`Gates/source_bindings_01.json` binds the 14 sources, the wire draft, the plan
and the review, and checks each keeps its HEAD line endings.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`, all exits 0):

- **Focused:** 77 tests, with ResourceWarnings raised as errors: the 11 live,
  37 set-service and 29 earlier host-service tests.
- **Set mutations:** `mutate_host_sets_03.py`, a copy of the previous
  checkpoint's harness, runs on the refactored suite. The unmutated text
  passes 37 tests, and all 27 mutants are killed. Every anchor still resolves
  unchanged, which shows the emitted set-service text did not move.
- **Live mutations:** `mutate_host_live_01.py` generates the live press's
  sections and mutates one emitted line at a time. The unmutated text passes
  all 11 tests, and each of 13 mutants fails at least one:
  - the silent pass: the verdict capture, the operator sequence's return, the
    put-back of the previous answer, and the verdict's publication;
  - the restore gates: not restoring, the set gate, the published session
    permit, and the lost-document staging;
  - a late or failed job running a pass;
  - the keep: refused while restoring, its failure flag, its value source and
    its preemption.
- **Full AB discovery:** 2,487 + 11 = 2,498 tests pass (1,194 s), with all 395
  Python module hashes unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

During development, one heredoc edit failed to parse in the shell before
writing anything, and one script rename missed its anchor before writing a
gate runner. Both were redone as files; neither touched a gated source.

## Boundary

The bench executes emitted ST against emitted initial data in the model. It
does not run `ScanCanonical`. The keep failure's publication there is
checked as emitted text, not executed. Still open:
- the host adapter (WP6.5): restore order and verdicts, write-on-change keep,
  the import-graph test and the tray lifecycle;
- WP6.6's removal of the legacy staged and provider endpoints, both v38
  builds, exact-image Capacity and scan, and S6-Q;
- the native claims of the earlier records.

S6 has not exited, and nothing is committed under O1.

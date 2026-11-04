# S6 WP6.5 — Declaration-free host adapter, offline

2026-11-04, America/Mexico_City. Entry commit `2c5f9b2c9`, with the
uncommitted S6 working tree. This follows the
[LiveDocuments record](AB_S6_HOST_LIVE_DOCUMENTS_OFFLINE_2026-11-04.md), which
stays unchanged. It implements the PLC-facing half of WP6.5 (plan §5.3): the
adapter that answers the V6.11 jobs, recorded in the
[wire draft](../AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md).
It makes no native claim. No controller or Echo session was used, and no
image was written to a file or downloaded. Nothing was committed when the
gates ran.

## What was built

| Source | Role |
|---|---|
| `fraktal_ab_host_adapter.py` | `RootService`: answers every ConfigSets and ConfigProvider job, and keeps and restores live documents in `live.restore`'s order and verdicts. Renders documents from published facts. CLI `main()` |
| `fraktal_ab_host_cip.py` | The pylogix port: discovery through S1, reply decode, request plus commit, a bounded acknowledgement, no resend, facts from the published tables |
| `fraktal_ab_set_documents.py` | The set-document format, `FileStore`, `Session` and the store folder, moved verbatim from `fraktal_ab_sets` |
| `fraktal_ab_live_medium.py` | `FileMedium` and its failure kinds, moved verbatim from `fraktal_ab_live` |
| `fraktal_ab_host_cursor.py` | The host-event cursor and ring metadata rules, moved verbatim from `fraktal_ab_host_events` |
| `fraktal_ab_canonical_reader.py` | The S1 read takes the V6.11 commit symbols and the request structure handles |
| `fraktal_ab_host_service_binding.py` | `complete`: a sparse chunk with every unnamed field empty, never widened |

The engineering modules re-export everything that moved, so no caller
changed. The adapter's facts all come from what the controller publishes:
- the typed command binding's `WriteCapabilities` rows and `Localization`
  keys give each ordinal's write key, kind and type;
- `<root>/AvailableModels` and `ModelCapacity` give the catalog;
- the legacy content hash gives the documents' configuration revision.

The port encodes each chunk against the Templates S1 validated at discovery,
because re-validating the whole capture per chunk would cost a full schema
walk inside a 1.5 s job window.

`Gates/source_bindings_01.json` binds the 13 sources, the wire draft, the plan
and the review, and checks each keeps its HEAD line endings.

## Tests

`test_fraktal_ab_host_adapter.py` (10 tests) runs `RootService` against the
emitted controller routines on the bench, through a port that reads the
published reply and writes the request and commit as a client does. Its
store and medium are real temporary folders. It covers:
- **Sets:**
  - save, list, load, export and delete, through the adapter's store;
  - the saved document equals the engineering `values_document` rendering;
  - a current export rendered, then served line by line;
  - an import in pieces, stored on commit;
  - a value the controller cannot parse sent as an invalid type, never
    coerced;
  - a missing set refused, and audited, by the transaction;
  - a full store refused.
- **Live:**
  - a download restored from the medium, then every document kept, equal to
    the engineering keeper's rendering of the same values;
  - a lost document restored as a loss;
  - an unreadable medium restoring nothing.
- **Process:**
  - a fresh interpreter imports the adapter and its port without the
    declaration, generator, station, projection, manifest, sets, live or
    mailbox modules;
  - the adapter's Core kinds and denied key equal the mailbox's.

`test_fraktal_ab_host_cip.py` (5 tests) covers the port against a fake
controller on the binding tests' synthetic Templates:
- the reply decodes to plain values;
- a request is the payload then the commit, and returns its acknowledgement;
- an unacknowledged or refused request is never resent;
- a sparse chunk is completed, never widened.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`, all exits 0):

- **Focused:** 226 tests, with ResourceWarnings raised as errors, covering:
  - the adapter (10) and its port (5);
  - the live (11), set-service (37) and earlier host-service suites;
  - the moved modules' own suites (sets, live, host events) and the S1
    reader's.
- **Mutations:** `mutate_host_adapter_01.py` changes one line of the
  adapter's source in memory at a time. The unmutated source passes all 10
  tests, and each of 8 mutants fails at least one:
  - a missing set answered as found;
  - a full store not refused;
  - an import commit not kept;
  - a restore that hides its losses;
  - a boolean rendered as a number;
  - invalid value text coerced;
  - the catalog never published;
  - a keep that never writes.
- **Full AB discovery:** 2,513 tests pass (1,069 s), with all 402 Python
  module hashes unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

A development mutation run, before these gates, left two mutants alive. Both
were test weaknesses:
- a missing set's refusal had not been told apart from a host failure;
- the coerced value happened to be out of range for the field chosen.

The tests now require the transaction's audited refusal and choose a field
whose range admits the coerced value. Earlier development failures were in
the tests or the move scripts:
- two live tests asserted a state the keep loop had since replaced;
- one move swept a declaration-bound function along and was redone;
- two shell heredocs mangled backslashes before writing anything.

## Boundary

The adapter is proven against the emitted controller code in the model, and
its port against synthetic Templates. Native Templates, timing and the
live pylogix exchange are S6-Q gates. Still open in WP6.5:
- **HostEvents delivery over the canonical ring.** The cursor's rules moved
  unchanged. Converting the ring's rows to the same batch needs equivalence
  proof on a native capture, and the bench does not run the routine that
  publishes the ring.
- **The tray's supervision of `host_adapter.args`.** The tray starts packaged
  executables only. How the Python adapter is distributed (bundled
  interpreter, frozen executable, or a port to Dart) is an owner decision.

Then WP6.6 removes the legacy staged and provider endpoints and the Python
gateway path that still uses them.

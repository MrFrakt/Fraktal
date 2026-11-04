# S6 WP6.4 — V6.11 configuration-set service, offline

2026-11-04, America/Mexico_City. Entry commit `2c5f9b2c9`, with the
uncommitted S6 working tree. This is offline engineering evidence for the
[V6.11 wire draft](../AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md)
("Parking an operator command"), under O4. It follows the
[layout record](AB_S6_HOST_SERVICE_LAYOUT_OFFLINE_2026-11-04.md) and its
[LF restoration](AB_S6_SOURCE_LF_NORMALIZATION_2026-11-04.md), and leaves both
unchanged. It makes no native claim. No controller or Echo session was used,
and no image was written to a file or downloaded. The generated sections the
tests run exist only in memory. Nothing was committed.

## What was built

| Source | Role |
|---|---|
| `fraktal_ab_declaration.py` | The `canonical_host_services` opt-in, default off |
| `fraktal_ab_host_services.py` | Opt-in validation, V6.11 schema/tag emission, the scan hooks around the typed ingress, the ring revision symbol |
| `fraktal_ab_host_sets.py` | The ConfigSets service: park, FETCH staging, resume, rejection text, export line, STORE receipt |
| `fraktal_ab_canonical_publication.py` | V6.11 header type, minor, table, content hash and tags under the opt-in |
| `fraktal_ab_owner_read_bindings.py` | The ring's whole-scope owner row on its own revision |
| `fraktal_ab_canonical_traceability.py` | The ring publication brackets every changing scan with that revision |
| `fraktal_ab_canonical_commands.py`, `fraktal_ab_mailbox.py`, `fraktal_ab_sets.py`, `fraktal_ab_generate.py` | Hooks, all under the opt-in. A parked command writes no answer; the refusal codes and keys; the set dispatch, staging source and receipt source |
| `fraktal_ab_st_bench.py` | The emitted data types, tag initializers and ST routines, run in the executed-ST model |
| `test_fraktal_ab_host_sets.py` | 28 tests over the emitted routines |

`Gates/source_bindings_01.json` binds these 12 sources, the wire draft and
the plan, and records that each keeps its HEAD line endings. All are LF
except the generator, which is CRLF at HEAD and stays CRLF. For that reason
`git diff --check` reports its one added line as trailing whitespace.

## How the tests run the emitted code

The bench builds every controller tag from the generated data types and the
Decorated initializers a download would carry, and parses each ST routine
from the generated programs when a JSR first reaches it. A test scans the
following routines in main-routine order, from a first scan with `S:FS`
set:
- `ScanCanonicalBegin`, `ScanAccessStartup`, `ScanHostClock`;
- the typed-ingress routine `HmiFrame` and the mailbox `HmiMailbox`;
- `ScanConfigRestore`.

It then runs the canonical response cyclic block, sliced from the emitted
`ScanCanonical` text by its first line at its generated length. The rest of
`ScanCanonical` is not run: its LINT arithmetic is outside the 32-bit model.
Module AOI bodies are not run either.

The tests cover:
- **Load:** the command parks with no answer. The host's header and records
  are applied through the unchanged transaction and audited, then the typed
  reply acknowledges. The job name is wiped at close.
- **Parking:** the previous answer, owner acknowledgement and response
  revision stay published while a command is parked.
- **Other commands:** a second set command is refused busy. A mode change is
  served during the park and cannot change the parked arguments. A resume
  yields to a command that arrives in the same scan.
- **Refusals:**
  - a silent host is refused as unavailable within `PARK_MS`, and nothing is
    applied;
  - a resume that could only run after `PARK_MS` is refused;
  - a first scan refuses a parked command.
- **Host answers:**
  - an unknown key, a range violation, a foreign record scope and a foreign
    header root each refuse, with the rejection text the broker gave;
  - non-OK statuses refuse and are audited;
  - four malformed streams are abandoned, never half-applied;
  - a host cannot open or answer a job that is not its own;
  - a stored set must answer the name asked for, including a same-prefix
    name.
- **Operations:**
  - an export publishes its line only for a valid document;
  - a save stores the transaction's snapshot, and its receipt settles or
    fails ConfigPersist;
  - a full store refuses;
  - a creation copies a model set and refuses a station set;
  - list, current export and import are refused by name and published
    unsupported.
- **Declaration:** V6.11 with three host rows and the ring on its own owner
  revision; live documents refuse the opt-in; without the opt-in nothing
  changes.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`, all exits 0):

- **Focused:** 57 tests, with ResourceWarnings raised as errors: the 28 new
  ones and the 29 earlier host-service tests.
- **Mutations:** `mutate_host_sets_01.py` generates the V6.11 sections once,
  then mutates one emitted line at a time in the program text. The unmutated
  text passes all 28 tests. Each of 19 mutants fails at least one:
  - no answer while parked: answer restore, handler and owner
    acknowledgement, typed-reply publication;
  - busy refusal, resume yielding, and the late-resume bound;
  - foreign scope, stored-name length, header root, and completeness at
    `Final`;
  - the abandoned-job reaction and the host-refusal invalidation;
  - the receipt result and the snapshot copy;
  - the rejection key lookup and the non-ASCII name;
  - the staging source and the export-line guard.
- **Full AB discovery:** 2,478 tests pass (1,203 s), with all 394 Python
  module hashes unchanged during the run. The pins and every existing
  generated image regenerate as before, so the opt-in changes nothing for
  declarations that leave it off.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

## Failures during development (not gate runs)

Each failure in the unrecorded development runs was in the bench or a test:
- The bench first lacked predefined types (`FBD_TIMER`, `LDT`, SFC
  structures) and a GSV model.
- The model stores an integer written into a BOOL, so the bench now keeps
  BOOL storage boolean, as a controller does.
- One test wrote an integer into a BOOL payload member, which a whole-record
  CPS correctly refuses.
- Two tests needed the configuration-restore routine in the scan, because it
  fills the model catalog.
- One test expected starvation without a command in the resume scan; the
  resume correctly runs at once.

The first development mutation run left the typed-reply publication mutant
alive. The test had executed that block from the generator's Python lines,
not the emitted text. It now slices the block from the emitted routine; the
recorded run kills that mutant with three failures.

## Boundary

The bench executes emitted ST against emitted initial data in the model. It
does not establish native behavior:
- the 2 s budget, the one-packet reply and the CPS reply atomicity;
- the native request size, and the scan cost of parking.

Still open:
- list, current export and import over V6.11, and the LiveDocuments keep and
  restore jobs, without which the opt-in refuses live documents;
- the host adapter (WP6.5);
- WP6.6's removal of the legacy staged and provider endpoints, both v38
  builds, exact-image Capacity and scan, and S6-Q.

S6 has not exited, and nothing is committed under O1.

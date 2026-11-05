# S6 WP6.5 — The host adapter's HostEvents delivery, proven on the native capture

2026-11-05, America/Mexico_City. Entry commit `156edea9b` (branch
`s6/host-services`), with the uncommitted working tree. No controller was
contacted. This closes the last WP6.5 item, HostEvents delivery, offline,
against the capture that the
[session 03 runtime](AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04.md) sealed on
Echo. Nothing was committed when the gates ran.

## What was built

| Source | Role |
|---|---|
| `fraktal_opcua_client` `CipHostEventsReader` | One root's canonical ring, from its HostEvents service row and its own owner-read row. It reads the `HostEvents` member alone (10,672 of the root's 147,784 bytes), between two reads of the ring's owner revision: an odd or moved revision returns nothing, to be read again. It projects with the gateway's own `CipPublication.projectSubtree`. `cipHostDiscover` now returns a `CipHostDiscovery` with the ingresses and the event rings |
| `host_events.dart` `batchFromCanonical` | The inverse of `fraktal_ab_host_events.project`: the metadata, then each active slot `((Head − Count + i) mod Capacity) + 1`, with Parents and the genealogy capacity |
| `host_events.dart` `HostEventsCursor`, `jsonlSink` | `fraktal_ab_host_cursor.Cursor` and the collector's JSONL sink, byte for byte (detail below) |
| `host_events.dart` `HostEventsService` | Per root: reads only when the ring revision moved since the last delivery, delivers, reports health. The executable runs one per ring, writing `events\host_events.jsonl` and `events\cursor.json` in the root's store folder |
| `python_json.dart` | Python's `ensure_ascii` string form and `json.dumps(sort_keys=True)`, plus the strict JSON reader, each written once and used by the set documents and the delivery alike |
| `fraktal_ab_host_bench_server.py` | A `cursor` variant needing no station, whose `deliver` op runs the engineering cursor and sink unchanged |
| `DEPLOYMENT.md`, `host_adapter.args.example` | Where events and their cursor are written; the restore runs under the logged-in operator's authority |

The batch validation is declaration-free: what can be checked without the
station's declaration, and refusal for anything wrong.
- **Metadata:** `validate_metadata` exactly, and the ring head equal to its
  metadata.
- **Each event:**
  - the sequence interval;
  - the kind range;
  - the verdict and reason rules per kind;
  - the station;
  - part identity only on part events, and subject only on resource events;
  - a parseable UTC stamp;
  - parents exactly their count, and only on part events.

No malformed row is dropped to manufacture continuity.

The cursor port keeps the engineering rules byte for byte:
- the cursor file is written whole and renamed into place;
- a lock on the never-unlinked guard file, and refusal beside a legacy
  `.lock` sentinel;
- loss records for an epoch change and an overwritten interval, and refusal
  of a regression within an epoch;
- the same idempotency keys, from the source
  `<serial>:<legacy content hash>`. The canonical manifest carries the same
  hash the Python collector derives from the declaration (`0DBD9CEA8EE6BC59`),
  so an existing cursor stays valid across the change of collector.

## A gateway defect found

Projecting the native V6.11 capture showed that `CipPublication` refused
every V6.11 image: `Owner scopes do not cover module headers/views`. V6.11
adds a whole-scope owner row for the HostEvents ring. The Python reader and
the Dart `CipManifest` admit that row, but the gateway's projection did not,
and no Dart test had projected a V6.11 namespace. The gateway itself would
have refused a V6.11 controller.

The projection now applies the Python reader's rule:
- every ring a HostEvents row names is published;
- the owner prefixes equal exactly modules ∪ views ∪ rings, now checked as a
  set where it was only counted;
- a whole-scope owner row is a declared view or such a ring.

## Tests

- **`gateway/test/host_events_test.dart`** (18 tests), on the sealed capture:
  - **Fixtures:** the two fixtures are the sealed files, by the session's
    manifest hashes.
  - **The proof:** the Dart reader's batch from the capture's ring bytes
    equals both legacy batches the session read natively around it (16
    events, wrapped, newest sequence 144).
  - **Projection:** the ring subtree projects as the whole root record does
    (220 leaves).
  - **Reads:** a read is kept only between two equal even revisions; odd or
    moved returns nothing.
  - **Refusals:** ten, one per validation rule above.
  - **Delivery parity:** the Dart cursor and sink write the engineering
    cursor's and sink's files byte for byte. The cases are first delivery
    (the overwritten interval, then 16 events), a repeated batch, a newer
    batch, an epoch change, a regression and a refusing sink.
- **`HMI/test/cip_v611_capture_test.dart`** (3 tests):
  - the projection accepts the V6.11 capture with its ring;
  - a ring owner row that no HostEvents row names refuses;
  - the gateway's read plan reproduces the whole projection of the V6.11
    capture, ring included.

## Mutations

`Investigation/mutate_host_events_01.py` (`Gates/mutations_01.json`). The
selected tests pass unmutated, and each of 8 one-line mutants is killed by a
failing test:
- the ring slot off by one;
- sequence continuity unchecked;
- a parent beyond its count accepted;
- an event acknowledged without its cursor commit;
- sink lines not ended as Python's text mode ends them;
- an epoch loss record misnamed;
- a torn read kept;
- the ring's owner row not admitted.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`): every gate
exits as expected. The usage request exits 64 by design; every other gate
exits 0.
- **Sources:** 12 files bound with their line endings, and the two fixtures
  equal to their sealed hashes.
- **Dart:**
  - `dart analyze` is clean for the client package and the gateway;
  - the gateway's 43 tests pass (the 18 new and 25 others) in 292 s, none
    skipped;
  - `fraktal_host_adapter.exe` compiles and prints its usage.
- **The tray** configures and builds, with only the three MSBuild notices
  about the temporary build folder.
- **Flutter:** `flutter analyze` is clean, and the full HMI suite passes 845
  tests with 12 skipped, the 3 new among them.
- **Python:**
  - the focused host-service suites pass 212 tests with ResourceWarnings
    raised as errors;
  - full AB discovery passes 2,515 tests in 1,166 s, with all 404 module
    hashes unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

## Boundary

The reader's native read of the ring has not run on a controller. It is the
same `readStruct` of one member and `readDint` of one revision the adapter
already uses natively, against the Templates this capture recorded. Its
native run joins S6-Q. Two adapter findings from the second session also
remain:
- `SessionPermits` covers only the set gate;
- a denied restore retries every 10 s.

Then WP6.6 (collapse), WP6.7 and WP6.8, and S6-Q.

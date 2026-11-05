# S6 — V6.11 host services on Echo: native restore and the HostEvents equivalence

2026-11-04, America/Mexico_City (05:45–06:00 UTC on 2026-11-05). Repository
head `64e27343c`, which regenerates the candidate source `5ADEF279…E2FA`
byte for byte. One guarded session on Echo `601FC87B` under the standing
owner decision O3, following plan §4, on the
[writable-strings candidate](AB_S6_HOST_WRITABLE_STRINGS_OFFLINE_2026-11-04.md)
(ACD `902831B4…E5C4`). **The session passed**, rollback included.

It follows two sealed failures, and it differs from the second only in its
procedure:
- the [first](AB_S6_HOST_SESSION_ATTEMPT_2026-11-04.md) found Read Only
  request strings, now fixed in the image;
- the [second](AB_S6_HOST_SESSION_02_ATTEMPT_2026-11-04.md) ran the restore
  logged out.

This one logs the fixture's ENGINEER account in before the adapter restores,
as the legacy restore always did.

## Stages

| Stage | Result |
|---|---|
| Guard, dump check, MANUAL, preflight | Pass. The preflight equals the re-baseline's record |
| Backup upload | Pass, with SDK and access audits |
| Candidate download | Pass. SDK audit, read-back equivalent, and the extended access audit, including every member nested in a writable ingress |
| Login | ENGINEER, level 4 |
| Native restore | Pass (below) |
| Logout | Level 0 |
| Events | The fixture's core rows in ST, SFC and LD: 21 rows pass, each with its own event and genealogy checks; inputs and policy restored |
| Capture | Coherent and equivalent (below) |
| Rollback | Pass: candidate MANUAL, genealogy pin downloaded with SDK and access audits, original documents unchanged by hash, 31/31 baseline cases, MANUAL, final preflight equal to the session start, final checks, timing |

## The native host adapter

`fraktal_host_adapter.exe`, compiled at the session head, ran against a
byte-exact session copy of the five baseline documents
(`FRAKTAL_AB_CONFIG_SET_DIR`), so the originals were never written.
- It discovered the V6.11 host services and reported `serving`.
- 0.77 s later it reported every document restored, with no loss.
- 0.08 s after that it kept the first document through a snapshot job.

The candidate was then no longer restoring, and its live values for
station, line and the three models equal the copied documents. Those
documents were saved by the V6.10 build under the genealogy revision, so this
also exercises the predecessor revisions natively.

This is the first time the Dart port's discovery, layout negotiation,
request and commit, acknowledgement and restore and keep jobs ran on a
controller.

## The HostEvents equivalence (WP6.5)

Once the fixture had stopped, `capture.py` made three reads on a quiet ring:
1. the legacy ring, metadata-bracketed;
2. the full canonical S1 acquisition;
3. the legacy ring again.

The results:
- **Coherent:** the two legacy batches are identical, and the canonical
  DataRevision (290) equals theirs.
- **The ring:** schema 5, capacity 16, wrapped. 144 events had been produced
  and it holds the newest 16, so the comparison covers slot wrap and every
  event kind the rows produce.
- **Equivalent:** each of the 220 leaves the legacy projection gives
  (`fraktal_ab_host_events.project`) equals the canonical leaf of the same
  path. No leaf differs, and the canonical ring has no leaf the projection
  lacks.

This is the native capture the plan required before the legacy ring can go.
The canonical ring publishes exactly what the legacy ring projects. The raw
canonical capture is sealed (`Session/capture_canonical.json.gz`) with both
legacy batches (`Session/capture_legacy.json`). The adapter's canonical-ring
reader can now be proven against them offline: its batch must equal the
legacy batch.

## Timing

TASK telemetry every 100 ms, from before the download to the rollback: 1,155
samples, 1,107 readable. The maximum scan was 9,112 µs with 0 overlaps. That
is under the 10,000 µs S6-Q bound, but above the 7,767 µs of the idle,
restoring candidate in the earlier attempts. The difference is the event rows
running under the adapter's keep jobs. After the rollback, the genealogy
baseline reads 1,166 µs, 0 overlaps.

## Artifacts

`AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04/Session/` holds 123 files:
- logs and JSON records;
- the scripts and SDK program source;
- the adapter's log;
- the session copy of the documents;
- both captures.

`withheld_artifacts.json` lists the ACDs, L5Xs and binaries by SHA-256 only.
The credential's secret appears in no archived file. There were no fault or
TASK-counter clears, clock, power or vendor-state operations, or Echo hard
kills.

## Still open

- **The adapter's HostEvents delivery:**
  - reading the canonical ring into the batch, proven against this capture;
  - the cursor and the sink.
- **Two adapter findings** from the second attempt: `SessionPermits` covers
  only the set gate, and a denied attempt retries every 10 s.
- **WP6.6–6.8, then S6-Q.**

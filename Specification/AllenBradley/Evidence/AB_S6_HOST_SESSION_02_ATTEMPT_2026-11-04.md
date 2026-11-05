# S6 — Second V6.11 host-services session: the restore denied while logged out

2026-11-04, America/Mexico_City (05:31–05:44 UTC on 2026-11-05). Repository
head `61205591d`, which regenerates the candidate source `5ADEF279…E2FA`
byte for byte. One guarded session on Echo `601FC87B` under O3, with the
stages of the [first attempt](AB_S6_HOST_SESSION_ATTEMPT_2026-11-04.md)
unchanged, on the
[writable-strings candidate](AB_S6_HOST_WRITABLE_STRINGS_OFFLINE_2026-11-04.md)
(ACD `902831B4…E5C4`). **The session failed** at the native restore again,
for a new reason. The genealogy baseline was restored and verified.

## What happened

Every stage before the adapter passed: guard, MANUAL, preflight, backup, the
candidate download with its SDK, read-back and access audits (the extended,
nested audit), and the candidate guard.

The Dart adapter discovered the host services and reported `serving`. This
time the controller accepted its host requests: the writable string family
works natively, and the restore jobs ran. The restore then stopped at the
line document, with the verdict `std.error.accessDenied`:
`Press.line: the controller session may not load sets`. The adapter stops a
denied attempt without concluding anything, as `live.restore` does. The
candidate stayed restoring, and the check timed out.

The rollback passed in full:
- the candidate's MANUAL, then the genealogy pin downloaded with its SDK and
  access audits;
- the original documents unchanged by hash;
- 31/31 baseline cases;
- MANUAL, a final preflight equal to the session start, final checks and
  timing.

The adapter's session copy of the documents was not written either: nothing
is kept while restoring. TASK maximum was 7,767 µs with 0 overlaps over 2,503
samples.

## Why

The session ran the adapter with no operator logged in. The baseline policy
requires level 0 at every gate, so the logged-out session passes the set
gate. That is what the reply's `SessionPermits` reports, and why the adapter
began: the model documents went first and were not denied. But each
document's values are then checked against their configuration class's
write level, and the line document's class needs a logged-in session.

V6.11 behaves as designed here: restoring writes stay under the logged-in
session's authorization, and the adapter gains no login. The legacy restore
always ran under the fixture's ENGINEER login. This session's procedure
missed that. So the next session logs that account in before the adapter
starts, and out after the restore. That needs no image change.

## Findings for WP6.5

- **`SessionPermits` is incomplete.** It is the set gate's predicate only, so
  it can report a session permitted that a document's class level still
  denies.
- **The adapter retries while denied.** Every 10 s it opens the model
  documents' restore jobs again under the same denied session. Each is a
  real, audited set transaction.

The adapter should wait for the session to change after a denial, and the
reply should cover the class levels a restore needs. Both are offline
changes for later; neither affects safety, because the station stays
unstamped and Start stays refused.

## Artifacts

`AB_S6_HOST_SESSION_02_ATTEMPT_2026-11-04/Session/` holds 108 files: logs,
records, scripts, SDK program source, the adapter's log and the session copy.
`withheld_artifacts.json` lists the ACDs, L5Xs and binaries by SHA-256 only.
The credential's secret appears in no archived file. There were no clears,
clock, power or vendor-state operations, or hard kills.

# S6 WP6.5 — Restore offered only to a session that could load every document

2026-11-05, America/Mexico_City. Entry commit `350607b16`, with the
uncommitted working tree. No controller was contacted. This fixes both
findings the
[second V6.11 host session](AB_S6_HOST_SESSION_02_ATTEMPT_2026-11-04.md)
recorded.

## The findings

That session ran the Dart adapter with nobody logged in. The baseline policy
requires level 0 at every gate, so the reply's `SessionPermits`, the set
gate's predicate alone, said the session was permitted. The adapter opened
the restore. The model documents loaded, and the line document was denied:
its 21 values, like one commissioning station value, need level 3. The
adapter then retried the whole attempt every 10 s under the same session,
reloading the models each time. Each reload was a real, audited set
transaction.

## The fix, on both sides

- **The controller** (`fraktal_ab_host_sets.prologue`). While restoring,
  `SessionPermits` is the set gate and each editable value's own resolved
  write level (`Levels.WriteLevel`), as the owner's transaction checks them:
  it is 1 only when the logged-in session could load every document. Opening
  a restore job is refused `ACCESS` on exactly that predicate (it was the
  gate alone), so what the reply publishes and what the open enforces cannot
  disagree.
- **The adapter** (`RootService`). A denied restore is not retried under the
  permission it was denied under. It is retried once `SessionPermits` has
  dropped and returned, which means a new session. This is defense in depth:
  with the exact predicate, a denial should no longer occur while permitted.

## Tests

- **`test_fraktal_ab_host_live`**, new case (12 tests in all), on the emitted
  code. The gate admits level 0, yet a logged-out session is offered no
  restore while restoring. Opening one is refused `ACCESS`. At level 4 the
  job is offered and the restore completes. With the per-value level check
  removed, the case fails.
- **`gateway/test/root_service_test.dart`**, new, against a scripted port
  whose every verdict is the denial:
  - one attempt, then no further attempt under the same permission, even
    with no retry delay;
  - none without permission;
  - exactly one more after the permission returns.

  Without the flag, the adapter reopens on every step (6 opens in 6 steps),
  and the test fails.

## Source 06

The same preparation as source 05
(`Gates/Prepare/prepare_candidate_06.json`):

All exits 0:
- **Image:** generated `7ECDC4F6…AC01`. The V6.10 owner image is
  byte-identical, and the BOOL scan of 15,912 lines is clean.
- **Both v38 targets** build, read back equivalent, and pass the SDK log
  audit.
- **Access:** the nested access audit passes on both read-backs, 141 types,
  no finding.
- **ACD:** `45483D6E…E7BC`, with a read-back equivalent to the source.
- **Capacity:** 2,234,928 of 3,145,728 blocks (71%), verified fit. The
  per-value check costs 640 blocks over source 05.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`), all exits 0:
- **Sources:** 4 files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway. Its 44 tests pass (the
  new one and 43 others), none skipped.
- **Python:**
  - the focused host-service, revision and image suites pass 242 tests with
    ResourceWarnings raised as errors;
  - full AB discovery passes 2,516 tests in 1,075 s, the previous 2,515 plus
    the new case. All 404 module hashes are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

## Boundary

The predicate and the adapter's rule are proven offline and compile for both
v38 targets. Their native run, with the ring reader's, is S6-Q's.

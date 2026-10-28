# Press S3 exit third attempt - walk stopped at the held mode-change case; genealogy restored

2026-10-25, America/Mexico_City. The owner approved `press_session_03` with
"approve press S3 exit session", after the
[retry](AB_PRESS_S3_EXIT_RETRY_ATTEMPT_2026-10-25.md). **The press walk ran most
of its scope natively and stopped at the fifth ST core case; the press
declaration is not accepted.** Everything that ran passed. The walk's cleanup
restored its inputs and policy; the rollback completed in full and Echo ends on
genealogy with the original host documents, 31/31 baseline cases and every final
check passing. The authorization is consumed. No commit or push.

## Target and artifacts

Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0; the exact guard passed
immediately before the start. Press ACD `15E8902551FD6C6D8041727E69D5C2FE917D5BAC0E031D808DB66D8EBFCFD76F`,
source `6FD00A4825A2ADFA0BE9E662446905B53461C17CE40A50C1DE02733F530FBB02`, fresh
backup `36F92C6321C8B8E9FB22127746AB96778E2634118E0DDED09CE63E6239F4FC1F`;
genealogy original `D67561C4...4084` only hashed.

## What passed natively on the press image

| Scope | Result |
|---|---|
| Backup, MANUAL, preflight, Program/download/Run, read-back, access | Pass |
| Isolated press medium commissioned from the image (station, line, three models) and restored | Pass |
| Access: unknown-user refusal, busy/authenticated/logged-out, class policy change and restore | 2 rows, 6 captures |
| Configuration: page walk and model bank, edit and exact restoration, hidden values, four provider refusals, set store save/list/export/import/load/delete | **8 / 8** rows; 36 captures; isolated set medium empty afterwards |
| Typed ingress: queries, stale and mismatched commits, stale revision, foreign root, unknown key, fractional value, edit and restore, PIN logout/login, legacy after typed | **14 / 14** rows, full-width wipe on every protocol row |
| Both commits in one multi-service request | `collision_refused`: both mailboxes refused, neither queued or replayed |
| ST core: normal cycle, handled NOK, hold and resume, hold then STOP | 4 rows; 4 sequence, 1 decision and 2 condition captures |
| ST hold then mode change | **Stopped**: `held mode timed out: step=0, error=0` |

All 49 paired captures passed. No dumps, fault clears, clock changes, power
operations or hard kills. The rollback, five-document restoration, 31 baseline
cases, final checks and preflight passed; restored LastScan median 99 us,
cumulative maximum 1,166 us.

## Cause and correction

The press walk's mode-change case waited for `Running` to drop. The generated
Unit does stand the chain down on a mode change (`Step := 0`, chart cleared),
but `Running` follows the run level, which only STOP lowers; it is re-asserted on
the next scan in MANUAL. The genealogy case never relied on `Running`: it waited
for the Part to abort, an owner the press does not declare.

The press case now waits for the mode to apply and the chain to stand at step 0;
counters must be unchanged, and the S3c layer still requires the cleared chart.
The scripted-Unit test now models the run level as the PLC does, so the earlier
wait fails there. The remaining cases (adopted fault and single-reset restart)
use the genealogy fixture's own Unit observables. An offline replay also shows
the standalone idle equivalence's oracle binding covers all 4,058 press contract
paths. **2,308 AB tests** and the root gates pass; the image is unchanged. A
fourth session needs a new current authorization.

Work: `C:/work/fraktal-ab-s3-exit-20261025/press_session_03/`.
Payload: [manifest](AB_PRESS_S3_EXIT_THIRD_ATTEMPT_2026-10-25/manifest.json).

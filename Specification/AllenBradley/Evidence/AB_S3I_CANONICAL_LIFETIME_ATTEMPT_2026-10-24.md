# S3i lifetime attempt — calendar capture failed, genealogy restored

Client date: 2026-10-24, America/Mexico_City. The owner answered **“Approve this
guarded S3i lifetime session”** to `call_cc943a76fb914520bb418dda6ea4beaf:0`
for ACD `A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42` on
local Echo **601FC87B**. **The session failed at the first calendar capture.
Every rollback step passed. S3i lifetime remains open.** The approval is
consumed. A separate session asked to “resume” while this driver was still
running. Nothing was started, repeated or interrupted; the driver was waited
on until it exited.

| Stage | Result |
|---|---|
| Guard, MANUAL (no write), preflight, backup, SDK/backup-access audits | Pass |
| Download, SDK log, read-back, effective access, candidate guard | Pass |
| Candidate fixture | **41/41**: 31 inherited, two Access, eight configuration |
| Accepted fixture pairs | **87**, all through the frame; independently replayed from native bytes |
| MANUAL after candidate | Pass |
| Calendar phase | **Failed** at `original_empty_profile`, before any calendar write (0 writes); public configuration restored |
| Retained Program/Run, retention, idle equivalence, generic acquisition, candidate TASK | Not reached |
| Rollback | Genealogy download, SDK log, access, guard: pass |
| Baseline regressions | **31/31** |
| Final checks / preflight / baseline TASK | Pass |
| Dumps before / after | None / none |

## Cause

The failed proof used all 100 polls: 91 unchanged-even waits, three odd polls
and six read windows. Every window closed one frame later (+2). The proof was
reading the frame generation, but each read outlasted the about 48 ms frame.

`CalendarRun.observe` sent `QUERY_CONFIG` on the mailbox writer, then passed
that same writer to the oracle. Every mailbox command sets the writer to the
500-byte frame size and leaves it there. The oracle gives its three observer
sockets the primary socket's size, so all four read the 173,792-byte frame in
500-byte requests. At the measured 12-byte reply framing that is an estimated
357 requests, against the 44 the fixture made at 4,000 bytes. The fixture's
captures record a 500-byte writer and an independent 4,000-byte observer,
which the calendar path bypassed.

## Correction

- `CalendarRun.observe` reads every pair through the same independent
  4,000-byte `capture_gate` observer the fixture uses.
- `fraktal_ab_paired_observation.read` refuses any read socket not at 4,000
  bytes, before any controller read. This applies to every caller.

The existing lifetime test replaced `observe` entirely, so it never exercised
the connection. A new test drives the real method and fails against the old
code, reading on the 500-byte writer. Another proves a 500-byte socket is
refused before any generation or wire read. No PLC source, image, value, type,
budget or proof rule changed.

Runtime: `C:/work/fraktal-ab-s3i-lifetime-20261024/runtime_9fe4b2baee484ed2bb9b25b66cd32168`.
Append-only payload: [manifest](AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24/manifest.json).
No ACD binary or credential is archived. No commit or push.

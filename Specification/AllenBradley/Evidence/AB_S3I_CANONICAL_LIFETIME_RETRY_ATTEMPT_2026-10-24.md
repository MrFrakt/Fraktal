# S3i lifetime retry — refused before download; controller unchanged

Client date: 2026-10-24, America/Mexico_City. The owner approved the S3i
lifetime rerun in chat (“yes”) for ACD
`A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42` on local
Echo **601FC87B**, from the
[retry preparation](AB_S3I_CANONICAL_LIFETIME_RETRY_PREPARATION_2026-10-24.md).
**The session helper refused its download gate. No download, mode change or
tag write occurred, and genealogy remained in place.** The approval is
consumed.

| Stage | Result |
|---|---|
| Guard, dumps before | Pass; none |
| MANUAL normalization | Already MANUAL=1; no write |
| Preflight, backup upload, SDK log, backup access | Pass |
| Pre-download gates | **Refused**: “Prior-stage Capacity evidence changed” |
| Download, fixtures, calendar, Program/Run, retention | Not attempted (no `deploy_attempt.json`) |
| Rollback | Not required; nothing was downloaded |
| Afterwards, read-only | Guard passes. Preflight equals this session's record: genealogy manifest, MANUAL/idle, five documents |

## Cause

The retry setup script copied 23 files as text. Eight of them needed no path
change, but their CRLF line ends were rewritten as LF. One is
`baseline_capacity.json`, which the helper binds by hash
(`CE2E2C42…` recorded, `8BD82E10…` copied), so it refused. A byte comparison
of every copy shows line ends are the only difference. The helper behaved as
designed: it failed closed on changed Capacity evidence before any controller
change.

The next setup copies every file as bytes, applying the path rebinding at
byte level. It then asserts that each copy equals its original apart from
that path. The approved correction itself (the independent observer and the
4,000-byte socket check) is unchanged.

Runtime: `C:/work/fraktal-ab-s3i-lifetime-20261024/retry_runtime_0eecb005d1bb4ecda0a50a157acffb61`.
Append-only payload: [manifest](AB_S3I_CANONICAL_LIFETIME_RETRY_ATTEMPT_2026-10-24/manifest.json).
No ACD binary or credential is archived. No commit or push.

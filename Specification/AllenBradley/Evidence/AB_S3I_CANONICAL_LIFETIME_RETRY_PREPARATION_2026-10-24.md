# S3i lifetime retry preparation — 2026-10-24

Client date: 2026-10-24, America/Mexico_City. **Prepared offline only. A new
current owner approval is required before this session.** No controller access,
tag write, download or mode change occurred in this preparation. The
[failed attempt](AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24.md) is sealed;
genealogy is restored and that approval is consumed.

The attempt failed because the calendar capture read the frame through the
mailbox writer's 500-byte connection. The owner approved the correction and
retry preparation in chat (“yes”). Two oracle/fixture changes and their tests
are the only source differences. The PLC source, image, values, types, budgets
and proof are unchanged.

| Gate | Result |
|---|---|
| `CalendarRun.observe` | Reads every lifetime pair through the independent 4,000-byte `capture_gate` observer, as every fixture capture already does |
| `fraktal_ab_paired_observation.read` | Refuses any read socket not at 4,000 bytes, before any controller read, for every caller |
| New tests | A real-`observe` test fails against the old code, which read on the 500-byte writer. A refusal test covers 500/4,000, 500/500 and 4,000/4,002 sockets |
| Focused suites | 22 pass (observation frame, lifetime fixture) |
| AB discovery suite | 2,191 pass in 300.715 s |
| Root suites / spec / contracts / strict consistency | 74 pass / pass / pass / 0 errors, 0 warnings |
| Source closure | 172 bindings: 168 unchanged, four changed (two sources, two tests), none added |
| PLC image | Regeneration is byte-identical to `0F3A5F6D…EC72C3`; exact-image v38 build/read-back and Capacity (87%) transfer from the [S3i preparation](AB_S3I_CANONICAL_PREPARATION_2026-10-24.md) |
| ACD copies | Deployment, review and mode-control copies made fresh from the pristine review copy; all `A5FAFA46…7E36C42` |
| Workspace | Sealed lifetime-preparation scripts, helper source and runtime template copied with only the workspace path rebound (seven occurrences) |
| Session helper | Rebuilt, 0 warnings. With authorization false, all six negative cases refuse before SDK or controller access. The cycle mode has no download or save |

## Proposed session

The approved lifetime scope is unchanged, now on the retry workspace:

1. Fresh guarded backup and download of `A5FAFA46…7E36C42`, then five-document
   restore.
2. The 41 candidate cases.
3. The fixed public calendar/target lifetime vectors with original-value
   restoration (at most 64 commits, 38 normal).
4. One Program/Run without download in the cycle, then a rerun of the native
   first-scan vectors.
5. Read-only retained type/value/scan checks.
6. Genealogy rollback, five-document restore, 31 baseline cases and final
   checks.

Fault clears, clock changes, firmware/network changes, power operations, hard
kills and vendor-state edits are excluded. AGENTS.md §3a requires current
explicit approval for this exact image and workspace; the working
authorization is false.

Workspace: `C:/work/fraktal-ab-s3i-lifetime-20261024/retry_prepare_1225822a67f84efc8efcb1ffeb9fffce`.
Append-only payload: [manifest](AB_S3I_CANONICAL_LIFETIME_RETRY_PREPARATION_2026-10-24/manifest.json).
No ACD binary or credential is archived. No commit or push.

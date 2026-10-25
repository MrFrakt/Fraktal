# S3i lifetime second retry preparation — 2026-10-24

Client date: 2026-10-24, America/Mexico_City. **Prepared offline only. A new
current owner approval is required before this session.** No download, mode
change or tag write occurred; the only controller access was read-only guard
and preflight. The
[refused retry](AB_S3I_CANONICAL_LIFETIME_RETRY_ATTEMPT_2026-10-24.md) is
sealed, genealogy stayed in place, and that approval is consumed.

That retry's helper refused to download because the setup script had copied
its files as text, rewriting CRLF line ends. One rewritten file was the
hash-bound `baseline_capacity.json`. This preparation keeps the approved
correction (independent 4,000-byte observer; socket-size refusal) and only
changes how the workspace is built.

| Gate | Result |
|---|---|
| Workspace copies | Byte-exact: 23 files copied as bytes with only the workspace path rebound (seven occurrences); each asserted against its original. A full byte comparison finds no difference |
| Download-gate dry check | New offline replica of the helper's file-bound deploy gates: Capacity evidence hash, review fields, baseline binding, ACD pin and prepared compare. Passes here; against the refused workspace it fails on exactly `baselineCapacityHash` |
| ACD copies | Deployment, review and mode-control copies made fresh from the pristine review copy; all `A5FAFA46…7E36C42` |
| PLC image | Regeneration is byte-identical to `0F3A5F6D…EC72C3`; exact-image v38 build/read-back and Capacity (87%) transfer |
| Source closure | 172 bindings: 168 unchanged, the same four changed files as the first retry |
| Session helper | Rebuilt, 0 warnings. With authorization false, all six negative cases refuse before SDK or controller access. The cycle mode has no download or save |
| AB discovery suite | 2,191 pass in 300.111 s |
| Root suites / spec / contracts / strict consistency / whitespace | 74 pass / pass / pass / 0 errors, 0 warnings / clean |

## Proposed session

Unchanged scope, now on this workspace:

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
explicit approval; the working authorization is false.

Workspace: `C:/work/fraktal-ab-s3i-lifetime-20261024/retry2_prepare_8a934eccd6e548aea4d0c1c5a2e06db7`.
Append-only payload: [manifest](AB_S3I_CANONICAL_LIFETIME_RETRY2_PREPARATION_2026-10-24/manifest.json).
No ACD binary or credential is archived. No commit or push.

# S4b frozen-package preparation — 2026-10-26

**This supersedes the initial S4b preparation's runnable package binding.**
The PLC image, application behavior, Capacity and authorized scope are unchanged.
No controller change has occurred; the native session is still unapproved.

Read the [initial preparation](AB_S4B_CANONICAL_PREPARATION_2026-10-26.md) for
the implementation, exact image, complete gate outputs, failures and proposed
41-candidate/31-baseline session. Its 808 artifacts and report hash still verify.
It verified 69 earlier seals (19,272 artifacts). Its failed final source check
is preserved rather than editing that evidence.

The check caught the IDE rewriting the shared generated package map with
Flutter 3.47.2 / Dart 3.13.2, after qualification with **Flutter 3.47.5 / Dart
3.13.4**. This was a package-root/SDK change, not merely a timestamp change.
The hash guard refused correctly. The owner/IDE-generated map is left alone.

The revised runner uses `dart_package_config.json`, copied from the tested
3.47.5 seal with every package root resolved to an absolute URI. It is private,
immutable and hash-bound. The mutable `.dart_tool/package_config.json` is not
an input to this runner. The same observer compiles to its expected argument
refusal under the private map, before network I/O. All 16 authorization
refusal cases and both missing-approval refusals pass again.

Runnable entry: `C:/work/fraktal-ab-s4b-20261025/session_01/qualification_session_v2.py`.
It reads `source_bindings_02.json` and invokes `candidate_regressions_v2.py`.
The SDK helper and all identity, active-session, idle, fault, dump, Capacity,
source/image, rollback and restoration guards remain unchanged. No approval
file, backup, session-start or deployment-attempt file exists.

- ACD: `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`.
- Source: `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
- Offline Capacity: **2,066,100 used / 1,079,628 available / 3,145,728 total
  Blocks (65%)**.
- Current gates: **2,336 AB / 74 root / 631 Flutter tests passed; 12 Flutter
  skips**; no analyzer issues, enforced lockfile, Windows debug build, both v38
  builds/read-backs, four access audits, 15 byte-identical accepted images.

Approval is still required for fresh backup, guarded MANUAL normalization and
Program/download/Run; five-document restore and inherited 41 candidate cases
with the concurrent read-only Dart observer/all-bank/detail reads; read-only
equivalence/capture/scan; pinned genealogy rollback, original documents,
31 baseline cases and final checks/preflight. Candidate work stops on its first
failure. Fault clears, clock changes, power/vendor-state operations and Echo
hard kills remain excluded. [AGENTS.md §3a](../../../AGENTS.md) requires
“current explicit authorization and an exact target check immediately before
use”; the V6.8 contract/offline approval is not that session approval.

Native S4b, GUI connection/rendering, S5–S7 and S3 physical I/O acceptance remain
pending. V2/Part III stay inactive. Nothing is committed or pushed. Credentials
and ACD binaries are excluded from the payload.

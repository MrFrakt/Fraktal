# S4b canonical desktop/configuration preparation — 2026-10-26

**Offline gates pass; the exact-image native session is prepared and unapproved.**
V2 and the Part III amendment remain inactive. No controller-changing operation,
commit or push occurred. Echo remains on the genealogy baseline.

## Decision and exact artifacts

The owner answered **“A — publish a read-only configuration view (Recommended)”**
to `call_519504369cbc4895aca3f61ae5696848:0`. This grants the V6.8 contract and
dependent offline work only. [AGENTS.md §3a](../../../AGENTS.md) says:
“Never perform a controller-changing operation … without current explicit
authorization and an exact target check immediately before use.” The new
download/mode/mailbox session still needs that authorization.

- Target: local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0,
  controller GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`.
- Prepared ACD: `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`.
- Generated L5X: `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`; generated from the S4b declaration, never hand-authored.
- Studio offline Capacity: **2,066,100 used / 1,079,628 available / 3,145,728
  total Blocks (65%)**. This is 161,700 more used Blocks than S4a's offline
  estimate. Native fit/scan and initialization/change-scan cost remain unmeasured.
- Pinned rollback original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  It is never opened; the session downloads a hash-checked copy.

## Implemented and verified offline

The opt-in PLC V6.8 view publishes exact read-service descriptors, configured
definitions and live/occupied-bank value rows. The existing R2 owner supplies
formatting, revisions and access decisions. Full-width wipes cover unreadable
and unused ValueText buffers, including the existing page window. The private
cache remains unexposed. The independent migration reference uses the legacy
capabilities/records/banks/access source, not the new view's values.

The Dart client discovers Symbols/Templates and the hashed manifest, projects
Core values/types, joins fragment members under one row guard, honors logical
bounds/count references, and carries quality and monotonic ages. The transport
exposes bounded reads only; unsecured direct writes return false locally.
The worker isolate, factory, reconnect policy, read tiers, read-only UI and
configuration adapter are implemented. Configuration batches yield to cyclic
reads, and unselected banks supply routing references without ValueText reads.
No observation frame or station declaration is a client dependency.

Golden replay matches the accepted genealogy **4,428** and press **4,058**
paths/types. Generated-ST/interpreter vectors independently match **979** added
view paths and four configuration pages (live plus three banks). Those V6.8
vectors are explicitly synthetic/offline, not native captures. The four old
HMI spike files and 13 one-off probes are preserved in a hashed retirement
archive and removed from the active tree. The legacy Python projection,
contexts, Frame adapter and observation instrument remain for S6.

| Gate | Exact output/result |
|---|---|
| AB discovery suite | `Ran 2336 tests`; `OK` (`ab_suite_02.log`) |
| Root suite | `Ran 74 tests`; `OK` (`root_tests_01.log`) |
| AB spec/contracts/strict consistency | exit 0 (`final_spec_01`, `final_contracts_01`, `final_consistency_01`) |
| Both v38 targets | EchoController and PhysicalController build/read-back pass |
| Access and SDK logs | four access audits; three clean SDK log audits |
| Prior images | 15 byte-identical (`compatibility_retry_01/accepted_images_01.json`) |
| HMI lockfile/analyze | `pub get --enforce-lockfile`; `No issues found!` |
| Full Flutter suite | **631 passed, 12 skipped** (`final_flutter_03.log`) |
| Windows desktop | debug build passes (`windows_build_03.log`); GUI connection/rendering not run |
| Authorization | 16 negative cases; missing-approval CLI and SDK stop before controller access |
| Whitespace | exit 0 with explicit `cr-at-eol` for tracked CRLF assets; default failures retained |

SDK: **Flutter 3.47.5 / Dart 3.13.4**, revision
`6a19cca56475dbfba1478ee68d7bd0c2ef891da1`, at `C:\work\fraktal-toolchains\flutter-3.47.5`. No dependency/lockfile
change was made. Owner changes in facet_cards and Siemens archives remain untouched.

## Read-only native checks and failed runs

On the unchanged genealogy image the new Dart reader pins identity and discovers
**60 Symbols / 50 Templates in 164 ms** (`native_read_wire_04`). Three earlier
read-only probes failed: SendUnitData Sender Context was incorrectly required
to echo; then the Identity ProductName attribute was requested instead of serial.
The corrected code uses session/connection/sequence for connected replies and
Identity attribute 6 for serial. No controller writes occurred. Protocol sources:
[ODVA PUB00123R1 §3.3.11.2.3](https://www.odva.org/wp-content/uploads/2020/06/PUB00123R1_Common-Industrial_Protocol_and_Family_of_CIP_Networks.pdf)
and [Rockwell 1756-PM020I](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf).

The final Flutter attempt initially caught the existing 80 ms detail-renewal
timer firing at 79.879 ms. The scheduler now rechecks its monotonic deadline
and rounds the remaining timer upward. The unchanged cadence assertion and
all 22 freshness tests pass; both subsequent full suites pass. Other retained
failures include schema/type warnings, early negative tests, a compatibility
wrapper that called a module without a CLI, SDK build before restore, and CRLF
whitespace checks. Their exact logs/exits are retained; none is native acceptance.

Read-only final checks pass: Run/not faulted/Remote, scanning, MANUAL/idle,
logged out, not restoring, policy restored and five saved documents equal to
live (`readonly_baseline_01.json`). No new dump or controller operation is
part of this preparation. Credentials are excluded from the archive.

## Prepared guarded session and acceptance still pending

`C:/work/fraktal-ab-s4b-20261025/session_01/qualification_session.py` refuses
without current exact-image authorization and matching source/gate hashes.
All guard/session/SDK helpers build or compile; the authorization template is
false and no authorization file exists. The single-use session is:

1. Fresh identity/listener/service/dump checks, guarded MANUAL normalization,
   fresh preflight and backup; SDK backup audit requires **Save As**.
2. Program/download/Run of the exact ACD above, read-back and access audit.
3. Read-only Dart worker/tier observer establishes a fresh progressing root
   before candidate fixture writes; it runs alongside the inherited **41**
   fixed candidate cases (31 main, two Access, eight config/set-store), including
   five-document restoration and restoration of changed values. It then reads
   every occupied bank and chart details without mailbox queries. No new typed
   command vectors are added.
4. All-path independent equivalence, generic capture and native scan.
5. Hash-checked genealogy rollback after any download attempt; exact original
   host documents, five-document restore, **31** baseline cases, MANUAL cleanup,
   final checks/preflight. A fault/dump stops further controller operations.

Fault clears, clock changes, power operations, vendor-state edits and Echo hard
kills are excluded. The observer owns a read-only Dart helper only. Failed runs
are kept and candidate work stops at its first failure. **None of this session
has run.** Full S4 acceptance also requires desktop connection/rendering; the
prepared native observer is not that GUI acceptance.

S5 gateway/installer and per-station write posture, S6 consumer census/legacy
retirement/persistence-event ownership/reductions, and S7 physical/CIP Security
acceptance remain. S3 physical real-I/O proof remains open. Persistence medium,
gateway station posture, S7 hardware and commit/push policy remain owner decisions.

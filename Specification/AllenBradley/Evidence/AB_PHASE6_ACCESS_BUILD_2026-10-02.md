# Fraktal/AB Phase 6 item 3 — controller access, offline build

**Date:** 2026-10-02, America/Bogota. **Parent:** `9e97af4`.
**Stage:** generated and tested offline; owner Studio v33 import,
Verify/download and guarded hardware verification pending. No controller writes
or download were performed. The last verified build is press55; its
[hardware evidence](AB_PHASE6_SETS_ON_HARDWARE_2026-10-02.md) remains historical.
The companion [JSON](AB_PHASE6_ACCESS_BUILD_2026-10-02.json) records artifacts,
source hashes, checks and mutations without credentials.

## Generated artifacts

Both declarations were generated from `C:\work\seed_v33.L5X` and reproduce
byte-for-byte, including a second reproduction after final source changes.
No L5X, ladder or SFC was hand-edited.

| Property | Press | Station template |
|---|---|---|
| File | `C:\work\press56.L5X` | `C:\work\phase6_access_template.L5X` |
| SHA-256 | `31216EFAECE6FC7B7E8D417162791CCA3650E28820D25C8D824FC6F5ECD57D6F` | `C0F79CD3EE1957494AEBB39CFFCD2769808D0829BB21F29C658DC028FE61575E` |
| ContentHash | `0FC1A37DB998B41C` | `C18743A4092531BF` |
| ConfigRevision | 1032611 | 12683075 |
| Manifest major | 3 | 3 |
| Manifest bytes | 79,992 | 79,992 |
| Fields | 544 / 768 | 358 / 768 |
| Localization | 541 / 768 | 452 / 768 |
| Rationalization | 23 / 32 | 19 / 32 |
| WriteCapabilities | 9 / 64 | 4 / 64 |

The manifest capacities and 102,400-byte budget are unchanged. ContentHash
identifies the published contract, not logic; the file SHA identifies this build.
The provider adds 200 bytes of public session/policy, 9,740 of public audit
metadata, 6,248 of private user/hash work and a 2,428-byte private sampled
mailbox request: 18,616 declared bytes, excluding native instruction/platform
bookkeeping. The sidecar uses the existing 64-entry alarm-ring capacity rather
than introducing another history ring. Its underlying projection still polls
whole structures; the HMI requests history on demand.

XML comparison against press55 confirms unchanged module AOIs, I/O, tasks and
all ST/SFC/LD mode-chain routines. Main and the mailbox change, and a SHA routine
is added. External Access matches the previous artifact plus the two new
read-only access tags. User/hash work and the sampled request have None; the
operator command surface remains the one HmiRequest mailbox. This is an offline
comparison, not a measured CIP security result or S9 pass.

## Controller authority and TC3 semantics

`access_users` is the declaration source for a maximum sixteen registrations.
Each contains name, level 1..4, a distinct 16-byte salt and a 32-byte hash. The
template enables an empty provider with `access_users=()`; `None` preserves a
legacy declaration's named refusals. Shipped policy is fully open: twelve NONE
thresholds and timeout zero, matching Core §7.7 and TC3.

The commissioning helper uses hidden confirmation prompts and prints only a
hash registration. The three press registrations are private bench apparatus
at OPERATOR, TECHNICIAN and ADMIN levels. Their unique random PINs live only in
a newly created local fixture file restricted to owner and SYSTEM. They are
absent from the repository, generated project and evidence. No existing bearer
or credential file was read or modified.

The algorithm matches TC3 §150: SHA-256(salt || PIN), then 256 further hashes of
digest || salt. Our maximum 48-byte message fits one SHA block. Unknown users
perform the same bounded work using a zero salt; all 32 digest bytes are compared
without an early exit. Invalid native string lengths and user-table bounds fail
without out-of-range indexing. Both transported and private Secret bytes are
wiped before the first compression; each buffer and schedule is then wiped.

LOGIN acknowledges consumption immediately, publishing optional LoginBusy
while one SHA block runs per task scan. Expected completion at a 10 ms period
is approximately 2.56 seconds; hardware scan cost remains to be measured. Other
mailbox commands remain available. A second LOGIN is refused by name; LOGOUT
cancels pending authentication. Immutable sampled identity prevents later
payload edits or policy requests from changing the result. Completion does not
rewrite a newer mailbox acknowledgement. Wrong PIN preserves the old session
and sets LoginFailed. Successful login replaces it. Entry to Run clears the
volatile session and work while retaining users/policy.

Every mutation checks its controller gate before dispatch, including direct CIP
mailbox writes. Policy edits validate levels, action ordinals and timeout bounds
and reject raising ACCESS_POLICY above the active level. ACK_CONFIG_RESTORE
directly requires ENGINEER, independently of policy, as TC3. Held-input release
always withdraws the input. Only successful login and accepted authenticated
mutations rearm idle time; reads, release/list/export queries and denials do not.
The session belongs to the root and is shared by its clients.

Configuration and set audit actors now come from the controller session rather
than the request's User claim. Access audits record LOW AUTO_RESET instant
come-and-gone closed events in the existing §8.3 ring. Typed sidecar metadata
supplies actor, kind, gate and result; normal alarms may overwrite its slots.
No audit contains a PIN or hash.

## Logix implementation and HMI

The ST hash uses native `BTDT` with a private
`FBD_BIT_FIELD_DISTRIBUTE` instruction tag. Rockwell documents ST `BTDT(tag)`
and CompactLogix 5370 support in its
[instruction reference](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/move-logical-instructions/bit-field-distribute-with-target--btdt-.html).
[BTD is ladder-only](https://www.rockwellautomation.com/en-us/docs/factorytalk-design-studio/current/contents-ditamap/instructions/instruction-set/move-logical-instructions/bit-field-distribute--btd-.html),
so the earlier Q1 implementation sketch has been corrected. Modulo additions
use 16-bit limbs rather than relying on signed DINT overflow. Masked dividends
are exact multiples, avoiding Logix integer-division rounding differences.
These references support the instruction choice; Studio v33 is still the
compile arbiter.

The gateway projects the PLC user, level and policy. Its --access-level option
only bounds the pre-login display and cannot grant a role. Missing provider
state fails closed. Bearer/proxy transport authentication remains separate.
The generic repository waits up to six seconds for LoginBusy to clear, then
checks LoginFailed, requested user and a positive level. Synchronous providers
without the optional field continue working. No AB screens were added.
The updated Web artifact built successfully at `C:\work\press56_hmi_web`;
it has not been deployed.

## Verification and remaining gate

- AB: 1,399 tests passed. Consistency: 33 passed, zero errors and warnings.
- HMI: 431 passed, six skipped; analysis clean; Web build successful.
- Seven compression vectors match hashlib, including empty, abc, binary and
  maximum-length blocks. One complete 257-block login executes the emitted SHA
  without an oracle shortcut. Checked arithmetic tests reject any intermediate
  signed overflow; provider/control tests use a separate hashlib oracle.
- Python mutations: 23/23 killed against a 17-test baseline and targeted cases;
  HMI mutations: 2/2 killed with all eleven repository tests executed. They cover
  hash constants/rotates/rounds, sampling-time wipe, digest comparison, async
  identity/ACK/cancellation, gate bypass, self-lockout, timeout/activity, restore
  level, held withdrawal, actor spoofing, audit severity, startup, projection
  role fabrication and fixture restoration/serial checks. Two initial wipe
  mutants exposed a test gap: checking only after dispatch missed late cleanup.
  The corrected test observes both Secret buffers before the first compression.
  All final mutants are assertion failures; none depend on syntax/import errors.

Python mutations execute changed source in child memory, with -B, bytecode
writes disabled and fresh cache prefixes. HMI mutations use an external copy.
No repository source was mutated for these checks and no caches were deleted.

The final SDK probe attempted OpenLogixProjectAsync on press56 and exited 1:
`OperationFailedException: No valid license. C:\work\press56.L5X`.
The handover assigns import/Verify/download to the owner's licensed Studio
desktop. This record claims generated and modeled behavior, not a compiler pass.

After owner Verify/download and gateway restart, `fraktal_ab_phase6_execute.py
192.168.100.89 --expect-serial 7036B510 --access --execute-fixture` performs the
guarded proof. Serial/fingerprint and anonymous default-policy reads precede
writes. It checks three accounts, wrong PIN, native User spoof denial with the
plant unchanged, set/policy denial, an accepted technician plant mutation,
activity rearm, pure-query expiry and the audit. Native probes recheck serial
and recreate the local sequence owner afterwards. Finally every original gate,
value and timeout is attempted independently, then logout; parent cleanup
restores baseline/mode/style and disarms all ten fixture inputs. It has not run.

The v33 legacy zone-and-conduit bench remains write-enabled by the explicit
2026-09-29 decision. This item widens writes to login and policy administration.
**S9 and the write-enabled claim remain owed.** Maximum task cost/overlap/faults,
physical power-cycle/download/upgrade retention, model-set load integration,
per-value data classes and shelving remain owed.

Import `C:\work\press56.L5X` in Studio 5000 v33, Verify Controller, download to
serial `7036B510` at `192.168.100.89`, then restart the gateway. Use the updated
generic HMI build when checking login. The owner's `done` authorizes the named
guarded verification loop, including manifest equality (major 3, 79,992 bytes,
hash above), readiness, S3, access, capture/sets and the prior regression suites.

# Fraktal/AB Phase 6 item 5 — alarm shelving, offline build

**Date:** 2026-10-03, America/Bogota. **Parent:** `918baec`.
**Stage:** prepared offline; owner Studio v33 Verify/download, gateway restart
and guarded hardware verification pending. The owner's “go on” authorizes this
offline item. No controller write, download, clock change or gateway restart
was performed. Press64 remains the last confirmed controller build.
The companion [JSON](AB_PHASE6_SHELVING_BUILD_2026-10-03.json) records artifacts,
source hashes, checks and mutations without credentials.

## Artifacts and scope

Both artifacts reproduce byte-for-byte from `C:\work\seed_v33.L5X`.
No L5X, ladder or SFC was hand-edited.

| Property | Press | Station template |
|---|---|---|
| File | `C:\work\press65.L5X` | `C:\work\phase6_shelving_template.L5X` |
| SHA-256 | `062530E31E0F03335E2F3C0F7C3248E95AF50C4C2672A66D89772ACF9B0D5A1C` | `F498CDA3CF50E223F0205F8BD543136A6230CA059515600A4A61D0EE315A29F7` |
| ContentHash | `832DD0D0F260872B` | `12B6BB5F18F8C282` |
| ConfigRevision | 8596944 | 1226427 |
| Manifest major / bytes | 4 / 80,760 | 4 / 80,760 |
| Fields | 565 / 768 | 379 / 768 |
| Localization | 570 / 768 | 481 / 768 |
| Rationalization | 23 / 32 | 19 / 32 |

AlarmActive/Ring V2 preserve their V1 prefix and append the Shelved column.
Private countdown work holds sixteen bounded durations. AccessWork becomes
private V6 so lifecycle events can retain their alarm source and explicit gate.
AccessState V3, AccessAudit V3 and the private registrations with their
four-slot capacity are unchanged.
The manifest row layouts remain major 4; the new field content changes its hash,
so controller and gateway must be updated together. No capacity raise occurs.

Declared payload grows by **424 bytes**: 320 for the two shelf columns, 96 for
private shelf work and 8 for private audit arguments. Compiled code and platform
bookkeeping are excluded; this figure does not establish controller fit.
XML comparison against press64 confirms unchanged module AOIs, mode chains,
I/O modules and tasks. Main, mailbox, audit and the key-dependent data-level
refresh routine change; no routine is added. Public alarm storage remains
externally read-only; shelf work remains private. The writable tag set is
unchanged. Embedded I/O remains uninhibited, output updates enabled, with
20 physical references and eight forceable outputs. This offline item did not
operate I/O.

## Authority and semantics

Core §8.10, TC3 IMPLEMENTATION_NOTES §22 and FB_AlarmLog/FB_UnitBase are the
behavioral oracle. The template already enables the alarm log and access
provider, so it inherits the same mechanism without project calls or flags.
Declarations without an access provider retain the named shelving refusal.

The PLC compares native request bytes for SourcePath and Description and
resolves exactly one non-closed event; it accepts no client slot or reason
ordinal. Foreign, missing, closed and duplicate identities refuse. ALARM_SHELVE
(gate 9) is checked against the PLC session, not the claimed request User.
The same registry-derived rationale that emits the manifest decides whether
the reason is shelvable. SAFETY wins over any shelvable flag; missing metadata
and non-shelvable reasons refuse.

As TC3, milliseconds are converted to whole seconds. Zero, negative and
subsecond durations refuse; the upper bound is 28,800 seconds. A new shelf
restarts the countdown. The binding uses its existing periodic task-duration
clock: it advances when the owning task executes, independently of calendar
changes. Hardware expiry accuracy and scan cost remain pending. No clock was
changed to test this behavior.

Shelving changes annunciation only. The event state, Error, interlocks,
Blocking and release rows remain authoritative. A shelved WAIT_RESET event
still refuses Start. Reset closes events normally; ring history retains their
shelf mark, and slot reuse clears the old flag/countdown. An unreused closed
slot's countdown still expires, matching TC3's Cyclic behavior.

Shelf, manual unshelf and expiry enter the existing 64-slot event ring as LOW
AUTO_RESET lifecycle messages. Operator events retain the actual actor and
alarm source; automatic expiry has sequence zero and no claimed actor. They
never create a blocking event. The ordinary accepted-action audit and idle
activity behavior remain inherited from the access provider.

The gateway projects the PLC's flag through the field the generic HMI already
consumes. Shelved events remain in lists with de-emphasis and leave banner
annunciation. No unused deadline or second client-side countdown is published.
HMI production source and the deployed HTTPS release are unchanged.

## Offline verification

- AB tools: **1,472 tests pass**, including nineteen shelving semantic tests
  that execute generated ST and five new fixture authorization/cleanup checks.
- Consistency: **0 errors, 0 warnings**, including inventory, localization,
  language parity and read-surface checks; its suite **33 tests passes**.
- Nine in-memory mutations are killed by assertion failures after their
  targeted baselines pass: cap, zero duration, safety override, ambiguous
  identity, expiry logging, slot reuse, control blocking, projection and role
  gating. No source-file mutant or active AB bytecode cache remains.
- HMI mapper/access/catalog checks: **15 tests pass**, including preservation
  of an active blocking event as Shelved changes. Analyze reports no issues.
- The SDK attempts `OpenLogixProjectAsync` on press65 and refuses **No valid
  license** before opening the project. It performs no online operation.
  Owner **Verify Controller** on the licensed Studio desktop is the compile
  gate; no clean compile or controller fit is claimed by this record.

## Deployment and remaining gate

Import **`C:\work\press65.L5X`**, run Studio v33 **Verify Controller**, download
to serial **7036B510** at **192.168.100.89**, and restart the gateway. No HMI
release rebuild or proxy change is needed. After the owner's “done”, run full
manifest/health readback and `fraktal_ab_phase6_execute.py --shelving
--execute-fixture`, followed by the existing regression set and final health,
manifest and fixture-disarm checks.

The prepared harness checks a standing shelvable metrics event, native role
impersonation refusal, identity/duration negatives, an above-cap accepted
request, expiry after logout and an unshelvable cylinder defect that still
blocks Start. The exact eight-hour assignment and duplicate/safety cases are
offline semantic checks; an eight-hour hardware wait is not performed here.
Read-only preflight accepts a known owner or anonymous session and refuses
pending login, foreign session or an existing active shelf. Private local
credentials are consumed only inside the armed fixture and never emitted.

The fixture attempts each independent restoration even after an earlier
failure: original gate policy, timeout, shelf and known owner session. The
parent restores mode/style/baseline and plant inputs in finally and disarms.
Every primitive direct write rechecks the exact serial; gateway transactions
retain their existing serial/fingerprint and Sequence-last discipline.

The bench's 2026-09-29 decision remains write-enabled on the v33 legacy
zone-and-conduit baseline. Item 5 widens the mutation surface with shelves.
The **write-enabled S9 claim**, physical retention, compile/fit and measured
runtime budget remain owed. These offline results close none of those gates.

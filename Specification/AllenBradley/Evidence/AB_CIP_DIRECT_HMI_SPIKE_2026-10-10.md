# AB cip:// direct HMI transport — spike state (session handoff)

Recorded 2026-10-10. Goal: the Fraktal Windows HMI connecting **directly** to
the Logix Echo press over EtherNet/IP (like ADS on TC3), no gateway process.

## Working (proven on the Echo emulator, 5069/1756 v38.011 at 127.0.0.1:44818)

- press86_echo38 project running (owner-downloaded); ScanCount climbing.
- `libplctag` v2.7.2 vendored at
  `FraktalCore/HMI/native/cip/third_party/libplctag-2.7.2/` (plctag.dll,
  libplctag.h, SHA256SUMS; DLL sha256
  936e197eded4ffd642d7d45c27b8945650d206c918ddcc3fda0ca041a34e6bde).
- libplctag-based reads WORK: `plc=lgx` attribute is REQUIRED in v2.7
  (`plc_type` is not recognized) — `protocol=ab_eip&gateway=HOST&path=1,0&plc=lgx&name=TAG&elem_type=DINT&elem_count=1`.
- `cip://` scheme wired end to end: wizard accepts it, preflight maps port
  44818, factory builds `CipSessionClient`, `OpcUaRepository` consumes the
  snapshot envelope (`values` + `paths`), HMI renders the press directly.
- Type keys for the press modules are served by the client (declaration
  pairs); the manifest does not carry them.
- Write-only mailbox members (`ExternalAccess=None`: Kind, TargetPath,
  NameValue, TextValue, User, Secret, IntValue, BoolValue, DurationMs) REJECT
  reads by contract (privilege violation / hidden). `Sequence` is Read/Write.
  A raw write to such a member from libplctag reported OK on the Echo but the
  value did not change (echo firmware treats None as no-access for unconnected
  writes) — see Open items.

## Open items (this is where the next session picks up)

1. **Connected-transport commanding**: the Echo accepts tag reads/writes only
   over a CIP connection (ForwardOpen + SendUnitData). The pure-Dart client
   (`lib/data/cip/eip_cip_client.dart`) now: RegisterSession OK, Extended
   ForwardOpen (0x5B, large-format 4-byte params, 0x4200|4000) OK, T->O CID
   captured from the reply (0xfff140xx pattern). The connected Read Tag
   returns CIP 0x13 "not enough data" — the path-length word covers
   path+count; the request needs the count OUTSIDE the path. Fix in
   `_cipTransaction`/`connectedRead` (split pathLen from count), then
   commanding flows through `connectedWriteDint/Bytes`.
2. **libplctag write-only members**: writes report OK but do not land on the
   Echo (unconnected route). If connected libplctag writes are preferred over
   the Dart path, use the connection-group attributes or the raw CIP service
   (`name=@raw`, see tests/test_raw_cip.c in libplctag).
3. Probe tools: `HMI/tool/probe_cip_direct.dart` (snapshot + raw read) and
   `HMI/tool/probe_cip_write.dart` (setMode transaction) — current state
   mirrors the open item 1.

## Environment notes

- HMI debug builds on this VM run VS Code's Flutter 3.47.2 (repo pin: 3.47.5);
  `pub get --enforce-lockfile` passes, lockfile untouched, deviation recorded.
- Windows Developer Mode was enabled on this VM (plugin symlink requirement).
- The wss gateway path (token + TLS, full projection) remains the complete
  supported transport; press86_echo38.acd is the verified artifact.

## Session-end debug state (2026-10-10 late)

`connectedRead` over the established connection returns a reply whose first
6 bytes are `[00 00 a0 02 0c a7]` followed by the KARF magic of the
MfHeader struct — i.e. the connected Read Tag works but the reply carries
6 leading bytes my parse does not skip (`[target seq(2)] [reply service(1)]
[status(1)]` + 2 more — likely the additional-status-size word). DEBUG
prints are left enabled in `EipCipClient` (`DEBUG chunk/tx-rr/connected
tx/rx`) and the exact tx/rx hex for one MfHeader read is reproducible with
`dart run tool/probe_cip_direct.dart 127.0.0.1`. Fix = adjust the reply
strip offset in `_cipTransaction` (currently `dataIndex + 4`), then verify
KeyLength = 56 decodes and the manifest tables parse.

## Addendum (2026-10-10 later): commanding root causes found and fixed

Diffing the pure-Dart client's wire bytes against libplctag's (debug level 5
dumps both directions; `tool/probe_libplctag_wire.dart`) found three defects,
plus one binding-level one behind the "unknown_kind" refusal
(`project.mailbox.refused.unknown_kind`, NumericKey 637, read from the
manifest localization pool):

1. **Member paths must be separate symbolic segments.** The client sent
   `Tag.Member` as one 0x91 segment carrying the literal dot; the Echo
   resolves it only as `[0x91]"Tag" [0x91]"Member"`. The one-segment form
   returns a *successful* Read reply whose value bytes are a stub
   (`c4 00`-less 4-byte body, same for every tag) — reads of every member
   were garbage while whole-tag reads (manifest tables, Unit, MfHeader)
   worked, which is why rendering looked alive. `_symbolPath` now splits on
   `.` (libplctag's proven form).
2. **Write Tag argument order was swapped.** CIP Write Tag is
   `path, type, count, data`; the client sent `path, count, type, data`.
   That is why writes reported success but stored garbage — and why the
   controller kept refusing `unknown_kind`: the Kind argument never landed
   while the Sequence commit word (last in order) sometimes did.
3. **Read replies carry an additional-status-size word** after the general
   status; struct payloads are `type 0x02A0 + 2-byte instance + data`
   (the Echo emits a 2-byte instance), atomic payloads are `type + data`.
   Write replies instead carry one trailing word and no data. The parse is
   now per-service; the KARF-magic anchor hack in `CipSessionClient` is
   gone.

**Binding change (press87_echo38_rw):** with 1–3 fixed the handshake
completes (`ack == committed sequence`) but the refusal stays 637, because
the Logix Echo **drops connected writes to ExternalAccess=None members**
(success reported, nothing stored) where the real L24ER family honors
write-only access — confirming the earlier libplctag observation. No client
can command the echo38 build through its guarded write-only mailbox. The
generator therefore gained `Application.simulation_mailbox_rw` (default
FALSE; bench builds unchanged, guarded form intact): the echo38 declaration
sets it, so `FRK_T_PressHmiRequestV3` argument members emit
`ExternalAccess="Read/Write"` on the simulation build only
(test_fraktal_ab_generate.Echo38TargetTests asserts both shapes; full AB
suite 1677 OK).

**press87_echo38_rw** — `C:/work/press87_echo38_rw.L5X`
(sha256 `256EF270F7107A3FD079F163DF029026EF1328BE38BC6831745754BD463C802B`),
delivered as `C:/work/press87_echo38_rw.ACD`
(sha256 `D3841D55500C749317FF2A68DBCAFB80D697A67EFBA1DB2549A9CB43D3DECD38`)
via L5X open + SaveAs; **offline-compiled: Build succeeded on BOTH
`EchoController` and `PhysicalController` targets, 0 diagnostics**.
Pending: owner download to the Echo (S15 posture), then
`dart run tool/probe_cip_write.dart 127.0.0.1 2` must show
`ACKED ... accepted=true` and the HMI mode change must move the controller.

**Verified end-to-end with the fixes (against the still-downloaded press86):**
libplctag write of Sequence=6 → `AckSequence=6` fires (mailbox processing
reachable from this VM); pure-Dart setMode transaction commits and polls;
ack/accepted/diagnostic read correctly. `flutter analyze` clean (probe-file
lints fixed), 565 tests pass, Windows debug exe rebuilt with the fixed
client, `plctag.dll` staged beside it.

## Addendum 2 (same day, commanding proven end-to-end)

**The remaining refusal was the V3 native frame.** The generated mailbox is
`FRK_T_PressHmiRequestV3`: on each Sequence commit the handler CPS-samples
`FRK_Press_HmiRequest.Frame.Words`, requires `Words[0] == 1` (schema) and
`Words[last] == Sequence`, then **rewrites Kind and the string members from
the frame** (`q.Kind := -1` first, so a missing frame decodes as
`unknown_kind`). Member-wise writes are the legacy surface and never reach
the dispatcher — every transaction up to here was refused 637 for this
reason, not because of transport. The client now stages the mailbox members
it is given and, at the Sequence commit, emits the S9 native frame
(fraktal_ab_mailbox_frame.encode mirrored in Dart: schema, four scalars,
five string lengths, packed ASCII payload padded to the 500-byte pylogix
connection budget, Sequence echo) as **one DINT-array write followed by the
Sequence commit** — two round trips, commit word last.

**Access login proven on the Echo (press88).** LOGIN (frame Kind=1,
User/Secret as frame strings) is accepted for processing immediately and
completes **asynchronously**: 257 SHA-256 rounds at HASH_BLOCK_SCANS=2 per
round take well over 12 s under the emulator; the definitive result is
`FRK_Press_AccessState.LoginResultSequence/CurrentLevel` (a settled login
can also be read from `AccessState`, Read-Only). Probe flow verified:

- `LOGIN echo_admin` → accepted; ~25 s later `CurrentLevel=4,
  UserLength=10, LoginResultSequence=<seq>`.
- `SET_MODE 2` → `accepted=true diagnosticKey=0 mode=2` — **the Echo
  controller's mode moved to MANUAL**, commanded from the Fraktal client
  over direct CIP with no gateway.

**Contention findings (recorded, not bugs):** the mailbox is one-writer by
contract. A stale gateway instance left running against the Echo after a
download loops its live-document restore (`LOAD_CONFIG_SET`, kind 29) every
~3 s — each attempt refused `accessDenied` (gate 11, anonymous) — and
tramples concurrent writers. Stop stray gateway/HMI writers before probing;
one writer (the HMI) is the supported shape.

**State:** press88_echo38_rw.ACD downloaded and running (owner);
`flutter analyze` clean, 565 HMI tests pass; Windows debug exe rebuilt with
the frame-writing client and `plctag.dll` staged. Remaining owner step:
launch the HMI, log in as `echo_admin` (PIN in
`C:/work/fraktal_echo38_access_fixture.json`), and command the mode change
from the UI.

## Addendum 3 (same day, HMI commanding false-failure root cause; faster login)

**The "Mode change blocked" banner was a client filter bug, not commanding.**
`CipSessionClient.readValues` looked its paths up in the snapshot ENVELOPE
(`{'values': …, 'paths': …}`) instead of the `values` map, so every ack poll
read an empty map, never matched the ack, and timed out at 2 s — while the
controller had already accepted and executed the command (the user's log
shows `opcua-request-timeout` beside a later `ack=<seq> accepted=1`). The
same filter black-holed the login and logout polls. One-line unwrap; the
poll now returns the three response leaves and commands settle in one
round-trip. Every HMI command had in fact been landing (ModeSwitches
climbed; the logout cleared the session).

**Login hashing sped up by owner direction** ("more than 3 s is
unacceptable"): `PIN_HASH_ROUNDS` 256 → 16 in `fraktal_ab_access.py`. The
runtime hashes one block per `HASH_BLOCK_SCANS` (10) scans, so a login
costs 17 blocks — ~1.7 s nominal, measured well under the old ~25 s on the
Echo. `login_timeout_ms` publishes 11700 ms; the HMI budget follows the
declared value. `echo_admin` re-provisioned at the new round count (same
local fixture PIN, fresh salt; fixture file updated, `pinHashRounds: 16`).
Six access tests that pinned the 256/257/35700 contract shapes now derive
from `PIN_HASH_ROUNDS`; the ten-minute-budget guard is pinned at its new
(unreachable) worst case. Full AB suite 1677 OK.

**press89_echo38_rw** — `C:/work/press89_echo38_rw.L5X`
(sha256 `AE6691CC4DE801412BDFBD2F5DB5BE5E2AF4006DF317E5340124E14449E5B47D`),
delivered as `C:/work/press89_echo38_rw.ACD`
(sha256 `7BC42E2B4D785824AD2435C9B7A33781B4EC2177D85F25AE873D9C732411E1CB`),
offline-built clean on both targets; generated tag carries
`LoginPrehashRounds=16`. Owner download pending. Note: a download clears
volatile sessions, so the first HMI login after this download runs the
17-block hash once (~2 s class).

**Session persistence observed by the owner** ("echo_admin is logged by
default"): `SessionTimeout` policy defaults 0 = no auto-logout, and
volatile sessions survive HMI reconnects by design (cleared on download
and on Run entry). Set a session timeout via the HMI/engineering surface
when auto-logout is wanted.

# Fraktal/AB — command-mailbox binding handover (write path to the controller)

Copy the fenced text below into a coding-agent chat opened at the cloned
repository root **on the bench workstation** (`DESKTOP-07VCTIN`) that has Studio
5000 v33, the Logix Designer SDK and a route to the bench controller. Written
2026-09-21.

This is the sequel to
[`AB_HMI_GATEWAY_HANDOVER_PROMPT.md`](AB_HMI_GATEWAY_HANDOVER_PROMPT.md). That
one put the generic HMI in front of the controller **read-only**. The project
owner then authorized writes (2026-09-21) and chose the **controller-side
mailbox** approach: give the AB root Unit a real `HmiRequest`/`HmiResponse`
command mailbox, the way the TwinCAT oracle has one, rather than translating in
the gateway. This handover is that work. It is a controller-code change, so it
needs Studio and the bench, which is why it is a separate host from where the
gateway was built.

## Why this is a separate host

| Needed | Where it is |
|---|---|
| Studio 5000 v33, Logix Designer SDK, licences, the bench controller | **the bench** (`DESKTOP-07VCTIN`) |
| The read+write gateway and its §14 gate | already on `main` (`cb456a4`); runs anywhere with the venv |

The gateway already speaks the mailbox protocol natively and refuses writes
unless a bearer token is presented (Core §14). What is missing is the mailbox on
the controller for it to write to: `fraktal_ab_manifest.py` publishes
`MailboxId: 0` today ("no mailbox … exists yet").

## What already exists

* `fraktal_ab_gateway.py` on `main`: read methods proved live; `write`/
  `writeBatch` gated by a bearer token (`--write-token`), confined to
  `<root>/HmiRequest/<member>` (`permits_write`), with the monotonic
  `HmiRequest/Sequence` commit. Its `write_fn` is **unwired** — an authenticated,
  in-scope write is refused as "not connected" until this mailbox exists.
  Evidence: `Evidence/AB_HMI_GATEWAY_2026-09-21.md`,
  `Evidence/AB_HMI_GATEWAY_WRITE_ENABLE_2026-09-21.md`.
* The AB press demo already implements the *actions* a command drives: the mode
  owner (AUTO/MANUAL/HOME), the S16 command handshake, the operator decision, and
  per-module manual commands. This mailbox does **not** re-implement those; it
  routes to them.

---

```text
You are continuing the Fraktal/AB implementation on the bench. The objective is
one thing: give the AB root Unit a controller-resident HmiRequest/HmiResponse
command mailbox that mirrors the TwinCAT oracle, so the generic HMI can command
the press through the already-built read+write gateway. Read
`Specification/Fraktal_AB_Part_III.md` (§11.2, §11.2.1) and
`FraktalCore/PLC/Allen-Bradley/README.md` before touching this tree.

THE CONTRACT TO MIRROR (do not invent one)

The oracle defines it. Read these and match member names, types and ordinals
exactly — enum ordinals are the PLC transport contract:

  FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs/ST_HmiRequest.TcDUT
  FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs/ST_HmiResponse.TcDUT
  FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs/E_HmiRequestKind.TcDUT
  FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/BaseClasses/FB_UnitBase.TcPOU
    (_M_HandleHmiRequest, _M_AuditHmiAccepted)

  HmiRequest  : Kind(E_HmiRequestKind→DINT), TargetPath STRING(255),
                NameValue STRING(160), TextValue STRING(255), User STRING(32),
                Secret STRING(32), IntValue DINT, BoolValue BOOL,
                DurationMs UDINT, Sequence UDINT (commit marker, written last)
  HmiResponse : AckSequence UDINT, Accepted BOOL, Diagnostic STRING(255),
                Report ST_ReleaseReport, ConfigPage ST_ConfigPage
  Handshake   : when HmiRequest.Sequence changes, clear the response, dispatch
                Kind, then set HmiResponse.AckSequence := HmiRequest.Sequence.
                The HMI polls HmiResponse until AckSequence == its Sequence.

The client side is `FraktalCore/HMI/lib/data/opcua_repository.dart` (_request):
it writes Kind/TargetPath/NameValue/TextValue/User/Secret/IntValue/BoolValue/
DurationMs then Sequence last, and polls HmiResponse/{AckSequence,Accepted,
Diagnostic}. Re-read it; do not trust this summary alone.

WHAT AB SUPPORTS VS REFUSES

The press demo has real mechanisms for a subset of E_HmiRequestKind. Wire those;
refuse the rest with a localization-key Diagnostic and Accepted := FALSE, the
same shape the oracle uses for an unsupported request. This is honest: silence or
a fake accept is worse than a named refusal.

  Support now (route to existing AB mechanisms):
    SET_MODE(3)      -> the mode owner's mode select (IntValue = E_Mode ordinal)
    START(5)/STOP(6) -> the run/abort request the S16 chain already consumes
    OPERATOR_RESET(9)-> the reset request
    DECISION_ANSWER(10) -> the operator-decision answer (IntValue)
    MANUAL_COMMAND(11)  -> the per-module manual command (TargetPath + IntValue)
    STEP_REQUEST(13), SET_HOLD_RUN(14) -> the sequence step/hold controls
    LAMP_TEST(26)    -> the lamp-test request
  Refuse for now (owed work, named in the projection's `absent`):
    LOGIN/LOGOUT(1,2) access enforcement; SET_MODEL(4)/recipes; CONTROL_*(7,8)
    control power; RELEASE_*(15-17); RESET_OEE(18); *_CONFIG/*_CONFIG_SET(19,
    27-33); SHELVE/UNSHELVE_ALARM(20,21); FORCE_CHANNEL(22); QUERY_CONFIG(23) —
    unless you also do the config manifest; SET_ACCESS_LEVEL(24)/
    SET_SESSION_TIMEOUT(25); MANUAL_HELD(34).

BUILD IT (offline first, the AB way)

1. Contract. Add ST_HmiRequest/ST_HmiResponse-equivalent UDTs and the
   E_HmiRequestKind DINT ordinals to `fraktal_ab_declaration.py` /
   `fraktal_ab_generate.py`, emitted on the root Unit. Add the new mailbox
   contract to `Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json` and its
   Part III marker together (the frozen-contract gate checks they agree), and pin
   E_HmiRequestKind against the TwinCAT DUT the way
   `test_fraktal_ab_core_ordinals.py` pins E_Mode — this enum is exactly the kind
   AB got wrong once (AUTO/MANUAL swapped).
2. Handler. Generate the mailbox routine (mirror _M_HandleHmiRequest): detect a
   Sequence change against a retained last-sequence, clear the response, CASE on
   Kind to set the existing request tag(s), set Accepted/Diagnostic, then
   AckSequence := Sequence LAST. Secret must be cleared after sampling, as the
   oracle does. Keep it a pure request-routing layer; the PLC re-checks §7.6/§7.7.
3. Manifest. Publish a non-zero MailboxId in `fraktal_ab_manifest.py` and the
   mailbox's writable field rows; keep the access audit's rule (mailbox
   Read/Write, everything else read-only/None) — run `fraktal_ab_access_audit.py`.
4. Projection. Surface HmiResponse/{AckSequence,Accepted,Diagnostic} and
   HmiRequest/Sequence in `fraktal_ab_projection.py` so the HMI can seed the
   sequence and read acks. Add a projection unit-test case.
5. Gateway. Wire `write_fn` in `fraktal_ab_gateway.py` to map an HmiRequest
   browse path to the emitted controller tag and pylogix-Write it, verifying the
   serial immediately before the batch and restoring nothing (a mailbox write is
   the command). Extend `test_fraktal_ab_gateway.py` for the browse-path→tag map.
6. Offline fixtures. Follow the existing pattern (a disposable fixture generated
   and checked structurally, like `test_fraktal_ab_s16_fixture.py`) for the
   mailbox UDTs, the handler routine and the manifest rows. A probe that cannot
   fail is not evidence — pair each check with its fault.

VERIFY AND PROVE (bench only)

7. Regenerate the L5X. Import into a fresh isolated solution, Studio v33 Verify —
   require 0 errors / 0 warnings. Run the AB reference suite and the press parity
   harness; the mailbox must not perturb the read projection the HMI already
   renders.
8. CONFIRM THE LOADED BUILD BEFORE ANY LIVE WRITE. Check which build is on the
   controller (the read-only record notes the loaded build may pre-date the
   mode-ordinal correction). Do not issue SET_MODE until E_Mode is confirmed —
   download the corrected `press_modes.ACD` first if needed, and record the
   download in a dated evidence file (that download is itself a controller-
   changing operation needing current authorization and an exact target check).
9. Download the regenerated build (authorized, exact serial 7036B510 checked
   immediately before), then prove the HMI commands end to end through the
   gateway started with `--write-token`: mode change, start, stop, decision,
   manual command, lamp test. Record the request/ack sequence for each, the
   refusals for the unsupported Kinds, and a paired negative (an anonymous write
   refused by the §14 gate, a stale Sequence refused).
10. Write a dated evidence record in `Specification/AllenBradley/Evidence/`,
    update Part III §11.2, the README and the tool catalog, run the full suite,
    commit imperative and push.

HOUSE RULES WITH TEETH HERE

* Enum ordinals are the PLC contract — pin E_HmiRequestKind the way E_Mode is
  pinned, or a client sends LOAD_CONFIG_SET when it meant LAMP_TEST.
* Never perform a controller-changing operation (download, mode change, tag
  write, clock set, …) without current explicit authorization and an exact target
  check immediately before use. Prior authorization is historical and shall not
  be inferred. "Writes are allowed" is the project posture, not per-use consent.
* No anonymous write. The gateway's §14 gate (bearer token) stays on; a mailbox
  write must never be reachable anonymously.
* Acceptance is not publication, and silence is not parity. Prove the mailbox by
  reading the ack back, not by trusting the write returned true.
```

## Bench state at handover

Unchanged from `AB_HMI_GATEWAY_HANDOVER_PROMPT.md`: controller
`1769-L24ER-QB1B/A`, firmware `33.014`, serial `7036B510`, `192.168.100.89`. **The mode-ordinal
correction was downloaded on 2026-09-21** and is the loaded build, recorded in
[`Evidence/AB_MODE_ORDINAL_DOWNLOAD_2026-09-21.md`](Evidence/AB_MODE_ORDINAL_DOWNLOAD_2026-09-21.md),
so `Mode 0` means AUTO and step 8's precondition is met. Read §4 of that
record before leaning on it: the loaded build rests on the operator's
confirmation, because no read-only discriminator exists while the unit is
idle. The first live SET_MODE will be the first machine evidence of it.

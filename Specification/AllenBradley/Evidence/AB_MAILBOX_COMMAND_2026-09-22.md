# Fraktal/AB — commanding the press through the mailbox

**Result:** **The controller-resident command mailbox works on hardware.** All
six routed request kinds were accepted and individually acknowledged, all three
refusals named their reason, and `SET_MODE` changed the mode the controller
publishes — so a command reached the machine, not merely the mailbox. The
handover's flagged unknown, whether `pylogix` can write a user `StringFamily`
member, is now **measured rather than reasoned**, and it works. Two real defects
in the write path were found and fixed on the way.

**One narrowing, recorded plainly:** the client that issued these commands was
the mailbox harness, **not the Flutter HMI**. The HMI could not be used on this
workstation, for a measured environmental reason given in §7. Everything the
controller and the gateway do is identical whoever holds the socket; what is not
yet proved is the HMI's own transport.

**Date:** 2026-09-22

**Repository revision:** `79d0ad3`, plus this change.

**Scope:** an authorized command run against the bench test controller, which
has **nothing wired to it**. The project owner authorized writes (2026-09-21)
and authorized this run explicitly. Every write was forwarded by the gateway
only after it re-read the controller serial immediately before the write, and
the run ends with the bench restored to AUTO.

## 1. The target, checked before and after

```
serial        7036B510          serial_matches: true   (re-checked before every write)
ContentHash   86F37D3289C043E4  ConfigRevision 8844157 (the command-mailbox build)
address       192.168.100.89:44818
```

The harness refuses unless the controller publishes the expected content hash,
so a command cannot be issued to a build this evidence does not describe.

## 2. The assumption that was reasoned, and is now measured

`AB_COMMAND_MAILBOX_DOWNLOAD_2026-09-22.md` §6 left this owed, and the handover
named it as the thing most likely to break: `MailboxWriter` writes a string
argument as `LEN` plus `DATA` because these are user `StringFamily` types and
not the built-in `STRING`. The HMI writes five string members on every command.

`fraktal_ab_mailbox_probe.py` measured it in isolation, writing only arguments
and never `Sequence`, so nothing was committed:

```
FRK_Press_HmiRequest.Kind            := 0                      Success
FRK_Press_HmiRequest.TargetPath.LEN  := 0                      Success
FRK_Press_HmiRequest.TargetPath.DATA := 'Press.PressRam'       Success
FRK_Press_HmiRequest.TargetPath.LEN  := 14                     Success
  read back -> LEN 14, DATA 'Press.PressRam'
restored -> LEN 0, DATA zeroed
```

**It works, both the length-only form every routed kind uses and the
length-plus-data form.** This is a type-map fact about this baseline and belongs
with the S12 findings: a user `StringFamily` member is writable over CIP through
its `LEN` and `DATA` members, unlike ST string-literal *assignment*, which v33
rejects.

One thing the probe had to get right to be evidence at all: `DATA` is an array,
and an array read issued without an element count returns element zero and
*succeeds* — the defect recorded in `AB_MANIFEST_CONTROLLER_READ_2026-09-08` §4.
Read without a count, the readback would have meant nothing.

## 3. The six kinds that route

Each row is one commit — nine arguments then `Sequence` last — followed by
polling `HmiResponse` until `AckSequence` matched. The ack is the proof; the
write returning true is not.

| command | seq | ack | Accepted | Diagnostic | mode after |
|---|---|---|---|---|---|
| `SET_MODE(MANUAL)` | 1 | 1 | true | — | **1** |
| `START` | 2 | 2 | true | — | 1 |
| `STOP` | 3 | 3 | true | — | 1 |
| `OPERATOR_RESET` | 4 | 4 | true | — | 1 |
| `DECISION_ANSWER(1)` | 5 | 5 | true | — | 1 |
| `MANUAL_COMMAND` (unaddressed) | 6 | 6 | true | — | 1 |
| `SET_MODE(AUTO)` (restore) | 10 | 10 | true | — | **0** |

`SET_MODE` is the one that proves a command reached the machine rather than the
mailbox: `ModeActivePublished` moved to 1 and back to 0. The others are accepted
request routings whose downstream effect the press demo owns.

## 4. The refusals — named, not silent and not falsely accepted

| command | seq | Accepted | Diagnostic |
|---|---|---|---|
| `LAMP_TEST` | 7 | false | `project.mailbox.refused.no_signal_tower` |
| `MANUAL_COMMAND` addressed `Press.PressRam` | 8 | false | `project.mailbox.refused.target_not_addressable` |
| `SET_MODE(3)` — a mode this app never declared | 9 | false | `project.mailbox.refused.mode_not_declared` |

Each was acknowledged with its own sequence, so a refusal is distinguishable
from a command that silently did nothing. The keys arrive as numeric
localization keys from the controller and are resolved by the projection against
the controller's own Localization table read in the same snapshot.

The addressed `MANUAL_COMMAND` is the interesting one: the declared manual chain
jogs one module, so honouring an address it cannot target would be worse than
refusing — and it refused by name rather than jogging the wrong module.

## 5. The negatives at the gate

A gate that cannot refuse is not a gate. **None of these reached the
controller** — each was refused by the gateway before any write was forwarded.

* **Anonymous write refused.** A session with no bearer token: *"write requires
  authentication; anonymous or unauthenticated write is prohibited (Core §14)"*.
* **Off-mailbox write refused.** `Press/Status/State` is not an `HmiRequest`
  member: *"write path is outside the allowed HmiRequest scope"*.
* **Replayed sequence refused.** Committing sequence 0, which the controller had
  already answered: *"stale mailbox sequence: expected 1, got 0"*.

The final state confirms each request was consumed exactly once:
`HmiRequest/Sequence 10`, `HmiResponse/AckSequence 10`, mode back to AUTO.

## 6. Two defects found and fixed before the first command

Both were found while preparing this run, and both are in `79d0ad3`.

* **The write token was only settable in `argv`.** Core §14.2/§14.3 says a
  credential is a configuration or secret-store value, never a literal, and argv
  is world-readable in a process listing. The gateway now takes it from
  `FRAKTAL_GATEWAY_WRITE_TOKEN`, symmetric with the HMI's
  `FRAKTAL_GATEWAY_BEARER_TOKEN`, and the environment wins over the flag.
* **The sequence guard meant nothing on the first write.** The gateway never
  seeded its per-mailbox record, so after a restart the *first* commit carried
  no expectation at all and any sequence was accepted — including one the
  controller had already answered. The reference server seeds precisely to stop
  that replay. It now seeds from the controller before judging a commit, and
  does not walk backwards when the PLC has not yet scanned a commit the gateway
  has made. **The replay negative in §5 only refuses because of this fix**;
  before it, that replay would have been forwarded to the controller.

## 7. Why the Flutter HMI was not the client — measured, not assumed

The handover asks for the commands to be issued *from the HMI*. That could not
be done on this workstation, and the reason is environmental rather than a
defect in the binding.

The HMI refuses to attach a bearer token to a plaintext endpoint:
`IoGatewaySecurityOptions.validate` throws for any protected material on a
non-`wss://` URL, and an existing test pins it
(`test/opcua_security_options_test.dart`). That is correct behaviour — a
credential may not cross a plaintext hop — so the gateway gained TLS
(`--tls-cert`/`--tls-key`) and was served as `wss://` with a CA-signed loopback
certificate carrying an `IP:127.0.0.1` SAN.

TLS then failed to verify, and `tool/probe_gateway_tls.dart` was written to say
why rather than guess:

```
trusted CA loaded: ca.pem
certificate did NOT verify; reporting it anyway:
  subject: /CN=127.0.0.1
  issuer : /CN=Avast Web/Mail Shield Untrusted Root
           /O=Avast Web/Mail Shield
           /OU=generated by Avast Antivirus for untrusted server certificates
```

**The workstation's endpoint-security product intercepts TLS, including on
loopback and on an unprivileged high port**, and re-signs the server certificate
with its *Untrusted* root — the root it uses precisely because the original
certificate is not in the machine trust store. That root is not presented in the
chain and is not trustable by configuration, so no client-side setting fixes it.
The same interception is on record in this programme for breaking `pip`.

**What would prove it:** either add an endpoint-security exclusion for the
gateway's loopback port, or install the bench CA into the workstation trust
store so the product re-signs with its *trusted* root. Both are changes to the
workstation rather than to this repository, and both are the owner's decision;
neither was made here. `test/live_ab_command_test.dart` is committed and issues
exactly the commands above through the real `OpcUaRepository`, so it runs
unchanged on a host without TLS interception.

What this narrowing does and does not cost: the controller's handshake, its
routing, its refusals and the §14 gate are all proved above and are indifferent
to which client holds the socket. What is unproved is the HMI's own transport
and what an operator sees on screen when a command is refused.

## 8. Tests

* **AB Python tools:** `python -m unittest discover` — **583 tests, OK**,
  including the mailbox and gateway suites.
* **HMI:** `flutter analyze` clean; `flutter test` unchanged from `79d0ad3`
  (the two pre-existing failures under the locally installed Flutter 3.44.5 vs
  the CI-pinned 3.44.6 are unrelated to this work and are recorded in
  `AB_HMI_GATEWAY_2026-09-21.md` §8).
* **AB Phase-0 gate:** `fraktal_ab_phase0_gate.py` needs Studio 5000, which is
  on the bench workstation and not here. It was **not run** and is not recorded
  as a pass.

## 9. Still owed

* The HMI as the commanding client (§7), pending a workstation decision.
* The §11.2.1 write-surface gap is **unchanged and still live**: the contract
  structures and the routed request tags remain externally `Read/Write`, so a
  CIP client can still write `FRK_Press_RunRequest` directly and never meet the
  bearer gate. This run did not close it and did not widen it. The fork — the
  evidence harnesses command through the mailbox, or they keep a declared
  harness-only writable surface recorded as a narrowing — is still the owner's,
  and `test_fraktal_ab_mailbox.py::test_the_mailbox_does_not_yet_have_the_write_surface_to_itself`
  still asserts the gap on purpose.
* Everything the refusals name: access enforcement, recipes, control power,
  release reports, OEE, the config manifest, the event core, physical I/O, a
  signal tower, step and hold-run control.

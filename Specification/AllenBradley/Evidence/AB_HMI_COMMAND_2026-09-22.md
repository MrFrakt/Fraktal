# Fraktal/AB — the generic HMI commands the press

**Result:** **The unmodified generic Fraktal HMI commands an Allen-Bradley press
through the controller-resident mailbox.** Every command was issued by the real
`OpcUaRepository` over an authenticated `wss://` session, acknowledged by the
controller, and — where the binding does not support a kind — **refused with a
reason the HMI received and surfaced** rather than a silent failure or a false
success.

This closes the one narrowing left open by
[`AB_MAILBOX_COMMAND_2026-09-22.md`](AB_MAILBOX_COMMAND_2026-09-22.md) §7, where
the commands were proved from the mailbox harness because the Flutter HMI could
not establish a verified TLS session on this workstation. It does not replace
that record: the controller behaviour, the measured `StringFamily` write and the
two defects fixed there all still stand.

**Date:** 2026-09-22

**Repository revision:** `d4ebb3c`, plus this change.

**Scope:** an authorized command run against the bench test controller, which
has **nothing wired to it**. The gateway re-read the controller serial
immediately before every write it forwarded, and the run ends with the bench
restored to AUTO.

## 1. What had to change, and what did not

Nothing in the binding changed. What changed was the workstation.

The HMI refuses to attach a bearer token to a plaintext endpoint, so the gateway
was served as `wss://` with a CA-signed loopback certificate carrying an
`IP:127.0.0.1` SAN. TLS then failed to verify because the workstation's
endpoint-security product intercepts TLS on loopback and re-signs the
certificate with its own *Untrusted* root — measured, not guessed, by
`tool/probe_gateway_tls.dart`. **The owner added an interception exception for
the gateway's port.** The same probe then reported the real chain:

```
trusted CA loaded: ca.pem
connected.
  subject: /CN=127.0.0.1
  issuer : /CN=Fraktal Bench Loopback CA
```

That is the whole difference. The gateway, the mailbox and the controller are
byte-identical to the previous record.

## 2. The HMI rendering, then commanding

```
rendering: Press mode=auto state=ready children=3
mailbox as found: seq=10 ack=10 accepted=true diag=""
```

Sequence 10 is where the harness run left it, and the HMI seeded its own
numbering from the controller rather than from zero — which is the behaviour
that makes a replay impossible to issue by accident.

| command | seq | ack | HMI returned | Accepted | Diagnostic |
|---|---|---|---|---|---|
| `SET_MODE(manual)` | 11 | 11 | true | true | — |
| `START` | 12 | 12 | true | true | — |
| `STOP` | 13 | 13 | true | true | — |
| `OPERATOR_RESET` | 14 | 14 | true | true | — |
| `DECISION_ANSWER(1)` | 15 | 15 | true | true | — |
| `MANUAL_COMMAND` (unaddressed) | 16 | 16 | true | true | — |
| `LAMP_TEST` | 17 | 17 | **false** | false | `project.mailbox.refused.no_signal_tower` |
| `MANUAL_COMMAND` addressed | 18 | 18 | **false** | false | `project.mailbox.refused.target_not_addressable` |
| `SET_MODE(changeover)` | 19 | 19 | **false** | false | `project.mailbox.refused.mode_not_declared` |
| `SET_MODE(auto)` (restore) | 20 | 20 | true | true | — |

`SET_MODE(manual)` moved `ModeActivePublished` to 1 and the restore returned it
to 0, so a command from the HMI reached the machine and not merely the mailbox.

**The HMI reports what the controller decided.** Each row asserts that the
repository's return value equals `Accepted`: a refused command returns `false`
to the caller, so an operator control cannot render success for a command the
machine declined. The HMI's own session log carries the reason with it:

```
stage=opcua-request-ack kind=lampTest sequence=17 accepted=false
  diagnostic=project.mailbox.refused.no_signal_tower
```

The keys arrive from the controller as numeric localization keys and are
resolved by the projection against the controller's own Localization table read
in the same snapshot, so a refusal survives translation rather than shipping one
hard-coded language.

## 3. The §14 gate, in the posture it is meant to run in

This is the first run where the gate did the job it was designed for rather than
a proxy for it: a bearer token, carried over TLS, from the real client.

* The token reached the gateway from `FRAKTAL_GATEWAY_BEARER_TOKEN` and the
  gateway took its own from `FRAKTAL_GATEWAY_WRITE_TOKEN` — neither on a command
  line (Core §14.2/§14.3).
* The gateway logged `stage=identity-verified serial=7036B510` and re-checked
  the serial immediately before forwarding writes.
* Final state: `HmiRequest/Sequence 20`, `HmiResponse/AckSequence 20`,
  `ModeActivePublished 0`, diagnostic cleared. Ten requests, ten
  acknowledgements, each consumed exactly once.

The anonymous, off-mailbox and replayed-sequence negatives are unchanged from
`AB_MAILBOX_COMMAND_2026-09-22.md` §5 and were not re-run here; they are
properties of the gateway and do not depend on which client holds the socket.

## 4. Reproducing it

```
# gateway, with the write token in the environment:
export FRAKTAL_GATEWAY_WRITE_TOKEN=...
python fraktal_ab_gateway.py 192.168.100.89 --expect-serial 7036B510 \
    --port 39443 --tls-cert server.pem --tls-key server-key.pem
# HMI:
export FRAKTAL_AB_GATEWAY=wss://127.0.0.1:39443/fraktal
export FRAKTAL_GATEWAY_BEARER_TOKEN=...      # the same value
export FRAKTAL_WSS_TRUSTED_CA=ca.pem
flutter test --run-skipped -t live test/live_ab_command_test.dart
```

On a host whose endpoint security intercepts TLS, add an exception for that port
first; `dart run tool/probe_gateway_tls.dart 127.0.0.1 39443 ca.pem` says which
certificate is really being offered, which is the difference between a
misconfigured trust store and an intercepted one.

## 5. Still owed

* **The §11.2.1 write-surface gap**, unchanged. The routed request tags and the
  contract structures remain externally `Read/Write`, so a CIP client can still
  write `FRK_Press_RunRequest` directly and never meet the bearer gate. The
  owner has chosen to close it by routing the harnesses through the mailbox;
  that work is scoped in §6 below and is not done here.
* Everything the refusals name: access enforcement, recipes, control power,
  release reports, OEE, the config manifest, the event core, physical I/O, a
  signal tower, and step/hold-run control.
* What an operator sees **on screen** for a refused command. This run proves the
  HMI receives the reason and reports the refusal to its caller; it does not
  photograph a panel. A GUI walkthrough is an operator step.

## 6. Scope of the write-surface close

`writable_inputs` splits in two, and only one half is commandable:

* **Operator commands, and exactly the six kinds the mailbox routes:**
  `RunRequest`, `AbortRequest`, `ResetRequest`, `ModeRequest`, `DecisionAnswer`,
  `JogCommand`. These can move behind the mailbox.
* **Not commands:** `Fault<Module>` / `Hold<Module>` injections, the simulated
  sensor inputs (two-hand, part-present, air-ok) and the rendition selector. A
  command mailbox cannot carry "the door sensor went true"; that is the
  simulated world, not an operator action, and giving it a request kind would
  invent a command no operator issues.

So a faithful close moves the six and scopes the remainder to a declared test
build rather than removing it, which would delete the fifteen-row press matrix
rather than secure it. Changing `writable_inputs` regenerates the L5X, so
Studio Verify and a download are required to prove it — bench work.

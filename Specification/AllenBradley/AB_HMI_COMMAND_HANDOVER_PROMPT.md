# Fraktal/AB — HMI command handover prompt (prove the mailbox from the HMI)

Copy the fenced text below into a coding-agent chat opened at the cloned
repository root **on the PC that has the Flutter/Dart SDK** and can reach the
bench controller. Written 2026-09-22.

It is the sequel to
[`AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md`](AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md),
whose build steps 1–7 are done and on `main`. What is left is steps 8–10: prove
the command path from the real HMI, on hardware, and record it. That needs the
HMI running, which is why it moves hosts again.

## State at handover

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, firmware `33.014`, serial `7036B510`, `192.168.100.89:44818` |
| Loaded build | **the command-mailbox build**, machine-verified by `ContentHash 86F37D3289C043E4` / `ConfigRevision 8844157` — see [`Evidence/AB_COMMAND_MAILBOX_DOWNLOAD_2026-09-22.md`](Evidence/AB_COMMAND_MAILBOX_DOWNLOAD_2026-09-22.md) |
| `Mode 0` | **means AUTO** (Core `E_Mode`), proved by the above |
| Mailbox | live and idle: `Sequence 0`, `AckSequence 0`, `Accepted false`, empty diagnostic |
| Commands issued so far | **none** |
| Repo | `main`, suite 578 tests, Studio v33 Verify 0/0 |

## Prerequisites

* Flutter/Dart SDK matching `FraktalCore/HMI/pubspec.yaml` (`>=3.0.0 <4.0.0`).
* Python 3.10+ and a venv **outside the repo** with `pylogix==1.1.5`, plus
  `FraktalCore/PLC/Allen-Bradley/tools/requirements-gateway.txt`.
* Network reach to `192.168.100.89`, or run the gateway on a host that has it.

---

```text
You are continuing the Fraktal/AB implementation. The objective is one thing:
prove the generic Fraktal HMI can COMMAND the Allen-Bradley press through the
controller-resident mailbox, and record honestly what works and what does not.
Read `Specification/Fraktal_AB_Part_III.md` (11.2, 11.2.1),
`FraktalCore/PLC/Allen-Bradley/README.md`, and the two evidence records
`Evidence/AB_COMMAND_MAILBOX_DOWNLOAD_2026-09-22.md` and
`Evidence/AB_HMI_GATEWAY_2026-09-21.md` before touching this tree.

WHAT IS ALREADY BUILT AND PROVED

* The generic HMI already RENDERS this controller read-only, through
  fraktal_ab_gateway.py serving fraktal_ab_projection.py over the HMI's own
  fraktal.opcua.gateway.v1 protocol. No AB-specific screens exist or are wanted.
* The root Unit has an HmiRequest/HmiResponse mailbox mirroring the TwinCAT
  oracle, generated from the declaration. It is on the controller now.
* The gateway's write path is connected: MailboxWriter maps
  <root>/HmiRequest/<member> to FRK_Press_HmiRequest.<member> and refuses
  anything else, behind the Core 14 bearer token (--write-token) and
  permits_write.
* 578 tests pass. SDK import 0/0, Studio v33 Verify 0/0.

WHAT IS NOT PROVED, AND IS YOUR JOB

Nothing has ever written to the mailbox. Every one of these is untested on
hardware:

* the handshake end to end - write arguments, commit Sequence last, poll until
  AckSequence matches, read Accepted and Diagnostic;
* pylogix writing LEN/DATA to a user StringFamily member. This is REASONED, NOT
  MEASURED. The HMI writes five string members on every command (usually
  empty), so if this does not work, nothing works. It is the same class of
  assumption that string-literal assignment in ST turned out to violate: the
  SDK accepted 21 of those at 0 errors and Studio Verify rejected exactly 21.
  Expect to find something here and record it.
* the refusals, the ack ordering, and the 14 negatives.

THE SIX KINDS THAT ROUTE, AND THE TWENTY-EIGHT THAT DO NOT

Routed: SET_MODE(3), START(5), STOP(6), OPERATOR_RESET(9), DECISION_ANSWER(10),
MANUAL_COMMAND(11) - and MANUAL_COMMAND only with an EMPTY TargetPath, because
the declared manual chain jogs one module and honouring an address it cannot
target would be worse than refusing.

Everything else refuses by name with a numeric localization key. Note that
STEP_REQUEST, SET_HOLD_RUN and LAMP_TEST are among the refusals: the previous
handover listed them as routable and that was wrong - there is no step-request
tag and no signal tower, and the Hold* tags are the S16 per-module hold
injections the evidence harness uses, not a sequence hold-run control.

The controller answers with a NUMERIC key, not a string, because Logix v33 ST
cannot assign a string literal to a StringFamily member. fraktal_ab_projection
resolves it against the controller's own Localization table read in the same
snapshot. Do not resolve it anywhere else: a numeric key means something only
within the revision that published it.

YOUR TASK

1. Start the gateway with --write-token and --expect-serial 7036B510. Without a
   token there is no writer at all and it stays read-only.
2. Run the real HMI against it. Issue, from the HMI: a mode change, start, stop,
   an operator reset, a decision answer, and a manual command. Record the
   request/ack sequence for each and what the operator actually sees.
3. Issue at least one refused kind and show the HMI renders the refusal reason,
   not a silent failure and not a false success.
4. Paired negatives, because a gate that cannot refuse is not a gate:
   - an anonymous write (no bearer token) must be refused by the 14 gate;
   - a replayed or stale Sequence must be refused;
   - a write to something that is not an HmiRequest member must be refused;
   - a MANUAL_COMMAND with a non-empty TargetPath must be refused by name.
5. Write a dated evidence record in Specification/AllenBradley/Evidence/. Include
   the controller identity and serial, the resolved dependency versions, and for
   each command the sequence, the ack, Accepted and the diagnostic key. Record
   what the HMI did NOT do as plainly as what it did.
6. Update Part III 11.2, the AB README and the tool catalog. Run the full suite.
   The AB gate (fraktal_ab_phase0_gate.py) needs Studio and will not run on this
   host - say so rather than recording a pass around it.
7. Commit imperative and push.

THE DEFERRED DECISION YOU WILL RUN INTO

The mailbox is NOT yet the only externally writable surface. The contract
structures and the routed request tags are still Read/Write, so a CIP client can
write FRK_Press_Unit or FRK_Press_RunRequest directly and never meet the bearer
gate. AB 11.2.1 wants mailbox Read/Write, public Read Only, everything else
None. The user deferred this deliberately on 2026-09-21 to get the mailbox
built; it is now live rather than theoretical, because there is a gated path
worth going around.

Closing it breaks the evidence harnesses - fraktal_ab_press_execute.py drives
its fifteen-row matrix by writing FRK_Press_RunRequest directly. The fork is
either the harnesses command through the mailbox, or they keep a declared
harness-only writable surface recorded as a narrowing. ASK THE USER. Do not
decide it yourself, and do not quietly leave it either:
test_fraktal_ab_mailbox.py::test_the_mailbox_does_not_yet_have_the_write_surface_to_itself
asserts the gap on purpose so closing it breaks that test rather than passing
unnoticed.

HOUSE RULES WITH TEETH HERE

* A tag write is a controller-changing operation. "Writes are allowed" is the
  project posture, not per-use consent: get current explicit authorization and
  do an exact target check immediately before use. Prior authorization is
  historical and shall not be inferred.
* No anonymous write, ever. The 14 bearer gate stays on.
* Acceptance is not publication and silence is not parity. Prove a command by
  reading the ack and the resulting machine state back, never by trusting that
  the write returned true.
* A probe that cannot fail is not evidence. Pair every check with its fault.
* Past evidence is append-only. Add a dated record; do not rewrite one.
* Enum ordinals are the PLC contract. test_fraktal_ab_core_ordinals.py reads the
  TwinCAT DUTs directly and pins E_Mode, E_ExecState and all 35
  E_HmiRequestKind ordinals. It exists because AB shipped AUTO and MANUAL
  swapped, which an HMI would have rendered as the wrong mode.
* If something cannot be proved on this host, record the narrowing and say what
  would prove it. Do not mark anything PASS around a gap.
```

## If the mailbox does not work

The most likely failure is the string write, and the fallback is already
half-designed: every kind this binding routes takes **no** string content, so a
`MailboxWriter` that wrote only the scalar members and set each string's `LEN`
to zero would serve all six routed kinds. If `pylogix` cannot write `LEN`
either, the remaining option is a `StringFamily` member written as a whole
structure. Record which was needed — it is a type-map fact about this baseline,
and it belongs with the S12 findings.

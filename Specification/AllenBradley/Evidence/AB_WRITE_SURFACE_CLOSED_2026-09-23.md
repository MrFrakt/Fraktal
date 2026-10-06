# Fraktal/AB — the mailbox is the only way in, and the latch is gone

**Result:** **AB §11.2.1 is met on the controller, and the latching defect is
fixed and proved by machine state.** A CIP client can no longer see, let alone
write, any tag the mailbox routes into; the mailbox is the only command surface;
and after `STOP` then `OPERATOR_RESET` the press stays stopped instead of
re-arming itself. The fifteen-row matrix now commands through the mailbox and
passes on three consecutive runs.

**Date:** 2026-09-23

**Repository revision:** `75da126`; the loaded build is `press_closed.ACD`,
identified on the controller by `ContentHash 71448732E842290F` /
`ConfigRevision 7423111`.

**Scope:** one authorized run of tag writes on serial `7036B510`, confined to
the `FRK_Press_HmiRequest` members and the ten simulated-plant inputs, with the
serial checked immediately before and restore in `finally`. No download, mode
switch at the keyswitch, fault clear, clock set, firmware, controller-network,
safety or SD-card operation.

## 1. The close, proved by refusal

Every request tag the mailbox routes into is `ExternalAccess="None"`, which
removes it from the CIP namespace entirely — a client cannot even read it:

```
read  FRK_Press_RunRequest        Path segment error
read  FRK_Press_AbortRequest      Path segment error
read  FRK_Press_ResetRequest      Path segment error
read  FRK_Press_ModeRequest       Path segment error
read  FRK_Press_DecisionAnswer    Path segment error
read  FRK_Press_JogCommand        Path segment error

write FRK_Press_RunRequest   1    Path segment error   REFUSED
write FRK_Press_AbortRequest 1    Path segment error   REFUSED
write FRK_Press_ModeRequest  1    Path segment error   REFUSED
```

With the controls that make it a probe rather than a broken connection:

```
read  FRK_Press_HmiRequest.Sequence   Success, 0      (the mailbox is reachable)
read  FRK_Press_TwoHand               Success, 0      (the plant is reachable)
```

An access audit of the generated project reports `Conforms: true` over 44 tags,
with `CommandSurface` a single entry — `FRK_Press_HmiRequest`.

## 2. The latch, proved by state rather than by acknowledgement

The request tags are unreadable now, so the deassert **cannot** be checked
directly. That is the right shape: it has to be proved by what the machine does.

The decisive sequence is `STOP` then `OPERATOR_RESET`. On the latching build
`RunRequest` stayed high, so the instant the reset cleared `Aborted` the run
latch would re-arm and `Running` would return to 1 on its own.

| command | accepted | Running | Aborted | Error | Step |
|---|---|---|---|---|---|
| `OPERATOR_RESET` (to idle) | true | 0 | 0 | 0 | 0 |
| `SET_MODE` AUTO | true | 0 | 0 | 0 | 0 |
| `START` | true | **1** | 0 | 0 | **100** |
| `STOP` | true | **0** | **1** | 0 | 0 |
| `OPERATOR_RESET` | true | **0** | **0** | 0 | 0 |
| *(settled 400 ms later)* | — | **0** | 0 | 0 | 0 |

`Running` stays 0 through the reset and stays 0 four hundred milliseconds after
it. The run level was lowered by `STOP`, and the one-shots were lowered by the
controller.

`Step 100` after `START` is worth noting on its own: 100 is the AUTO chain's
first working step, so the machine ran AUTO for mode ordinal 0. That is the
**first machine evidence of the mode-ordinal correction** — the earlier download
record could only rest on the operator's confirmation, because nothing readable
distinguished the builds.

## 3. Refusals, by name

Each unsupported kind answers with its own localization key rather than a
generic failure, and none of them moved the machine:

| request | accepted | `Diagnostic` |
|---|---|---|
| `CONTROL_ON` | false | `project.mailbox.refused.no_control_power` |
| `LAMP_TEST` | false | `project.mailbox.refused.no_signal_tower` |
| `MANUAL_COMMAND` with `TargetPath="Press.Door"` | false | `project.mailbox.refused.target_not_addressable` |
| `SET_MODE` with `IntValue=3` (CHANGEOVER, undeclared) | false | `project.mailbox.refused.mode_not_declared` |
| kind `99` | false | `project.mailbox.refused.unknown_kind` |

`SET_MODE 3` matters: `CHANGEOVER` is a real `E_Mode` ordinal that this
application does not declare. It is refused by name rather than clamped, so a
client asking for a mode the press does not have is told, instead of quietly
landing in AUTO.

## 4. Replay

Re-issuing sequence 10 — carrying a `START` — changed nothing:

```
AckSequence stayed at 10     Running 0   Aborted 0   Step 0
```

The handler consumes a request only when `Sequence` changes, so a replayed
command is not a second command.

## 5. The matrix, commanding through the mailbox

`fraktal_ab_press_execute.py` drove its fifteen rows through the mailbox over
CIP, three consecutive times:

| run | rows | all passed | sequence seed | disarm |
|---|---|---|---|---|
| 1 | 15 | yes | 12 | cleared |
| 2 | 15 | yes | 62 | cleared |
| 3 | 15 | yes | 112 | cleared |

The seeds rising 12 → 62 → 112 are themselves evidence: each run seeds above
what the controller has already acknowledged, so the first command of run 2 was
not refused as a replay of run 1. A harness that restarted its numbering at 1
would have had every run after the first silently ignored.

**The harness no longer supplies a deassert.** It used to write `1` then `0` on
every one-shot, which is exactly what hid the latch: the controller never
lowered them, and nobody noticed because the client always did. It now writes
the raise only, and the controller lowers its own.

## 6. Bench state at the end

```
unit     Mode 0 (AUTO)  Step 0  Running 0  Complete 0  Aborted 0  Error 0  Held 0
plant    all ten inputs 0, including RenditionSelect
mailbox  Sequence 162, AckSequence 162   (matched: nothing outstanding)
```

## 7. What this does not cover

* **The gateway was not in the path.** These commands went over CIP directly,
  because the harness is apparatus rather than an operator. The Core §14 bearer
  gate is proved in
  [`AB_HMI_COMMAND_2026-09-22.md`](AB_HMI_COMMAND_2026-09-22.md), not here.
* **No HMI was driven.** The generic HMI commanding this closed build is not
  re-proved; only the controller-side contract it depends on is.
* **The plant is still writable**, and that is a property of a demo with no I/O
  card. A real application takes those ten signals from hardware and declares
  none. It is asserted by
  `test_the_simulated_plant_is_the_remaining_writable_surface` so it cannot
  quietly grow.

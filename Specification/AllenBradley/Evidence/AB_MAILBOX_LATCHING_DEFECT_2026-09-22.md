# Fraktal/AB — the mailbox latches the requests it drives

**Result:** **Every command the HMI issued was accepted and acknowledged, and
the press was left unusable.** After `START`, `STOP` and `OPERATOR_RESET`, the
bench controller held `RunRequest`, `AbortRequest`, `ResetRequest` and
`JogCommand` all at 1 and the Unit reported `Aborted`. The mailbox handler sets
each request and nothing ever clears it.

This is the failure mode "acceptance is not publication" exists to catch: ten
acknowledgements, `Accepted = true` on every routed kind, and a machine that had
been driven into a latched abort the whole time.

**Date:** 2026-09-22

**Repository revision:** `56ff289`, found while closing the §11.2.1 write surface.

**Scope:** read-back of the bench after the command runs recorded in
[`AB_MAILBOX_COMMAND_2026-09-22.md`](AB_MAILBOX_COMMAND_2026-09-22.md) and
[`AB_HMI_COMMAND_2026-09-22.md`](AB_HMI_COMMAND_2026-09-22.md), plus an
authorized cleanup write to restore the bench. The controller is the bench test
unit with nothing wired to it, serial checked before the cleanup.

## 1. What was found

```
FRK_Press_RunRequest       1        FRK_Press_Unit.Aborted    1
FRK_Press_AbortRequest     1        FRK_Press_Unit.Running    0
FRK_Press_ResetRequest     1        FRK_Press_Unit.Error      0
FRK_Press_JogCommand       1        FRK_Press_Unit.Mode       0
FRK_Press_DecisionAnswer   1        FRK_Press_Unit.Step       0
```

## 2. Why

The generated logic treats these as **levels**, not pulses. Each is copied into
the Unit context every scan and tested as a level:

```
FRK_Press_Unit.RunRequest := FRK_Press_RunRequest;
IF (Ctx.RunRequest <> 0) AND (Ctx.Error = 0) AND (Ctx.Aborted = 0)
IF Ctx.RunRequest = 0 THEN            (* waits for the deassert that never comes *)
IF Ctx.AbortRequest <> 0 THEN
IF Ctx.ResetRequest <> 0 THEN
```

The mailbox handler only ever raises them:

```
START:          FRK_Press_RunRequest   := 1;
STOP:           FRK_Press_AbortRequest := 1;
OPERATOR_RESET: FRK_Press_ResetRequest := 1;
MANUAL_COMMAND: FRK_Press_JogCommand   := 1;
```

Nothing lowers them. The oracle does not have this problem because
`_M_HandleHmiRequest` calls methods — `Start()`, `Stop()` — rather than driving
a tag that something else samples. The AB binding maps the same commands onto
level-sensitive tags, and the mapping lost the deassert.

**It was hidden until now** because those tags were externally writable: the
HMI and `fraktal_ab_press_execute.py` both wrote `1` and then `0`, supplying the
deassert the controller never performs. The command mailbox inherited the raise
and not the lower.

## 3. Why it becomes blocking

Closing the §11.2.1 write surface makes the mailbox the **only** writer of these
tags. A build carrying both that close and this handler would:

* latch `AbortRequest` on the first `STOP`, leaving the Unit `Aborted`;
* leave `ResetRequest` asserted, so the unit re-resets continuously;
* never satisfy `IF Ctx.RunRequest = 0`, so any step waiting on the deassert
  stalls;
* and offer **no way to recover**, because nothing outside the controller may
  write those tags any more. The only exit would be another download.

So the write-surface close and this defect must not reach a controller in the
same build. The close is in the repository; the fix is not, and the download is
gated on it — see
[`AB_STUDIO_WRITE_SURFACE_HANDOVER_PROMPT.md`](../AB_STUDIO_WRITE_SURFACE_HANDOVER_PROMPT.md).

## 4. The bench was restored

Authorized cleanup, serial `7036B510` verified immediately before:

```
FRK_Press_RunRequest 0   FRK_Press_AbortRequest 0   FRK_Press_ResetRequest 0
FRK_Press_DecisionAnswer 0   FRK_Press_JogCommand 0
FRK_Press_Unit.Aborted 0   Error 0   Running 0   Mode 0 (AUTO)
```

The currently loaded build still exposes those tags, which is what made the
cleanup possible. That will not be true of the next build.

## 5. Pinned so it cannot be forgotten

`test_fraktal_ab_mailbox.py::OneShotRequestTests` asserts the defect on purpose:
it requires that the handler raises each one-shot and does **not** contain a
matching deassert. Fixing the handler breaks that test, which is the point — it
has to be replaced by the assertion that every one-shot drops again.

A second test pins the reason it matters: no command tag is externally writable,
so nothing outside the controller can paper over a latched request.

## 6. What a fix has to get right

Not attempted here, because it is generated controller logic and cannot be
trusted without Studio Verify:

* **One-shot requests must drop.** `AbortRequest`, `ResetRequest` and
  `JogCommand` need to be high for long enough for the mode owner to sample
  them and then return to 0 — a pulse, not a level.
* **`RunRequest` is genuinely a level** and should stay one: `START` raises it,
  and `STOP` should lower it as well as raising `AbortRequest`. A `STOP` that
  leaves `RunRequest` high is a contradiction the controller has to resolve.
* **Scan order matters.** The mailbox routine must run before the Unit AOI in
  the same scan, or a one-scan pulse is cleared before the thing that consumes
  it ever sees it. Whatever the fix, the emitted routine order is part of it.
* **It must be proved by state, not by acknowledgement.** This defect passed
  every ack check there is. The re-proof has to read `Unit.Running`,
  `Unit.Aborted` and the step back, not `AckSequence`.

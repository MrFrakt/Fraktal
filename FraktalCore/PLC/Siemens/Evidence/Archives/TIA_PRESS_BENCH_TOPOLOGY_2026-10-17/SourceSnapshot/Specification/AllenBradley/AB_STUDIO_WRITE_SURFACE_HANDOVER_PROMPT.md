# Fraktal/AB — Studio 5000 handover: close the write surface, and fix the latch

Copy the fenced text below into a coding-agent chat opened at the cloned
repository root **on the bench workstation** (`DESKTOP-07VCTIN`) that has Studio
5000 v33, the Logix Designer SDK and a route to the bench controller. Written
2026-09-22.

It follows
[`AB_HMI_COMMAND_HANDOVER_PROMPT.md`](AB_HMI_COMMAND_HANDOVER_PROMPT.md), whose
work is done: the mailbox is proved on hardware and the generic HMI commands the
press through it. This handover carries the two things that came out of that and
need Studio — a controller-logic fix, and the download that closes AB §11.2.1.

> **Do not download the current `main` build to a controller until step 1 is
> done.** The write-surface close and the latching defect must not reach a
> controller in the same build. See
> [`Evidence/AB_MAILBOX_LATCHING_DEFECT_2026-09-22.md`](Evidence/AB_MAILBOX_LATCHING_DEFECT_2026-09-22.md).

## State at handover

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, fw `33.014`, serial `7036B510`, `192.168.100.89:44818` |
| Loaded build | the **command-mailbox** build, `ContentHash 86F37D3289C043E4` / `ConfigRevision 8844157` — still has the open write surface |
| Bench state | restored: all request levels 0, `Unit.Aborted` 0, mode AUTO |
| Repo `main` | the write surface is **closed in generation**: `ContentHash 71448732E842290F` / `ConfigRevision 7423111`. Not downloaded. |
| Suite | 586 tests, OK |

The two hashes differ, so a client can tell which build is loaded by reading the
manifest — the property the mode-ordinal download did not have.

---

```text
You are continuing Fraktal/AB on the bench. Two jobs, in this order, and the
first gates the second. Read Specification/Fraktal_AB_Part_III.md (11.2,
11.2.1), FraktalCore/PLC/Allen-Bradley/README.md, and these three evidence
records before touching the tree:

  Evidence/AB_MAILBOX_LATCHING_DEFECT_2026-09-22.md   <- start here
  Evidence/AB_MAILBOX_COMMAND_2026-09-22.md
  Evidence/AB_HMI_COMMAND_2026-09-22.md

1. FIX THE LATCH. This is a controller-logic defect and it blocks everything
   else.

   The mailbox handler raises the request tags it routes into and never lowers
   them. The generated logic treats them as levels - each is copied into the
   Unit context every scan and tested with IF Ctx.RunRequest <> 0 - so after a
   START/STOP/OPERATOR_RESET run the bench was left with RunRequest,
   AbortRequest, ResetRequest and JogCommand all at 1 and the Unit reporting
   Aborted. It was invisible until now because those tags were externally
   writable and every client wrote 1 then 0, supplying a deassert the controller
   never performed.

   What a fix has to get right:
   * the one-shots (AbortRequest, ResetRequest, JogCommand) must be high long
     enough for the mode owner to sample them and then return to 0;
   * RunRequest is genuinely a level: START raises it and STOP must LOWER it as
     well as raising AbortRequest, because a STOP that leaves RunRequest high is
     a contradiction the controller then has to resolve;
   * scan order is part of the fix. The mailbox routine must run before the Unit
     AOI in the same scan, or a one-scan pulse is cleared before the thing that
     consumes it sees it. Check the emitted JSR order, do not assume it;
   * the oracle does not have this problem because _M_HandleHmiRequest calls
     Start() and Stop() rather than driving a tag something else samples. You are
     re-creating that semantics on level tags; say in the code why the shape
     differs.

   test_fraktal_ab_mailbox.py::OneShotRequestTests asserts the defect ON PURPOSE.
   Your fix will break it. Replace it with the assertion that every one-shot
   drops again - do not delete it.

2. DOWNLOAD THE CLOSED BUILD AND RE-PROVE.

   main already closes AB 11.2.1 in generation:
   * every request tag the mailbox routes into (RunRequest, AbortRequest,
     ResetRequest, ModeRequest, DecisionAnswer, JogCommand) is ExternalAccess
     None and is no longer described in the manifest - it is the mailbox's
     output, not public data;
   * the contract structures (FRK_Press_Unit, FRK_Press_Chart, the Ctx tags, the
     ParCfg record) are Read Only;
   * FRK_Press_HmiRequest stays Read/Write and is the only command surface;
   * what remains writable is the simulated plant and the evidence apparatus -
     the sensors, the Fault/Hold injections and the rendition selector. That is a
     property of a DEMO with no physical I/O, not of the binding: a real
     application takes those from a card and this list is empty for it. It is
     asserted by test_the_simulated_plant_is_the_remaining_writable_surface so it
     cannot quietly grow.

   Steps: regenerate the L5X, import into a fresh isolated solution, Studio v33
   Verify - require 0 errors / 0 warnings - run fraktal_ab_access_audit.py
   against the generated project and require Conforms: true, then download with
   an exact serial check immediately before.

3. RE-PROVE BY STATE, NOT BY ACKNOWLEDGEMENT.

   The latching defect passed every ack check there is: ten acknowledgements,
   Accepted true on every routed kind, and a latched abort the whole time. So the
   re-proof reads the machine back:
   * run fraktal_ab_mailbox_execute.py --arm-writes and, after each command, read
     Unit.Running, Unit.Aborted, Unit.Error and the step - not just AckSequence;
   * confirm every request tag returns to 0 after its command;
   * confirm a CIP write to FRK_Press_RunRequest is now REFUSED by the
     controller. That is the paired negative for the whole close, and without it
     you have not shown the surface is shut.

4. FIX THE HARNESSES. fraktal_ab_press_execute.py drives its fifteen-row matrix
   by writing the command tags directly, which the closed build refuses. Route
   those five stimuli through the mailbox (write the HmiRequest members over CIP
   and poll AckSequence - the tag is Read/Write, no gateway needed); its plant
   stimulus keeps writing the sim inputs directly, because sensors are not
   commands. fraktal_ab_s16_execute.py needs the same review. Keep the serial
   guard and the restore-in-finally in both.

5. Write a dated evidence record, update Part III 11.2/11.2.1, the README and the
   tool catalog, run the full suite, commit imperative and push.

HOUSE RULES WITH TEETH HERE

* Acceptance is not publication and silence is not parity. This defect is the
  proof: prove a command by the machine state it produced, never by the ack.
* A probe that cannot fail is not evidence. The close needs its refusal test.
* Never perform a controller-changing operation without current explicit
  authorization and an exact target check immediately before use. The bench is a
  test controller with nothing wired to it; that is not a licence to skip the
  serial check.
* Past evidence is append-only. Add a dated record; do not rewrite one.
* Enum ordinals are the PLC contract; test_fraktal_ab_core_ordinals.py pins
  E_Mode, E_ExecState and all 35 E_HmiRequestKind ordinals.
* If something cannot be proved on the bench, record the narrowing and say what
  would prove it. Do not mark anything PASS around a gap.
```

## If the one-scan pulse turns out to be too short

The mode owner samples each request once per scan, so a pulse that spans a
single scan is sufficient *if* the mailbox routine runs first. If the emitted
order cannot be changed cheaply, the fallback is a two-scan pulse driven by a
retained countdown beside `FRK_<app>_HmiLastSequence` — it is already a
non-contract tag with `ExternalAccess="None"`, so a companion costs nothing in
published surface. Record which was needed; it is a scan-order fact about this
baseline and belongs with the S11/S16 findings.

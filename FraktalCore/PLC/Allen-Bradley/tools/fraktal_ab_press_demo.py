#!/usr/bin/env python3
"""The press demo declaration: the first application emitted from the runtime base.

This is the committed source of truth for the Fraktal/AB press demo. It mirrors
the **observable behaviour** of the TwinCAT ``Fraktal_Press_Demo`` - TC3 is the
behavioural oracle for semantics, never for implementation shape. Core
obligations are met here by generated composition, not by inheritance.

**No control power, no physical I/O.** The plant is arithmetic on controller
tags; the embedded I/O module is inhibited and task output updates are disabled.
Nothing electrical is represented, and no control-power domain exists.

Deliberately out of scope, and deferred rather than forgotten: recipes and
changeover, part traceability, release reports, the reusable module library
(module AOIs are generated per-application here; the library form is Phase 6),
the gateway/repository adapter, the generic HMI, physical I/O.

Where AB diverges mechanically from TC3 the divergence is named in the evidence
record's step-graph table rather than absorbed silently. The two that matter:

* **N180 door close.** TC3 treats a two-hand release during closing as an
  operator *abort*: it warns, reopens the door (N185), slides the part out
  (N190) and returns to the two-hand wait. Here it is the **S16 held**
  condition - the close stands still, a LOW named reason is published, no alarm
  is raised, and it self-resumes when the buttons return. The mission specifies
  the held form; the abort form is TC3's. Both are legitimate readings of
  §6.1's "progress resumes on its own"; they are not the same machine
  behaviour, so the difference is recorded.
* **N220 dwell.** TC3 holds the dwell timer when the two-hand is released. Here
  the dwell is a plain delay, because the held condition is already carried at
  N180 and duplicating it would prove nothing new.
"""

from __future__ import annotations

from pathlib import Path

import fraktal_ab_declaration as decl


# --- named reasons ----------------------------------------------------------
# Fixture-scoped numbers, deliberately NOT E_Reason entries: a disposable
# application must not add members to a Core enumeration.
REASONS = {
    "HELD_PERMISSIVE": 6101,     # a permissive was lost; LOW, self-resuming
    "DEVICE_FAULT": 6102,
    "TIMEOUT": 6103,
    "ABORT_REQUEST": 6104,
    "TWO_HAND_RELEASED": 6130,   # the N180 held reason
    "WAIT_DELAY": 6110,
    "WAIT_CONDITION": 6111,
    "WAIT_DECISION": 6112,
    "STEP_STALLED": 6120,
    "PART_NOT_PRESENT": 6131,
    "AIR_NOT_READY": 6132,
    "SLIDE_FAULT": 6133,
}

MODE_MANUAL, MODE_AUTO, MODE_HOME = 0, 1, 2

DECISION_PRESS_NOT_REACHED = 1

# Plant geometry. Retracted is 0, extended is 100, 25 units per scan, so a full
# stroke is four scans at the declared task period.
RETRACTED, EXTENDED = 0, 100


def _cylinder(name: str, comment: str) -> decl.Module:
    return decl.Module(
        name=name,
        comment=comment,
        commands=(
            decl.Command("RETRACT", 1, RETRACTED, "to the retracted end"),
            decl.Command("EXTEND", 2, EXTENDED, "to the extended end"),
        ),
        speed_per_scan=25,
        timeout_ms=500,
    )


def application() -> decl.Application:
    """The committed declaration. Everything the project contains comes from here."""

    par_cfg = decl.Record(
        name="FRK_T_PressParCfg",
        comment="Core §3.8 configuration record for the press demo",
        par_cfg=True,
        members=(
            # Core §3.8: a ParCfg-shaped record leads with SchemaVersion so a
            # reader knows which contract it is holding before it reads it.
            decl.scalar(decl.SCHEMA_VERSION_MEMBER, "which ParCfg contract this is",
                        initial=1),
            decl.duration_ms("TransferSettleMs", "settle after the slide moves in",
                             initial=200),
            decl.duration_ms("PressDwellMs", "how long the ram holds pressure",
                             initial=300),
            decl.boolean("RequireTwoHandStart", "the cell's own policy", initial=1),
            decl.scalar("GoodPartTarget", "parts to make before stopping", initial=0),
        ),
    )

    press_ram = _cylinder("PressRam", "the press ram; EXTEND presses, RETRACT is up")
    door = _cylinder("Door", "the guard door; EXTEND closes, RETRACT opens")
    part_slide = _cylinder("PartSlide", "the part transfer slide")

    n = "Press"
    two_hand = f"FRK_{n}_TwoHand"
    part_present = f"FRK_{n}_PartPresent"
    air_ok = f"FRK_{n}_AirOk"

    # --- AUTO ---------------------------------------------------------------
    # Step numbers mirror the TC3 chain so the two graphs can be compared row by
    # row. The load-position composite is inlined as 240/242/244 because Logix
    # has no sub-chain call in this shape; that is a mechanical divergence, not a
    # behavioural one, and it is recorded as such.
    auto = decl.Chain(
        name="AUTO",
        mode_ordinal=MODE_AUTO,
        loops=True,
        comment="the continuous production cycle",
        steps=(
            decl.Step(0, "autoInitialize", decl.MARK,
                      comment="clear the cycle marker and start",
                      marks=("Ctx.Complete := 0",), on_advance=100),
            decl.Step(100, "awaitTwoHandStart", decl.AWAIT,
                      comment="part present, air ready, and a fresh two-hand start",
                      conditions=(part_present, air_ok, two_hand),
                      hold_reason=REASONS["PART_NOT_PRESENT"], on_advance=110,
                      time_class="WAIT_OPERATOR"),
            decl.Step(110, "ramUp", decl.ISSUE, comment="clear the press",
                      module="PressRam", command="RETRACT", on_advance=130),
            decl.Step(130, "doorOpen", decl.ISSUE, comment="open the guard",
                      module="Door", command="RETRACT", on_advance=150),
            decl.Step(150, "slideInside", decl.ADOPT,
                      comment="transfer the part in; an awaited child whose "
                              "first-out the unit adopts verbatim",
                      module="PartSlide", command="EXTEND", on_advance=170),
            decl.Step(170, "transferSettle", decl.DELAY,
                      comment="let the transfer settle",
                      duration_member="TransferSettleMs", on_advance=180),
            decl.Step(180, "doorClose", decl.HELD_AWAIT,
                      comment="close the guard while the two-hand is held; "
                              "releasing HOLDS the close and self-resumes",
                      module="Door", command="EXTEND",
                      hold_condition=two_hand,
                      hold_reason=REASONS["TWO_HAND_RELEASED"], on_advance=200),
            decl.Step(200, "ramDown", decl.REPORT,
                      comment="press; a ram failure is reported, NOT adopted, "
                              "because the confirmation below is the handling",
                      module="PressRam", command="EXTEND",
                      report_reason=REASONS["DEVICE_FAULT"],
                      on_advance=220, on_jump=210),
            decl.Step(210, "notReachedConfirm", decl.DECISION,
                      comment="the operator confirms before the part is scrapped; "
                              "a scrap is deliberate, so there is no timeout",
                      decision_id=DECISION_PRESS_NOT_REACHED,
                      on_advance=215, on_jump=240, time_class="WAIT_OPERATOR"),
            decl.Step(215, "scrapPart", decl.MARK, comment="disposition NOK",
                      marks=("Ctx.ScrapCount := Ctx.ScrapCount + 1",),
                      on_advance=240),
            decl.Step(220, "pressDwell", decl.DELAY, comment="hold pressure",
                      duration_member="PressDwellMs", on_advance=230),
            decl.Step(230, "recordResult", decl.MARK,
                      comment="record the applied dwell",
                      marks=(), on_advance=240),
            decl.Step(240, "safeRamUp", decl.ISSUE,
                      comment="load-safe position, part 1 of 3",
                      module="PressRam", command="RETRACT", on_advance=242),
            decl.Step(242, "safeDoorOpen", decl.ISSUE,
                      comment="load-safe position, part 2 of 3",
                      module="Door", command="RETRACT", on_advance=244),
            decl.Step(244, "safeSlideOutside", decl.ISSUE,
                      comment="load-safe position, part 3 of 3",
                      module="PartSlide", command="RETRACT", on_advance=999),
            decl.Step(999, "autoComplete", decl.MARK,
                      comment="count the cycle and loop",
                      marks=("Ctx.CycleCount := Ctx.CycleCount + 1",
                             "Ctx.GoodCount := Ctx.GoodCount + 1"),
                      on_advance=100),
        ),
    )

    # --- HOME ---------------------------------------------------------------
    home = decl.Chain(
        name="HOME",
        mode_ordinal=MODE_HOME,
        comment="establish the load-safe position and stop",
        steps=(
            decl.Step(0, "homeInitialize", decl.MARK, marks=("Ctx.Complete := 0",),
                      on_advance=900),
            decl.Step(900, "homeRamUp", decl.ISSUE, module="PressRam",
                      command="RETRACT", on_advance=902),
            decl.Step(902, "homeDoorOpen", decl.ISSUE, module="Door",
                      command="RETRACT", on_advance=904),
            decl.Step(904, "homeSlideOutside", decl.ISSUE, module="PartSlide",
                      command="RETRACT", on_advance=998),
            decl.Step(998, "homeComplete", decl.COMPLETE,
                      comment="the load-safe position is established"),
        ),
    )

    # --- MANUAL -------------------------------------------------------------
    # One command per request, no cycling: the jog target is selected by the
    # operator surface and the chain returns to its wait after each move.
    manual = decl.Chain(
        name="MANUAL",
        mode_ordinal=MODE_MANUAL,
        loops=True,
        comment="jog one module per request",
        steps=(
            decl.Step(0, "manualIdle", decl.AWAIT,
                      comment="wait for a jog request",
                      conditions=(f"FRK_{n}_JogCommand",),
                      hold_reason=REASONS["WAIT_CONDITION"], on_advance=10,
                      time_class="WAIT_OPERATOR"),
            decl.Step(10, "manualJogExtend", decl.ISSUE,
                      comment="jog the selected module out",
                      module="PartSlide", command="EXTEND", on_advance=20),
            decl.Step(20, "manualJogRetract", decl.ISSUE,
                      comment="jog the selected module back",
                      module="PartSlide", command="RETRACT", on_advance=0),
        ),
    )

    return decl.Application(
        name=n,
        controller="1769-L24ER-QB1B",
        major_revision=33,
        task_name="FRK_PressTask",
        task_period_ms=10,
        watchdog_ms=500,
        comment="Fraktal/AB press demo: the first application emitted from the "
                "runtime base. No control power, no physical I/O.",
        records=(par_cfg,),
        modules=(press_ram, door, part_slide),
        chains=(manual, auto, home),
        reasons=REASONS,
        sim_inputs=(two_hand, part_present, air_ok, f"FRK_{n}_JogCommand"),
        chart_steps=32,
    )


def generate(source: Path, output: Path) -> dict[str, object]:
    """The gate-leg entry point: same shape as every other fixture generator."""
    import fraktal_ab_generate

    return fraktal_ab_generate.generate(application(), source, output)

#!/usr/bin/env python3
"""A new Fraktal/AB station, every feature on: copy this file and edit it.

`Specification/Guides/AB_NEW_PROJECT_GUIDE.md` walks through it. The press demo
(`fraktal_ab_press_demo.py`) is the full reference; this is the smallest
station that still uses everything Phases 0-5 delivered, so that a new project
starts with all of it on and turns off what it does not want - rather than
starting bare and having to discover what it is missing.

The cell: a part arrives at a sensor, a clamp closes on it, holds for the
model's dwell, and opens again. AUTO loops that cycle, HOME opens the clamp,
MANUAL commands the clamp directly through its interlock.

Select it for every tool with one variable, never by editing a tool:

    set FRAKTAL_AB_DECLARATION=fraktal_ab_station_template
    python fraktal_ab_generate.py seed.L5X cell.L5X

What is on, and where it is declared:

* §3.4.2 run styles - CONTINUOUS, SINGLE_STEP, HOLD_TO_RUN (`run_styles`)
* §8.5.1 OEE with Performance - `ideal_cycle_member` + `decl.ideal_cycle_ms`
* §8.11.4(d) degradation watch - `baseline_work_member` + `decl.baseline_work_ms`
* §3.12 state flags - `state_flags`
* §8.12 system health - `system_health=decl.SystemHealth.for_task(...)`
* §7.8 a START permit and §7.2 a direction interlock - `start_permits`, `permits`
* §3.8 ParCfg and §3.8a StationCfg records, each SchemaVersion-first
* §3.8 changeover between two models - `models`, `default_model`

Generated whatever a station declares (nothing to opt into): the §6.1
handshake, §6.9 stall diagnosis, the alarm log, MachineState and ReworkCount,
the cycle profiler and command timing, the manifest, the mailbox, the closed
write surface.
"""

from __future__ import annotations

from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_library as library
import fraktal_ab_reasons as reasons
import fraktal_ab_line as line_profile

# --- reasons (Core §8.8) -----------------------------------------------------
# A library type's codes come from the type, Core's from the registry, and the
# station's own from ONE project band, reserved before the first is written.
# This template uses 13000-13999; a real project records its band in the
# binding record so no two stations on a line raise the same number.
REASONS = {
    **reasons.PARAMETER_SETS,
    **library.CYLINDER.reasons,        # INTERLOCK_DROPPED, CYL_NOT_*, CYL_CFG_INVALID
    **library.DIGITAL_INPUT.reasons,   # UNSUPPORTED_COMMAND
    "STEP_STALLED": reasons.CORE["STEP_STALLED"],              # §6.9 fallback
    "PERMISSIVE_NOT_MET": reasons.CORE["PERMISSIVE_NOT_MET"],  # a START permit
    "CYCLE_TIME_DEGRADED": reasons.CORE["CYCLE_TIME_DEGRADED"],  # §8.11.4(d)
    **{name: reasons.CORE[name] for name in (                  # §8.12
        "TASK_OVERRUN", "TASK_JITTER_HIGH", "FIELDBUS_MASTER_FAULT", "DC_SYNC_LOST",
        "TIME_SYNC_LOST", "CONTROLLER_METRICS_UNAVAILABLE")},
    "WAIT_DELAY": 13010,         # a DELAY step's stall reason
    "PART_NOT_PRESENT": 13020,   # the N100 wait
}

# Core E_Mode ordinals: the contract, not a local choice.
MODE_AUTO, MODE_MANUAL, MODE_HOME = 0, 1, 2

# Core §3.8 models: code, description key, dwell, ideal cycle. Measure the real
# cycle on the bench and set the ideal at or below it - an ideal above the
# real cycle caps Performance at 100 %, the flattering number O7 forbids.
MODELS = (
    ("C-1", "project.model.cellC1", 500, 600),
    ("C-2", "project.model.cellC2", 800, 900),
)


def application(*, line=None) -> decl.Application:
    """The committed declaration. Everything the project contains comes from here."""

    n = "Cell"
    part_present = f"FRK_{n}_PartPresent"   # the simulated sensor source

    par_cfg = decl.Record(
        name=f"FRK_T_{n}ParCfg",
        comment="Core §3.8 configuration record: per model",
        par_cfg=True,
        schema_version=1,
        members=(
            decl.scalar(decl.SCHEMA_VERSION_MEMBER, "which ParCfg contract this is",
                        initial=1),
            decl.config_access(decl.editable(decl.duration_ms("DwellMs", "how long the clamp holds",
                                           initial=MODELS[0][2]),
                          "cell.dwellMs", "project.config.cellDwellMs",
                          minimum=50, maximum=10000), "commissioning", min_write_level=3),
            decl.ideal_cycle_ms(MODELS[0][3], "cell.recipe.idealCycleMs"),
            decl.capture(decl.baseline_work_ms(MODELS[0][3], "cell.recipe.baselineWorkMs"),
                         "Profiler.LastWork"),
        ),
    )
    # Core §3.8a: what was measured on THIS cabinet. SchemaVersion starts at 0,
    # "never written", so a fresh download installs these defaults silently.
    station_cfg = decl.Record(
        name=f"FRK_T_{n}StationCfg",
        comment="Core §3.8a deployment record",
        station_cfg=True,
        schema_version=1,
        members=(
            decl.scalar(decl.SCHEMA_VERSION_MEMBER, "0 = never written (Core §3.8a)",
                        initial=0),
            decl.config_access(decl.editable(decl.scalar("StationNumber", "where this cell sits in the line",
                                      initial=1),
                          "station.number", "project.config.stationNumber",
                          minimum=1, maximum=99), "public"),
        ),
    )

    part_there = decl.ModuleState("PartSensor", ("OutImm_Value", "OutImm_Quality"))
    clamp_open = decl.ModuleState("Clamp", ("OutImm_Retracted",), zero=("OutImm_Extended",))

    clamp = decl.Module(
        name="Clamp",
        comment="the part clamp; EXTEND closes, RETRACT opens",
        # TC3's E_CylinderCommand ordinals: EXTEND 1, RETRACT 2.
        commands=(
            decl.Command("EXTEND", 1, library.CYLINDER_EXTENDED, "to the extended end"),
            decl.Command("RETRACT", 2, library.CYLINDER_RETRACTED, "to the retracted end"),
        ),
        timeout_ms=500,
        type_key=library.CYLINDER.type_key,
        # §7.2: a direction's interlock, first-out, in AUTO and MANUAL alike.
        permits=(("EXTEND", (decl.Permit((part_there,),
                                         "project.interlock.cellClampRequiresPart"),)),),
    )
    part_sensor = decl.Module(
        name="PartSensor",
        comment="a part is at the clamp",
        commands=(),
        type_key=library.DIGITAL_INPUT.type_key,
        input=part_present,
    )

    auto = decl.Chain(
        name="AUTO",
        mode_ordinal=MODE_AUTO,
        loops=True,
        # Add decl.SFC and decl.LD to carry the same graph in three languages.
        renditions=(decl.ST,),
        comment="the continuous production cycle",
        steps=(
            decl.Step(0, "autoInitialize", decl.MARK, comment="clear the cycle marker",
                      marks=("Ctx.Complete := 0",), on_advance=100),
            decl.Step(100, "awaitPart", decl.AWAIT, comment="a part at the clamp",
                      conditions=(part_there,),
                      condition_labels=("project.condition.partPresent",),
                      hold_reason=REASONS["PART_NOT_PRESENT"], on_advance=110,
                      time_class="WAIT_OPERATOR"),
            decl.Step(110, "clampClose", decl.ADOPT,
                      comment="close; a clamp fault is adopted verbatim",
                      module="Clamp", command="EXTEND", on_advance=120),
            decl.Step(120, "dwell", decl.DELAY, comment="hold the part",
                      duration_member="DwellMs", on_advance=130),
            decl.Step(130, "clampOpen", decl.ISSUE, module="Clamp", command="RETRACT",
                      on_advance=999),
            decl.Step(999, "autoComplete", decl.MARK, comment="count the cycle and loop",
                      marks=("Ctx.CycleCount := Ctx.CycleCount + 1",
                             "Ctx.GoodCount := Ctx.GoodCount + 1"),
                      on_advance=100),
        ),
    )
    home = decl.Chain(
        name="HOME",
        mode_ordinal=MODE_HOME,
        comment="open the clamp and stop",
        steps=(
            decl.Step(0, "homeInitialize", decl.MARK, marks=("Ctx.Complete := 0",),
                      on_advance=900),
            decl.Step(900, "homeClampOpen", decl.ISSUE, module="Clamp",
                      command="RETRACT", on_advance=998),
            decl.Step(998, "homeComplete", decl.COMPLETE,
                      comment="the cell is in its load position"),
        ),
    )

    return decl.Application(
        name=n,
        controller="1769-L24ER-QB1B",
        major_revision=33,
        task_name=f"FRK_{n}Task",
        task_period_ms=10,
        watchdog_ms=500,
        comment="Fraktal/AB station template: every feature on.",
        records=(par_cfg, station_cfg) + (() if line is None else (line_profile.record(line),)),
        line=line,
        modules=(clamp, part_sensor),
        chains=(auto, home),
        manual_mode=MODE_MANUAL,       # MANUAL has no chain: modules take commands
        start_permits=(decl.Permit((decl.ModuleState("Clamp", (), zero=("Error",)),),
                                   "project.condition.cellClampHealthy"),),
        run_styles=decl.RUN_STYLES,
        ideal_cycle_member="IdealCycleMs",
        baseline_work_member="BaselineWorkMs",
        # Twice the period is an overrun, a fifth of it is high jitter, and
        # nothing this controller cannot measure is required. Pass
        # require_time_sync=True where the station runs CIP Sync.
        system_health=decl.SystemHealth.for_task(10),
        # Candidate transport limits: measure and freeze them for each new station.
        read_budget=decl.ReadBudget(500, 250, 2000, 3000, 1000, 2000, 3000),
        config_sets=True,
        # Where the gateway keeps this station's documents. Live documents
        # replace seeding each new image, but their restore writes the
        # controller: enable them only where the binding record answers
        # "write-enabled" (AB_NEW_PROJECT_GUIDE §3).
        config_medium=decl.ConfigMedium(live_documents=False),
        data_classes=(decl.DataClass("public", "project.dataClass.public"),
                      decl.DataClass("commissioning", "project.dataClass.commissioning")),
        access_users=(),  # provision salted hashes before locking the open policy
        state_flags=(decl.StateFlag("project.state.cellAtLoadPosition", (clamp_open,)),),
        reasons=REASONS,
        sim_inputs=(part_present,),
        type_key="project.moduleType.cell",
        default_model=MODELS[0][0],
        models=tuple(
            decl.Model(code=code, description_key=key,
                       values={"DwellMs": dwell, "IdealCycleMs": ideal,
                               "BaselineWorkMs": ideal})
            for code, key, dwell, ideal in MODELS),
    )


def generate(source: Path, output: Path) -> dict[str, object]:
    """The gate-leg entry point: same shape as every other fixture generator."""
    import fraktal_ab_generate

    return fraktal_ab_generate.generate(application(), source, output)

"""Core §8.8/§8.9 on the Allen-Bradley binding: one reason number space.

The registry is the collision authority. A reason whose symbol it defines is
the SAME reason on every binding: the same code, the same priority, category
and shelving, and the same `std.reason.<code>` texts the HMI already ships.
So a registered reason is never re-rationalized here, and it never gets a
`project.*` key: an AB cylinder that times out extending says exactly what a
TwinCAT one does, in the words the HMI catalogue already has.

Everything else is a project reason, and §8.8 puts those in a band at or
above 10000. The press uses TC3's press band, 12000-12999.

What this module holds is the part only a binding can say: which Core codes
AB raises, and the Core enum ordinals the published numbers mean. Both are
restated here and pinned to the TwinCAT sources by test
(test_fraktal_ab_reasons), the rule the mode ordinals already follow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = (Path(__file__).resolve().parents[4] / "Specification"
                 / "reason_rationalization.json")

# Core E_Severity and E_Category, as published. Pinned by test.
PRIORITY = {"LOW": 0, "MED": 1, "HIGH": 2}
CATEGORY = {"PROCESS": 0, "SAFETY": 1, "SYSTEM": 2}

# The Core reasons this binding raises (E_Reason), by symbol. Pinned by test.
CORE = {
    # Core §8.12, the System band, as TC3's FB_SystemHealthPublisher raises them
    "TASK_OVERRUN": 10,
    "TASK_JITTER_HIGH": 11,
    "FIELDBUS_MASTER_FAULT": 15,
    "DC_SYNC_LOST": 16,
    "TIME_SYNC_LOST": 17,
    "CONTROLLER_METRICS_UNAVAILABLE": 21,
    "PERMISSIVE_NOT_MET": 2002,  # a START's own condition is missing (§7.8)
    "INTERLOCK_DROPPED": 2003,   # a module held on a dropped interlock
    "STEP_STALLED": 2005,        # a chain on a step its graph does not declare
    "CYCLE_TIME_DEGRADED": 2007,  # WORK time drifted past its baseline (§8.11.4(d))
    "UNSUPPORTED_COMMAND": 2008,  # a command a passive module does not take
    "CONFIG_PERSIST_FAILED": 2041,
    "CONFIG_SET_REJECTED": 2042,
    "EVENT_CONFIG_SET_APPLIED": 2043,
}

PARAMETER_SETS = {n: CORE[n] for n in ('CONFIG_PERSIST_FAILED',
                 'CONFIG_SET_REJECTED', 'EVENT_CONFIG_SET_APPLIED')}

# §8.8: a project's own codes live in a band at or above this.
PROJECT_BAND_FLOOR = 10000


@lru_cache(maxsize=1)
def registry() -> dict[str, dict]:
    """The registry's reasons, by symbol."""
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["reasons"]


def registered(name: str) -> bool:
    return name in registry()


@dataclass(frozen=True)
class Rationale:
    priority: int
    category: int
    shelvable: bool
    stem: str              # the text key; `.action` and `.consequence` extend it


def rationalize(name: str, code: int, waits: bool = False) -> Rationale:
    """One reason's §8.9 record.

    Registered: the registry's, with TC3's `std.reason.<code>` keys. Project:
    a wait or hold the operator is expected to clear (`waits`) is LOW and
    shelvable - the machine asking, not the machine broken - and anything else
    is HIGH. Every project reason on this press is a PROCESS condition.
    """
    entry = registry().get(name)
    if entry is not None:
        return Rationale(PRIORITY[entry["priority"]], CATEGORY[entry["category"]],
                         bool(entry["shelvable"]), f"std.reason.{code}")
    return Rationale(PRIORITY["LOW"] if waits else PRIORITY["HIGH"],
                     CATEGORY["PROCESS"], waits, f"project.reason.{name.lower()}")


def waiting_reasons(app) -> set[str]:
    """Project reasons the declaration uses for a wait or a hold.

    From how they are used, not from their names: a step's `hold_reason` is
    what it publishes while it waits, the generator's own wait reasons
    (`WAIT_*`) are the delay, condition and decision stalls, and a guarded
    command's warning is the operator letting go - designed behaviour, which
    TC3's press raises at LOW (N180's M_RaiseWarning).
    """
    by_code = {code: name for name, code in app.reasons.items()}
    names = {name for name in app.reasons if name.startswith("WAIT_")}
    for chain in app.chains:
        for step in chain.steps:
            if step.hold_reason in by_code:
                names.add(by_code[step.hold_reason])
            if step.action == "guarded" and step.report_reason in by_code:
                names.add(by_code[step.report_reason])
    return names


def of(app, name: str) -> Rationale:
    """The rationale of a reason the application registers."""
    return rationalize(name, app.reasons[name], name in waiting_reasons(app))


def validate(app) -> list[str]:
    """§8.8 bands: a reason is registered, with its registered code, or in a
    project band. The registered code itself is checked against TwinCAT by
    test; this holds the declaration to the rule."""
    findings: list[str] = []
    needs = {"STEP_STALLED"}       # every chain's fallback for an undeclared step
    for chain in app.chains:
        for step in chain.steps:
            if step.action == "delay":
                needs.add("WAIT_DELAY")
                if step.conditions and not step.hold_reason:
                    needs.add("WAIT_CONDITION")
            elif step.action == "await" and not step.hold_reason:
                needs.add("WAIT_CONDITION")
            elif step.action == "decision":
                needs.add("WAIT_DECISION")
    if getattr(app, "start_permits", ()):
        needs.add("PERMISSIVE_NOT_MET")    # a start permit's release reason
    if getattr(app, "baseline_work_member", ""):
        needs.add("CYCLE_TIME_DEGRADED")   # the degradation watch's event
    if getattr(app, "system_health", None) is not None:
        import fraktal_ab_generate as gen
        needs.update(gen.HEALTH_EVENTS)    # §8.12's events, each one
    for name in sorted(needs - set(app.reasons)):
        findings.append(f"{app.name} publishes {name} as a stall reason but "
                        f"does not register it")
    for name, code in app.reasons.items():
        if registered(name):
            core = CORE.get(name)
            if core is not None and code != core:
                findings.append(f"{name} is Core {core}, not {code}")
        elif code < PROJECT_BAND_FLOOR:
            findings.append(
                f"{name} = {code} is neither a registered reason nor in a "
                f"project band (>= {PROJECT_BAND_FLOOR}, Core §8.8)")
    return findings

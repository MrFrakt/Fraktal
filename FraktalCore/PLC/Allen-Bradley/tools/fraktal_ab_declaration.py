#!/usr/bin/env python3
"""The Fraktal/AB declaration: the committed source a Logix application emits from.

One declaration is the source of truth for an application. The generator turns it
into contract UDTs, module AOIs, a mode owner, routine bodies and an L5X.
Hand-authored L5X is forbidden; if something is not expressible here, the
declaration grows - the output never gets edited.

**The S16 findings are rules here, not conventions.** Each is enforced by
``validate`` and covered by a negative test, because a rule that cannot reject
anything is a comment:

1. **Ordering is self-checked.** Every emitted mode owner verifies that each
   child module AOI ran in this scan and counts a violation if not. S11 proved
   the ordering for sequences and S16 restated it for commands; a generator that
   emitted the call order correctly but could not detect its own violation would
   be relying on the author having got it right.
2. **Durations are milliseconds, converted from the declared task period**, and
   the emitted project asserts at build time that the task it is scheduled on
   still has that period. S16 found the task rate is part of the contract: a
   module moved to a task of another period silently changes its own timeouts.
3. **A held command's timeout does not accrue.** Held exists to distinguish "the
   operator let go" from "the machine is broken"; a hold that matures into a
   timeout destroys that distinction.
4. **The frozen v33 type map.** Booleans are 0/1 ``DINT``; durations are
   range-checked ``DINT`` milliseconds. ``TIME``/``TIME32``/``LREAL`` are absent
   and ``LINT`` is transport-only (S12). **No ``BOOL`` member may appear in a
   public contract UDT** - that layout is a recorded S12 hole, not a local call.
5. **Every ParCfg-shaped record starts with ``SchemaVersion : DINT``** (Core
   §3.8), so a reader can tell which contract it is holding before it reads it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


# --- the frozen v33 type map (S12) -----------------------------------------

DINT = "DINT"
EXCLUDED_TYPES = ("TIME", "TIME32", "LREAL")
TRANSPORT_ONLY_TYPES = ("LINT",)
BOOLEAN_CARRIER = DINT       # 0/1, never BOOL - the S12 hole
DURATION_CARRIER = DINT      # milliseconds, range checked

DURATION_MIN_MS = 0
DURATION_MAX_MS = 3_600_000  # one hour; a range check that can actually reject

SCHEMA_VERSION_MEMBER = "SchemaVersion"


class DeclarationError(ValueError):
    """The declaration is not emittable. Raised instead of emitting bad Logix."""


# --- members and records ----------------------------------------------------

@dataclass(frozen=True)
class Member:
    """One contract UDT member. Everything is a DINT on this baseline."""

    name: str
    comment: str = ""
    kind: str = "scalar"          # scalar | boolean | duration_ms | reason
    dimension: int = 0
    initial: int = 0
    external_access: str = "Read/Write"

    @property
    def data_type(self) -> str:
        return DINT


def boolean(name: str, comment: str = "", initial: int = 0,
            dimension: int = 0) -> Member:
    """A 0/1 DINT. Not a BOOL: the BOOL-member UDT layout is unmeasured (S12)."""
    return Member(name, comment, kind="boolean", initial=initial,
                  dimension=dimension)


def duration_ms(name: str, comment: str = "", initial: int = 0,
                dimension: int = 0) -> Member:
    return Member(name, comment, kind="duration_ms", initial=initial,
                  dimension=dimension)


def reason(name: str, comment: str = "", dimension: int = 0) -> Member:
    return Member(name, comment, kind="reason", dimension=dimension)


def scalar(name: str, comment: str = "", initial: int = 0, dimension: int = 0) -> Member:
    return Member(name, comment, kind="scalar", initial=initial, dimension=dimension)


@dataclass(frozen=True)
class Record:
    """A contract UDT.

    ``par_cfg`` marks the Core §3.8 configuration shape, which must lead with
    ``SchemaVersion``.
    """

    name: str
    members: tuple[Member, ...]
    comment: str = ""
    par_cfg: bool = False
    schema_version: int = 1


# --- modules ----------------------------------------------------------------

@dataclass(frozen=True)
class Command:
    """One command a module accepts, and where its simulated plant ends up."""

    name: str
    ordinal: int
    target_position: int
    comment: str = ""


@dataclass(frozen=True)
class Module:
    """A module type: the Core §6.1 handshake over a simulated plant.

    ``adopts_faults`` records whether a parent awaiting this module adopts its
    first-out verbatim. It is a property of how the chain awaits the child, so
    the chain step carries the choice; this flag is the module's default.
    """

    name: str
    comment: str
    commands: tuple[Command, ...]
    speed_per_scan: int = 25
    timeout_ms: int = 500
    position_min: int = 0
    position_max: int = 100
    can_fault: bool = True


# --- chain steps ------------------------------------------------------------

ISSUE = "issue"                 # command a module, wait for Done
DELAY = "delay"                 # wait a declared duration
AWAIT = "await"                 # wait for named conditions
HELD_AWAIT = "held_await"       # wait, but publish Held + LOW reason, no Error
DECISION = "decision"           # wait for an operator answer, never faults
ADOPT = "adopt"                 # awaited child: adopt its first-out verbatim
REPORT = "report"               # child error reported, NOT adopted, then jump
MARK = "mark"                   # set a counter or flag
COMPLETE = "complete"           # terminal for a non-looping chain


@dataclass(frozen=True)
class Step:
    """One step of one chain."""

    number: int
    name: str
    action: str
    comment: str = ""
    module: str = ""
    command: str = ""
    duration_member: str = ""
    conditions: tuple[str, ...] = ()
    hold_condition: str = ""
    hold_reason: int = 0
    adopt_from: str = ""
    report_reason: int = 0
    decision_id: int = 0
    on_advance: int = -1
    on_jump: int = -1
    marks: tuple[str, ...] = ()
    time_class: str = "WORK"


# The languages a chain's graph may be rendered in. The graph is declared once;
# a rendition is an emission of it, never a second maintained source. TC3 keeps
# the same rule for its press: one graph, several renditions, machine-checked
# for equality.
ST = "ST"
SFC = "SFC"
LD = "LD"
RENDITIONS = (ST, SFC, LD)


@dataclass(frozen=True)
class Chain:
    """One mode's step graph, and the languages it is rendered in."""

    name: str
    mode_ordinal: int
    steps: tuple[Step, ...]
    comment: str = ""
    loops: bool = False
    renditions: tuple[str, ...] = (ST,)

    @property
    def multi_rendition(self) -> bool:
        """True when this chain is carried in more than one language.

        A multi-rendition chain is hosted in program routines rather than inside
        the mode-owner AOI: an Add-On Instruction cannot contain an SFC routine,
        so the only way to render the same graph in all three languages is to
        put each rendition where all three can live.
        """
        return len(self.renditions) > 1


# --- the application --------------------------------------------------------

@dataclass(frozen=True)
class Application:
    """One committed declaration: everything a Logix project is emitted from."""

    name: str
    controller: str
    major_revision: int
    task_name: str
    task_period_ms: int
    watchdog_ms: int
    comment: str
    records: tuple[Record, ...]
    modules: tuple[Module, ...]
    chains: tuple[Chain, ...]
    reasons: dict[str, int] = field(default_factory=dict)
    # Simulated operator and sensor inputs the harness writes. Every condition a
    # step waits on must name one of these: a condition referencing a tag that
    # does not exist is rejected here rather than discovered in Studio.
    sim_inputs: tuple[str, ...] = ()
    chart_steps: int = 32
    program_name: str = ""
    routine_name: str = ""

    @property
    def program(self) -> str:
        return self.program_name or f"FRK_{self.name}Program"

    @property
    def routine(self) -> str:
        return self.routine_name or f"FRK_{self.name}Main"


# --- validation -------------------------------------------------------------

def _validate_record(record: Record) -> list[str]:
    findings: list[str] = []
    if not record.members:
        findings.append(f"{record.name}: a contract record with no members")
    for member in record.members:
        if member.data_type != DINT:
            findings.append(
                f"{record.name}.{member.name}: {member.data_type} is not on the "
                f"frozen v33 map; every contract scalar is a DINT"
            )
        if member.kind == "duration_ms" and not (
            DURATION_MIN_MS <= member.initial <= DURATION_MAX_MS
        ):
            findings.append(
                f"{record.name}.{member.name}: duration {member.initial} ms is "
                f"outside the checked range {DURATION_MIN_MS}..{DURATION_MAX_MS}"
            )
        if member.kind == "boolean" and member.initial not in (0, 1):
            findings.append(
                f"{record.name}.{member.name}: a boolean carrier holds 0 or 1, "
                f"not {member.initial}"
            )
    if record.par_cfg:
        if not record.members or record.members[0].name != SCHEMA_VERSION_MEMBER:
            findings.append(
                f"{record.name}: a ParCfg-shaped record shall start with "
                f"{SCHEMA_VERSION_MEMBER} (Core §3.8)"
            )
    names = [m.name for m in record.members]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        findings.append(f"{record.name}: duplicate members {sorted(duplicates)}")
    return findings


def _validate_chain(app: Application, chain: Chain) -> list[str]:
    findings: list[str] = []
    numbers = [s.number for s in chain.steps]
    duplicates = {n for n in numbers if numbers.count(n) > 1}
    if duplicates:
        findings.append(f"{chain.name}: duplicate step numbers {sorted(duplicates)}")
    known = set(numbers)
    module_names = {m.name for m in app.modules}
    duration_members = {
        m.name for r in app.records for m in r.members if m.kind == "duration_ms"
    }
    for step in chain.steps:
        where = f"{chain.name}.N{step.number}"
        for target, label in ((step.on_advance, "on_advance"), (step.on_jump, "on_jump")):
            if target != -1 and target not in known:
                findings.append(f"{where}: {label} targets missing step N{target}")
        if step.action in (ISSUE, ADOPT) and step.module not in module_names:
            findings.append(f"{where}: unknown module {step.module!r}")
        if step.action == ISSUE:
            module = next(m for m in app.modules if m.name == step.module)
            if step.command not in {c.name for c in module.commands}:
                findings.append(
                    f"{where}: {step.module} has no command {step.command!r}"
                )
        if step.action == DELAY and step.duration_member not in duration_members:
            findings.append(
                f"{where}: delay references {step.duration_member!r}, which is not "
                f"a declared duration member"
            )
        if step.action == HELD_AWAIT:
            if not step.hold_condition:
                findings.append(f"{where}: a held wait needs a hold condition")
            if not step.hold_reason:
                findings.append(
                    f"{where}: a held wait needs a named reason - an unnamed hold "
                    f"is indistinguishable from a stall"
                )
        if step.action == REPORT and not step.report_reason:
            findings.append(f"{where}: a reported child condition needs a reason")
        if step.action == DECISION and not step.decision_id:
            findings.append(f"{where}: a decision step needs a decision id")
        for condition in tuple(step.conditions) + (
            (step.hold_condition,) if step.hold_condition else ()
        ):
            if condition not in app.sim_inputs:
                findings.append(
                    f"{where}: condition {condition!r} is not a declared "
                    f"simulated input; nothing would define that tag"
                )
    if chain.steps and not chain.loops:
        if not any(s.action == COMPLETE for s in chain.steps):
            findings.append(f"{chain.name}: a non-looping chain needs a COMPLETE step")

    if not chain.renditions:
        findings.append(f"{chain.name}: a chain must be rendered in at least one language")
    for rendition in chain.renditions:
        if rendition not in RENDITIONS:
            findings.append(f"{chain.name}: unknown rendition {rendition!r}")
    if len(set(chain.renditions)) != len(chain.renditions):
        findings.append(f"{chain.name}: duplicate renditions {list(chain.renditions)}")
    if chain.renditions and chain.renditions[0] != ST:
        # ST is the reference rendition every other one is compared against, so
        # it is the one that must always exist and be listed first.
        findings.append(f"{chain.name}: ST is the reference rendition and comes first")
    return findings


def validate(app: Application) -> list[str]:
    """Return every reason this declaration must not be emitted. Empty means go."""
    findings: list[str] = []

    if app.task_period_ms <= 0:
        findings.append("the task period must be positive; it is part of the contract")
    if app.watchdog_ms <= app.task_period_ms:
        findings.append("the watchdog must exceed the task period")

    record_names = [r.name for r in app.records]
    duplicates = {n for n in record_names if record_names.count(n) > 1}
    if duplicates:
        findings.append(f"duplicate record names {sorted(duplicates)}")
    for record in app.records:
        findings.extend(_validate_record(record))

    module_names = [m.name for m in app.modules]
    duplicates = {n for n in module_names if module_names.count(n) > 1}
    if duplicates:
        findings.append(f"duplicate module names {sorted(duplicates)}")
    for module in app.modules:
        if not (DURATION_MIN_MS <= module.timeout_ms <= DURATION_MAX_MS):
            findings.append(
                f"{module.name}: timeout {module.timeout_ms} ms is outside the "
                f"checked range"
            )
        # Guarded: a non-positive period is already reported above, and dividing
        # by it here would raise instead of reporting the real finding.
        if app.task_period_ms > 0 and module.timeout_ms % app.task_period_ms:
            findings.append(
                f"{module.name}: timeout {module.timeout_ms} ms is not a whole "
                f"number of {app.task_period_ms} ms task periods, so the module "
                f"cannot count it exactly"
            )
        if not module.commands:
            findings.append(f"{module.name}: a module with no commands")

    mode_ordinals = [c.mode_ordinal for c in app.chains]
    duplicates = {n for n in mode_ordinals if mode_ordinals.count(n) > 1}
    if duplicates:
        findings.append(f"duplicate mode ordinals {sorted(duplicates)}")
    for chain in app.chains:
        findings.extend(_validate_chain(app, chain))

    used = {s.number for c in app.chains for s in c.steps}
    if len(used) > app.chart_steps:
        findings.append(
            f"{len(used)} distinct steps exceed the declared chart size "
            f"{app.chart_steps}; the §3.13 marks would be truncated"
        )
    return findings


def require_valid(app: Application) -> None:
    findings = validate(app)
    if findings:
        raise DeclarationError(
            "declaration cannot be emitted:\n  " + "\n  ".join(findings)
        )


def scans_for(app: Application, milliseconds: int) -> int:
    """Convert a declared duration to whole task scans.

    The conversion lives here, next to the declared period, so the emitted logic
    never carries a magic scan count whose origin has been forgotten.
    """
    if milliseconds < DURATION_MIN_MS or milliseconds > DURATION_MAX_MS:
        raise DeclarationError(f"duration {milliseconds} ms is outside the checked range")
    if milliseconds % app.task_period_ms:
        raise DeclarationError(
            f"{milliseconds} ms is not a whole number of {app.task_period_ms} ms scans"
        )
    return milliseconds // app.task_period_ms


def chart_index(app: Application, ordered_steps: Sequence[int], number: int) -> int:
    """Index of a step in the §3.13 chart arrays."""
    return list(ordered_steps).index(number)

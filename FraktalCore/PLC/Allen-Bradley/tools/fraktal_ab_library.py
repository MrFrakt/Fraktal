"""The Fraktal/AB module library: reusable types, independent of any application.

This is the Logix counterpart of TC3's ``Fraktal_Modules``. An application
declares module INSTANCES of these types; the generator embeds one AOI per type
it uses, and that AOI is the same bytes in every application - which is what
makes a fix to a type a fix everywhere, the O1 promise that standardisation is
paid once per reusable module type.

Nothing here may name an application, a task period, or an application's
reason codes. ``test_fraktal_ab_library.py`` generates each type's AOI under
two unrelated applications and requires identical output.

Adding a type: declare it here, add it to ``TYPES``, and give it generated
logic in ``fraktal_ab_generate.type_logic``. The four press modules the TC3
build has and this one does not (TwoHand, AirPressureMonitor,
PartPresentSensor, PartFeed - audit 2026-09-29 §6.2) are born here.
"""

from __future__ import annotations

import fraktal_ab_declaration as decl


# Core §6.1 handshake over a positional plant: EXTEND/RETRACT to a target, HELD
# on a dropped interlock, a timeout that does not accrue while held.
#
# TC3's FB_CylinderCM's own codes, so an AB cylinder fault is the same
# registered reason with the same texts: held on INTERLOCK_DROPPED (its
# FB_PermIntlk conditions), and a timeout named by the end that did not
# report. CYL_CFG_INVALID is TC3's for a cylinder that cannot time a move.
# The numbers are pinned to Fraktal_Core/E_Reason and Fraktal_Modules/
# PL_ModuleReasons by test_fraktal_ab_reasons.
# Where the simulated cylinder's end sensors read true: TC3's ExtendedFb and
# RetractedFb, at the two ends of a stroke the press declares as 0..100.
CYLINDER_RETRACTED, CYLINDER_EXTENDED = 0, 100

CYLINDER = decl.ModuleType(
    type_key="std.moduleType.cylinder",
    description="Fraktal cylinder: Core §6.1 handshake over a positional plant",
    reasons={
        "INTERLOCK_DROPPED": 2003,
        "CYL_NOT_EXTENDED": 10101,
        "CYL_NOT_RETRACTED": 10102,
        "CYL_CFG_INVALID": 10115,
    },
    # TC3 FB_CylinderCM names the end sensor that did not report: a timeout
    # extending implicates the extended sensor, retracting the retracted one.
    io_roles=("retractedFb", "extendedFb"),
    # FaultRequest holds the plant still; HoldRequest drops the interlock.
    injections=("Fault", "Hold"),
)


# TC3's FB_DigitalInputCM: a passive monitor. It publishes the input's Value
# and Quality as its HAL presents them, and refuses any command it is given
# with UNSUPPORTED_COMMAND. Owning logic consumes the semantic value; the
# electrical tag is the application's, bound to the `input` role.
DIGITAL_INPUT = decl.ModuleType(
    type_key="std.moduleType.digitalInput",
    description="Fraktal digital input: a passive monitor of one input",
    reasons={"UNSUPPORTED_COMMAND": 2008},
    io_roles=("input",),
    passive=True,
)

# TC3's FB_TwoHandStartCM: a functional cycle-start edge from a certified
# two-hand result. It implements no simultaneity, anti-tie-down or safe output
# - SafeActive is the safety system's, never computed here. It arms when both
# buttons are released, and a SafeActive rising edge while armed is one
# StartPulse. Passive: any command is refused.
TWO_HAND = decl.ModuleType(
    type_key="std.moduleType.twoHand",
    description="Fraktal two-hand start: a start edge from a certified result",
    reasons={"UNSUPPORTED_COMMAND": 2008},
    io_roles=("left", "right"),
    passive=True,
)

# TC3's FB_AirPressureMonitorCM: two pneumatic-pressure switches. Pressure is
# OK when the operating switch is on, the low switch is off and the reading is
# trusted. Both on is implausible - but only once it has persisted for the
# station's ConflictTime, because the switches overlap briefly while air
# fills - and it is then a fault naming both switches, latched until an
# operator reset.
AIR_PRESSURE = decl.ModuleType(
    type_key="std.moduleType.airPressure",
    description="Fraktal air pressure monitor: two pressure switches",
    reasons={"AIR_SWITCH_CONFLICT": 10601, "UNSUPPORTED_COMMAND": 2008},
    io_roles=("low", "operating"),
    passive=True,
)

TYPES: dict[str, decl.ModuleType] = {
    t.type_key: t for t in (CYLINDER, DIGITAL_INPUT, TWO_HAND, AIR_PRESSURE)}


def type_of(module: decl.Module) -> decl.ModuleType:
    """The library type a module instance declares, or KeyError."""
    return TYPES[module.type_key]


def types_used(app: decl.Application) -> tuple[decl.ModuleType, ...]:
    """Each library type the application uses once, in first-use order."""
    seen: dict[str, decl.ModuleType] = {}
    for module in app.modules:
        seen.setdefault(module.type_key, type_of(module))
    return tuple(seen.values())


def validate(app: decl.Application) -> list[str]:
    """What the declaration cannot check alone, because it knows no library.

    Two rules. An instance names a type that exists - otherwise there is no AOI
    for it to call. And the application registers each type's reason codes
    exactly as the type declares them: the type raises them, so the type is the
    source, and a registration that disagreed would rationalize a code the
    controller never sends while the one it does send goes unexplained.
    """
    import fraktal_ab_reasons as reasons

    findings: list[str] = list(reasons.validate(app))
    for module in app.modules:
        if module.type_key not in TYPES:
            findings.append(
                f"{module.name}: {module.type_key!r} is not a library type; "
                f"declare it in fraktal_ab_library.TYPES")
    for module in app.modules:
        mtype = TYPES.get(module.type_key)
        if mtype is None:
            continue
        for name, code in mtype.reasons.items():
            registered = app.reasons.get(name)
            if registered != code:
                findings.append(
                    f"{app.name} registers {name} = {registered}, but library "
                    f"type {mtype.type_key} raises {code}")
    # A passive type is fed from a declared source and commanded by nothing;
    # a commanded one is the reverse.
    for module in app.modules:
        mtype = TYPES.get(module.type_key)
        if mtype is None:
            continue
        if mtype.passive:
            if module.commands:
                findings.append(f"{module.name}: {mtype.type_key} is passive and "
                                f"takes no commands")
            if module.input not in app.sim_inputs:
                findings.append(f"{module.name}: its input {module.input!r} is not "
                                f"a declared source")
        else:
            if not module.commands:
                findings.append(f"{module.name}: {mtype.type_key} is commanded and "
                                f"declares no commands")
            if module.input:
                findings.append(f"{module.name}: {mtype.type_key} is commanded and "
                                f"takes no input")
    # A channel role is the join a diagnostic's IoTag travels through, so it
    # must name a role its module's type can implicate, and name it once.
    by_name = {m.name: m for m in app.modules}
    bound: set[tuple[str, str]] = set()
    for io_module in app.io_modules:
        for channel in io_module.channels:
            if not channel.role:
                continue
            owner = by_name.get(channel.module_path)
            mtype = TYPES.get(owner.type_key) if owner else None
            if mtype is None or channel.role not in mtype.io_roles:
                findings.append(
                    f"{channel.name}: role {channel.role!r} is not one "
                    f"{channel.module_path or 'an unowned channel'} can implicate")
            elif (channel.module_path, channel.role) in bound:
                findings.append(
                    f"{channel.name}: {channel.module_path} already binds "
                    f"{channel.role!r} to another channel")
            bound.add((channel.module_path, channel.role))
    return sorted(set(findings))


def require_valid(app: decl.Application) -> None:
    findings = validate(app)
    if findings:
        raise decl.DeclarationError("; ".join(findings))

#!/usr/bin/env python3
"""Project an Allen-Bradley controller into the HMI's transport-neutral snapshot.

The Fraktal HMI is generic and data-driven: its snapshot mapper takes a flat
``{browsePath: value}`` document, finds a module wherever a node publishes
``Status/Name`` and ``Status/ModuleType``, and builds the tree from the dotted
identity. It says so itself - "maps a *transport-neutral* flat OPC UA browse
snapshot" - and keys off the normative ``Status`` member rather than any
concrete function-block type. So an AB controller does not need its own screens
or its own repository: it needs a projection into that document.

This is that projection. It reads the published manifest for the shape of the
station and the live contexts for its state, and emits the document.

**It is fail-closed, because Core §3.10 says discovery is all or nothing.** An
invalid manifest, a truncated one, or a content hash that disagrees with the
declaration invalidates the whole projection. There is no degraded mode that
renders part of a station: a client that cannot trust the manifest does not
proceed on assumption, and a half-drawn plant is a worse answer than a refusal.

**What the AB binding does not publish is named, not zero-filled.** The mapper
coerces a missing key to a default - a missing ``TileEnable`` becomes true, a
missing count becomes zero - so silence here would render as data. Everything
this binding cannot supply is listed in ``absent`` as machine-readable fact,
and the reason is recorded with it.

Read-only. Nothing in this file writes to a controller.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_station as station

SCHEMA = "fraktal.ab.projection"
SCHEMA_VERSION = 1

# The selected station: the press unless FRAKTAL_AB_DECLARATION says otherwise.
APP = station.application()

# lib/domain/types.dart: enum ModuleType { none, unit, equipmentModule,
# controlModule }. These are the HMI contract, the same way E_Mode is.
MODULE_TYPE_UNIT = 1
MODULE_TYPE_CONTROL = 3

# What this binding cannot publish today, and why. Each entry is a browse-path
# suffix the mapper would read; naming them keeps the gap in the data rather
# than in a paragraph someone has to remember.
ABSENT: tuple[tuple[str, str], ...] = (
    ("Status/DescriptionKey",
     "the declaration carries one name per module, not a separate description"),
    ("Status/ControlDomainId",
     "the control-power domain is a recorded Phase 4 deferral"),
    ("HostEvents/*", "the host event ring is owed work, not published"),
    ("ControlPower/*", "out of scope: no control-power domain"),
    ("Nameplate/*", "no module in this application declares a nameplate"),
)


class ProjectionRefused(Exception):
    """Discovery failed its own validity check, so nothing is projected."""


class BuildMismatch(ProjectionRefused):
    """The controller runs a build other than the declaration loaded here.

    Carries both hashes, so a caller can say which side moved instead of
    parsing the message: the usual cause is a download that landed after the
    reader loaded its declaration, and the fix for that is a restart.
    """

    def __init__(self, message: str, controller_hash: Any, declared_hash: str):
        super().__init__(message)
        self.controller_hash = controller_hash
        self.declared_hash = declared_hash


class ReadFailed(Exception):
    """A controller read returned nothing, so there is no state to project."""


def validate(header: dict[str, Any]) -> None:
    """Core §3.10: partial discovery is not a degraded conformance mode."""
    reasons: list[str] = []
    if header.get("Magic") != manifest.MANIFEST_MAGIC:
        reasons.append("the manifest magic is wrong; this is not a Fraktal manifest")
    if header.get("SchemaMajor") != manifest.MANIFEST_SCHEMA_MAJOR:
        reasons.append(
            f"manifest schema major {header.get('SchemaMajor')} is not "
            f"{manifest.MANIFEST_SCHEMA_MAJOR}")
    if header.get("Valid") != 1:
        reasons.append("the controller reports the manifest is not valid")
    if header.get("Truncated") != 0:
        reasons.append("the manifest is truncated; the station is not fully described")
    # The hash covers what is published, not the room it is stored in, so two
    # builds of one declaration with different table sizes share it. A table
    # sized for another build is read at the wrong size, so it is refused by
    # name - before a single table is read, not after a slow fallback.
    for table in manifest.tables(APP):
        published = header.get(f"{table.name}Capacity")
        if published != table.capacity:
            reasons.append(
                f"{table.name} holds {published} rows on the controller and "
                f"{table.capacity} in the declaration; it was built from another "
                f"declaration")
    declared = manifest.content_hash(APP)
    if header.get("ContentHash") != declared:
        reasons.append(
            f"content hash {header.get('ContentHash')!r} does not match the "
            f"declaration {declared!r}")
        raise BuildMismatch("; ".join(reasons), header.get("ContentHash"), declared)
    if reasons:
        raise ProjectionRefused("; ".join(reasons))


def browse_path(identity: str) -> str:
    """The browse path for a dotted identity.

    The mapper discards a node whose browse name differs from the last segment
    of its identity - that is how it drops TF6100 reference aliases - so the two
    are kept in step by construction here.
    """
    return identity.replace(".", "/")


def modules(rows: dict[str, Any]) -> list[dict[str, Any]]:
    """Identity, browse path and module type for every published module."""
    keys = {row["NumericKey"]: row["PortableKey"]
            for row in rows["Localization"]}
    # §7.1 type keys come from the declaration, the one source the manifest is
    # also generated from; the controller carries no copy to drift.
    type_keys = {module.name: module.type_key for module in APP.modules}
    out = []
    for row in rows["Modules"]:
        identity = keys.get(row["CanonicalPathKey"], "")
        if not identity:
            continue
        out.append({
            "moduleId": row["ModuleId"],
            "identity": identity,
            "base": browse_path(identity),
            "type": (MODULE_TYPE_UNIT if row["Tier"] == manifest.TIER_ROOT
                     else MODULE_TYPE_CONTROL),
            "displayNameKey": keys.get(row["LocalNameKey"], ""),
            "typeKey": (APP.type_key if row["Tier"] == manifest.TIER_ROOT
                        else type_keys.get(identity.split(".")[-1], "")),
        })
    return out


# PTP is not enabled on any deployment this binding claims (AB S9): the
# controller clock is correct locally and synchronized to nothing else. One
# statement of that fact, for every timestamp the projection publishes.
TIME_SYNCHRONIZED = False


def reason_description(app, code: int) -> str:
    """A registered project reason's text key; "" otherwise.

    The controller publishes the number (Logix v33 ST cannot assign a string,
    S12) and this is where it becomes a key, as DiagnosticKey does for the
    mailbox. A Core reason is described by the client from its code
    (reasonDescriptionKey), and an unregistered one has nothing true to say.
    """
    name = next((n for n, c in app.reasons.items() if c == code), None)
    return manifest.reason_key(app, name) if name and code else ""


def io_join(app, module_name: str, roles: int) -> tuple[str, str]:
    """The electrical tags and addresses a diagnostic implicates.

    `roles` is the bit set the module's AOI published - which of its type's
    io_roles the fault is about - and this declaration binds each role of each
    module to one channel. Several are joined " / ", as TC3's cylinder joins
    both sensor tags for a sensor conflict. Nothing bound: "" and "".
    """
    import fraktal_ab_library as library

    module = next((m for m in app.modules if m.name == module_name), None)
    if module is None or not roles:
        return "", ""
    type_roles = library.type_of(module).io_roles
    wanted = {role for bit, role in enumerate(type_roles) if roles >> bit & 1}
    tags, addresses = [], []
    for io_module in app.io_modules:
        for channel in io_module.channels:
            if channel.module_path == module_name and channel.role in wanted:
                tags.append(channel.name)
                addresses.append(channel_address(io_module, channel))
    return " / ".join(tags), " / ".join(addresses)


def channel_address(io_module, channel) -> str:
    """A channel's Logix address, the one form the fieldbus view and every
    diagnostic that names the channel both publish."""
    outward = channel.direction == DIR_OUTPUT
    return f"{io_module.address}:{'O' if outward else 'I'}.{channel.bit}"


def diagnostic(app, reason: int, since_date: int, since_time: int,
               io: tuple[str, str], description: str | None = None) -> dict[str, Any]:
    """Core §6.9(a) Status.Diagnostic, in the fields the client reads.
    `description` names the condition when the module knows more than its
    reason code does - TC3's PermIntlk description of the missing interlock."""
    tag, address = io
    return {
        "Status/Diagnostic/ReasonCode": reason,
        "Status/Diagnostic/Description": description or reason_description(app, reason),
        "Status/Diagnostic/IoTag": tag,
        "Status/Diagnostic/IoAddress": address,
        # Since is the onset the controller stamped when this reason began; a
        # module with nothing to report has no onset, said as 0.
        "Status/Diagnostic/Since": (_controller_time(since_date, since_time)
                                    if reason else 0),
        "Status/Diagnostic/TimeSynchronized": TIME_SYNCHRONIZED,
    }


def held_description(app, name: str, context: dict[str, int],
                     catalogue: dict[int, str] | None) -> str | None:
    """Which interlock holds a module, by TC3's key for it: the area
    interlock (SetAreaSafe) first, as TC3's PermIntlk orders it, else the
    missing directional permit, whose number the controller published and
    this controller's own catalogue names. None when nothing holds it."""
    if not context.get("OutImm_Held"):
        return None
    module = next((m for m in app.modules if m.name == name), None)
    if module is None:
        return None
    if context.get("AreaSafe", 1) == 0 and module.area_safe_key:
        return module.area_safe_key
    if context.get("Permit", 1) == 0 and context.get("PermitKey", 0):
        return (catalogue or {}).get(context["PermitKey"])
    return None


def command_catalog(app, name: str) -> dict[str, Any]:
    """TC3's §7.6.1 command catalogue (`_M_PublishCommand`): what a manual
    command to this module may be. From the declaration - it is the module's
    static contract, as the step names are - with TC3's std.command labels.
    A module that takes no commands publishes an empty catalogue."""
    module = next((m for m in app.modules if m.name == name), None)
    commands = module.commands if module is not None else ()
    values: dict[str, Any] = {"CatalogCount": len(commands)}
    for index, command in enumerate(commands, start=1):
        values[f"Catalog[{index}]/Value"] = command.ordinal
        values[f"Catalog[{index}]/Label"] = f"std.command.{command.name.lower()}"
        values[f"Catalog[{index}]/Style"] = 0          # E_CommandStyle.ONESHOT
    return values


def module_status(context: dict[str, int], app=None, name: str = "",
                  catalogue: dict[int, str] | None = None) -> dict[str, Any]:
    """One module's Status members, from its contract context."""
    app = app or APP
    reason = context["OutImm_Reason"]
    stamped = context.get("DiagStamped") == reason
    return {
        "Status/State": context["OutImm_ExecState"],
        "Status/FaultActive": context["Error"] != 0,
        **diagnostic(app, reason,
                     context.get("DiagSinceDate", 0) if stamped else 0,
                     context.get("DiagSinceTime", 0) if stamped else 0,
                     io_join(app, name, context.get("OutImm_IoRoles", 0)),
                     held_description(app, name, context, catalogue)),
        **command_catalog(app, name),
        **command_timing(app, name, context),
    }


def command_timing(app, name: str, context: dict[str, Any]) -> dict[str, Any]:
    """TC3's Timing.Rows, as the HMI's command table reads them: one row per
    command ordinal, 1..8, each with its Count, Last, Minimum, Maximum and Avg.
    Every row is published for a module that takes commands, empty where no
    command has that ordinal or none has run; a module that takes none
    publishes no timing at all. TC3's LastCmdTime and Truncated stay on the
    controller: nothing reads them (O4)."""
    import fraktal_ab_generate as gen

    # Timing is a member of the commanded types alone (the library cylinder),
    # so a passive module's context simply has none.
    module = next((m for m in app.modules if m.name == name), None)
    if module is None or "TimCount" not in context:
        return {}
    by_ordinal = {c.ordinal: c for c in module.commands}
    values: dict[str, Any] = {}
    for row in range(gen.CMD_STATS):
        command = by_ordinal.get(row + 1)
        base = f"Timing/Rows[{row + 1}]"
        values[f"{base}/Id"] = row + 1 if command else 0
        values[f"{base}/Label"] = f"std.command.{command.name.lower()}" if command else ""
        for leaf, member in (("Count", "TimCount"), ("Last", "TimLast"),
                             ("Minimum", "TimMin"), ("Maximum", "TimMax"),
                             ("Avg", "TimAvg")):
            values[f"{base}/{leaf}"] = context[member][row] if command else 0
    return values


def unit_status(unit: dict[str, int], chart: dict[str, Any] | None) -> dict[str, Any]:
    """The root Unit's own members, beyond the Status every module carries."""
    values: dict[str, Any] = {
        "Status/State": (gen.STATE_ERROR if unit["Error"] else
                         gen.STATE_BUSY if unit["Running"] else
                         gen.STATE_DONE if unit["Complete"] else gen.STATE_READY),
        "Status/FaultActive": unit["Error"] != 0,
        # Core E_Mode ordinals, published verbatim: the HMI resolves them
        # against the same enum, which is why they have to be the same numbers.
        "ModeActivePublished": unit["Mode"],
        "GoodCount": unit["GoodCount"],
        "NokCount": unit["ScrapCount"],
        "ReworkCount": unit["ReworkCount"],
        "CurrentStep/StepNo": unit["Step"],
        # Core §3.4.2: the active run style, CONTINUOUS where none is declared.
        "RunStyle": unit.get("RunStyle", 0),
        "Decision/Default": unit["DecisionAnswer"],
    }
    # DiagReason is chosen on the controller (adopted fault, else held) and
    # stamped there; the adopted child's implicated I/O came with it.
    reason = unit.get("DiagReason", 0)
    stamped = unit.get("DiagStamped") == reason
    source = _module_path(APP, unit.get("ErrorSource", 0) + 1).rsplit(".", 1)[-1]
    values.update(diagnostic(
        APP, reason,
        unit.get("DiagSinceDate", 0) if stamped else 0,
        unit.get("DiagSinceTime", 0) if stamped else 0,
        io_join(APP, source, unit.get("DiagIoRoles", 0)) if unit.get("Error")
        else ("", "")))
    if chart is not None:
        values["CurrentStepElapsed"] = chart["CurrentStepMs"]
        # The §6.9 watchdog, not "the step has a pending reason": waiting at a
        # delay or for an operator is the step working, and TC3 flags only a
        # step that outran StallTime with nothing held.
        values["CurrentStepTimedOut"] = unit.get("StepTimedOut", 0) != 0
    return values


# E_ModeSwitchShield and E_ModeSwitchStyle, from the Core DUTs and pinned by
# test the way E_Mode is.
DIR_OUTPUT = 1
NODE_OFFLINE = 0
NODE_OPERATIONAL = 4
NODE_FAULT = 5
SHIELD_INTERRUPTIBLE = 0
STYLE_IMMEDIATE = 1


def mode_policy(app) -> dict[str, Any]:
    """Which modes this application offers, and how a switch behaves.

    Without this the HMI has no list of selectable modes and shows only the one
    that happens to be active - which is how a press declaring AUTO, MANUAL and
    HOME came to present as AUTO-only. The mapper builds its policy map from
    ``ModePolicy[ordinal + 1]``, skipping any index it cannot find, so an absent
    policy is indistinguishable from a mode the machine does not have.

    The values describe what the generated controller actually does, not what
    would be polite. A mode change there stands the chain down unconditionally -
    `Step := 0`, `Running := 0`, no confirmation and no wait for a safe point -
    so it is INTERRUPTIBLE and IMMEDIATE. Publishing CONFIRM or GRACEFUL would
    promise an operator a negotiation the controller will not hold.
    """
    values: dict[str, Any] = {}
    for mode in decl.declared_modes(app):
        index = mode + 1
        # What the mode bar actually offers. `supportedModes` is built from
        # these flags, and the mapper falls back to `[currentMode]` when the
        # list comes out empty - so an unpublished array does not render as "no
        # modes", it renders as "this machine has exactly one", which is a
        # confident lie rather than a visible gap. That is what a press
        # declaring AUTO, MANUAL and HOME looked like before this existed.
        values[f"SupportedModesPublished[{index}]"] = True
        # How a switch behaves once offered (Core §3.4.1). Separate concern:
        # ModePolicy governs leaving a mode, not whether it is listed.
        values[f"ModePolicy[{index}]/Shield"] = SHIELD_INTERRUPTIBLE
        values[f"ModePolicy[{index}]/Style"] = STYLE_IMMEDIATE
    # TC3's SupportedRunStylesPublished: what the step toggle offers (§3.4.2).
    # 1-based, as the mode flags above are; the mapper finds either form.
    for style in decl.RUN_STYLES:
        values[f"SupportedRunStylesPublished[{style + 1}]"] = style in app.run_styles
    return values


# TC3's ST_ReleaseReport holds 24 reasons, and the HMI re-reads exactly those
# 24 slots, in TF6100's array naming, the moment a request is acknowledged -
# its bulk read refuses the whole batch if any of them is unpublished. So all
# 24 are published, empty past Count, whatever this controller can fill.
REPORT_SLOTS = 24
REPORT_BASE = "HmiResponse/Report"


def release_report_values(app, report: dict[str, Any] | None,
                          catalogue: dict[int, str]) -> dict[str, Any]:
    """TC3's HmiResponse.Report, from the controller's report: each reason's
    text resolved through this controller's own catalogue, its owner as the
    module's qualified identity (TC3's SourcePath)."""
    report = report or {}
    count = min(report.get("Count", 0), gen.RELEASE_CAPACITY)
    values: dict[str, Any] = {
        f"{REPORT_BASE}/Released": report.get("Released", 0) != 0,
        f"{REPORT_BASE}/Count": count,
    }
    for slot in range(1, REPORT_SLOTS + 1):
        base = f"{REPORT_BASE}/Reasons/Reasons[{slot}]"
        if slot <= count:
            i = slot - 1
            source = report["Source"][i]
            owner = (app.name if source == 0 or source > len(app.modules)
                     else f"{app.name}.{app.modules[source - 1].name}")
            values.update({
                f"{base}/Description": catalogue.get(report["Key"][i], ""),
                f"{base}/ReasonCode": report["Reason"][i],
                f"{base}/SourcePath": owner,
                f"{base}/Kind": report["Kind"][i],
                f"{base}/Bypassable": False,      # §7.4: nothing here bypasses
            })
        else:
            values.update({f"{base}/Description": "", f"{base}/ReasonCode": 0,
                           f"{base}/SourcePath": "", f"{base}/Kind": 0,
                           f"{base}/Bypassable": False})
    return values


def mailbox_values(rows: dict[str, Any], response: dict[str, int],
                   request_sequence: int,
                   report: dict[str, Any] | None = None) -> dict[str, Any]:
    """The command mailbox as the HMI's repository reads it.

    ``opcua_repository.dart`` writes ``HmiRequest/*`` and then polls
    ``HmiResponse/{AckSequence, Accepted, Diagnostic}`` until the ack matches
    the sequence it wrote. It expects ``Diagnostic`` to be text, and the
    controller answers with a numeric key - Logix v33 ST cannot assign a string
    literal - so the key is resolved here.

    It is resolved against the **controller's own** Localization table, the one
    read in this same snapshot, rather than against the local declaration. A
    numeric key is only meaningful within the revision that published it, so
    resolving it from anywhere else would be reading this controller's answer
    through another build's catalogue.
    """
    import fraktal_ab_mailbox as mailbox

    catalogue = {row["NumericKey"]: row["PortableKey"]
                 for row in rows["Localization"]}
    key = response.get("DiagnosticKey", 0)
    return {
        "HmiRequest/Sequence": request_sequence & 0xffffffff,
        "HmiResponse/AckSequence": response.get("AckSequence", 0) & 0xffffffff,
        "HmiResponse/Accepted": response.get("Accepted", 0) != 0,
        # An unresolvable key is reported as such rather than as no reason at
        # all: blank would read as "accepted without comment".
        "HmiResponse/Diagnostic": (
            "" if key == 0
            else catalogue.get(key, f"{mailbox.UNKNOWN_KEY}#{key}")),
        **release_report_values(APP, report, catalogue),
    }


TOPOLOGY_ROOT_SUFFIX = "Fieldbus"


def topology(app, io_state: dict[str, dict[str, int]] | None) -> dict[str, Any]:
    """The §10.2 fieldbus view, from the declared channels and two live words.

    Split the way the HMI consumes it. **Identity** - the electrical tag, the
    description key, the address, the direction - comes from the committed
    declaration, because that is where it is authored and it needs no
    controller round trip. **State** - the bit, the fault, the link - comes
    from the module's own input/output words, because nothing else can know it.

    The declaration cannot lie about state and the controller cannot lie about
    identity, which is the division that keeps a stale build from publishing a
    channel the chassis does not have with values that look live.

    ``io_state`` is ``{address: {"input": word, "output": word,
    "fault": word}}``. None means the words were not read this cycle: the
    channels still publish their identity, with ``Quality`` FALSE so the HMI
    renders them unavailable rather than showing a confident zero. That is the
    same rule OPC UA Bad quality follows in `HMI_CONTRACT.md`.
    """
    if not app.io_modules:
        return {}
    root = f"{app.name}{TOPOLOGY_ROOT_SUFFIX}/Topology"
    values: dict[str, Any] = {
        f"{root}/NodeCount": len(app.io_modules),
        # The mapping is the declaration's own, and it was validated before
        # emission, so it is valid by construction here. A controller-side
        # publisher would have something to say; this one would be inventing
        # a doubt it cannot have.
        f"{root}/MappingValid": True,
        f"{root}/MappingDiagnostic": "",
    }
    for index, module in enumerate(app.io_modules, start=1):
        node = f"{root}/Nodes[{index}]"
        state = (io_state or {}).get(module.address)
        live = state is not None
        # Every channel's fault bit set is what an INHIBITED module reports,
        # and it is the honest answer for the press today: the module is there
        # and it is carrying nothing. Distinguish it from a partial fault, so
        # the HMI can say "offline" rather than "sixteen broken channels".
        faults = (state or {}).get("fault", 0)
        # Which outputs the controller is holding, and whether it would accept
        # a new force at all. Both are read FROM the controller: a gateway that
        # decided forcing was permitted would be answering a question only the
        # machine's own state can answer (§10.5.1).
        forced = (state or {}).get("forced", 0)
        force_permitted = bool((state or {}).get("forcePermitted", 0))
        mask = (1 << module.data_width) - 1
        inhibited = live and (faults & mask) == mask
        if not live:
            node_state = NODE_OFFLINE
        elif inhibited:
            node_state = NODE_OFFLINE
        elif faults:
            node_state = NODE_FAULT
        else:
            node_state = NODE_OPERATIONAL
        values.update({
            f"{node}/Name": module.name,
            f"{node}/DescriptionKey": module.description_key,
            f"{node}/TypeId": module.type_id,
            f"{node}/Address": module.address,
            f"{node}/State": node_state,
            f"{node}/LinkOk": node_state == NODE_OPERATIONAL,
            f"{node}/ParentIdx": 0,
            f"{node}/ChannelCount": len(module.channels),
        })
        for position, channel in enumerate(module.channels, start=1):
            leaf = f"{node}/Channels[{position}]"
            outward = channel.direction == DIR_OUTPUT
            word = (state or {}).get("output" if outward else "input", 0)
            faulted = bool(faults >> channel.bit & 1) if live else False
            values.update({
                # The electrical tag, verbatim. Never localized.
                f"{leaf}/Name": channel.name,
                f"{leaf}/DescriptionKey": channel.description_key,
                f"{leaf}/Address": channel_address(module, channel),
                f"{leaf}/Path": f"{module.name}.{channel.name}",
                # A station signal - a lamp, the two-hand buttons, air
                # pressure - belongs to the root Unit, not to a device module.
                # Publishing "" instead would cost it its alarm cross-link,
                # and the HMI resolves a channel's owning root from this path.
                f"{leaf}/ModulePath": (f"{app.name}.{channel.module_path}"
                                       if channel.module_path else app.name),
                f"{leaf}/Dir": channel.direction,
                f"{leaf}/Kind": channel.kind,
                f"{leaf}/BoolValue": bool(word >> channel.bit & 1) if live
                                     else False,
                f"{leaf}/AnalogValue": 0,
                f"{leaf}/Unit": channel.unit,
                f"{leaf}/Quality": live and not faulted,
                f"{leaf}/FaultActive": faulted,
                f"{leaf}/Diagnostic": "",
                # §10.5.1 forcing, and an OUTPUT only: forcing an input would
                # be a lie, because the module overwrites it every scan. The
                # request still travels the mailbox like every other command,
                # so AB §11.2.1 keeps its single command surface; the
                # controller applies the force and withdraws it.
                f"{leaf}/Forced": bool(forced >> channel.bit & 1)
                                  if outward and live else False,
                f"{leaf}/Forceable": outward and force_permitted,
            })
    return values


def model_status(app, unit: dict[str, int], codes=None) -> dict[str, Any]:
    """Core §3.8 changeover, as the HMI reads it.

    The catalogue of models comes from the declaration and the SELECTION comes
    from the controller, the same split the fieldbus view uses: the
    declaration cannot be wrong about which models exist and the controller
    cannot be wrong about which one is loaded.

    Ordinals are 1-based so 0 can mean "no model committed", which is what a
    station reads before its first changeover - and it is a real state, not a
    missing value. It publishes an empty code, and the HMI omits the chip
    rather than drawing an empty one.
    """
    if not app.models:
        return {}
    codes = codes if codes is not None else [m.code for m in app.models]
    ordinal = unit.get("ModelOrdinal", 0)
    values: dict[str, Any] = {
        "AvailableModelCount": len(codes),
        "ModelCapacity": app.model_capacity,
        "Model/ModelCode": (codes[ordinal - 1]
                            if 1 <= ordinal <= len(codes) else ""),
    }
    for index, code in enumerate(codes, start=1):
        values[f"AvailableModels[{index}]/ModelCode"] = code
    return values


def step_status(app, unit: dict[str, int],
                chart: dict[str, Any] | None = None) -> dict[str, Any]:
    """What the running chain is doing, by name.

    `Unit.Step` is a number and the HMI shows a sentence, so something has to
    resolve one to the other. This binding publishes no step table, so the
    gateway does it from the declaration - the live mode says which chain, the
    live step number says which step, and the declaration supplies its name.

    Without this the operator sees a blank where the guidance goes. A chain
    waiting on a decision - "Waiting for a model to be selected" - then looks
    exactly like a chain that did nothing at all, which is precisely how a
    changeover appears to hang.
    """
    step = current_step(app, unit)
    # Always published, empty when the step is not one this declaration knows.
    # See `decision_status` for why a path that comes and goes is not free.
    values: dict[str, Any] = {
        "CurrentStep/StepName": f"project.step.{step.name}" if step else "",
        # TC3's form, 'PressRam.RETRACT': the child and the command awaited.
        "CurrentStep/AwaitingLabel": (f"{step.module}.{step.command}"
                                      if step and step.module and step.command
                                      else ""),
        # TC3's M_Step ExpectedTime: a delay expects its duration (N170 and
        # N220 pass it), every other step T#0S. The controller resolves it
        # against the live recipe, because the watchdog times the step by it.
        "CurrentStep/ExpectedTime": unit.get("StepExpectedMs", 0) if step else 0,
    }
    time_class = step.time_class if step else "WORK"
    values["CurrentStep/TimeClass"] = decl.TIME_CLASSES.index(time_class)
    values["Starved"], values["Blocked"] = wait_attribution(app, unit)
    values.update(condition_records(step, unit, chart))
    return values


def current_step(app, unit: dict[str, int]):
    """The declared step the running mode's chain is on, or None."""
    chain = next((c for c in app.chains if c.mode_ordinal == unit.get("Mode")),
                 None)
    if chain is None:
        return None
    return next((s for s in chain.steps if s.number == unit.get("Step", 0)), None)


def wait_attribution(app, unit: dict[str, int]) -> tuple[bool, bool]:
    """§8.11.3 Starved and Blocked, as FB_UnitBase derives them: BUSY in a
    step classed as an upstream or a downstream wait. Derived every poll,
    never latched."""
    step = current_step(app, unit)
    time_class = step.time_class if step else "WORK"
    busy = not unit.get("Error") and bool(unit.get("Running"))
    return (busy and time_class == "WAIT_UPSTREAM",
            busy and time_class == "WAIT_DOWNSTREAM")


# Core E_MachineState (§8.11.3), pinned to the TwinCAT DUT by test, and the
# one E_Mode ordinal the classification reads.
MACHINE_STATES = {"PRODUCING": 0, "IDLE": 1, "BLOCKED": 2, "STARVED": 3,
                  "DOWN": 4, "CHANGEOVER": 5, "STOPPED": 6}
MODE_CHANGEOVER = 3


def machine_state(app, unit: dict[str, int],
                  active: dict[str, Any] | None) -> dict[str, Any]:
    """TC3's MachineState: one state from the fixed set, in its priority -
    a fault first, then the planned states, then line attribution, then
    producing or idle. Derived every poll from what the Unit publishes, as
    Starved and Blocked are; nothing on the controller is latched for it.

    TC3's STOPPED reads `_stopReq OR ABORTED`. Its Stop is graceful, so
    `_stopReq` is only ever up while the Unit is still BUSY - where PRODUCING
    wins - and STOPPED is in effect ABORTED: AB's `Aborted`, which its STOP
    sets and the reset clears.

    Nothing when the alarm log did not read: DOWN depends on its Blocking,
    and an IDLE that might have been DOWN is a figure nobody read."""
    if active is None:
        return {}
    starved, blocked = wait_attribution(app, unit)
    if unit["Error"] or active["Blocking"]:
        state = "DOWN"
    elif unit["Mode"] == MODE_CHANGEOVER:
        state = "CHANGEOVER"
    elif blocked:
        state = "BLOCKED"
    elif starved:
        state = "STARVED"
    elif unit["Running"]:
        state = "PRODUCING"
    elif unit["Aborted"]:
        state = "STOPPED"
    else:
        state = "IDLE"
    return {"MachineState": MACHINE_STATES[state]}


def sequence_slots(app) -> int:
    """How many §3.13 rows are published: the longest chain, since one mode
    session's rows are that mode's steps. Fixed, so the path set is too."""
    return min(max((len(c.steps) for c in app.chains), default=0),
               app.chart_steps)


def sequence_status(app, unit: dict[str, int],
                    chart: dict[str, Any] | None,
                    record_values: dict[str, dict[str, int]] | None = None
                    ) -> dict[str, Any]:
    """Core §3.13, the flow chart, as TC3's FB_UnitBase publishes it.

    The controller discovers each row when the step is first entered in this
    mode session (`RowEpochOf`/`RowOf`), keeps how long its last visit took
    (`LastMs`) and what a §6.9(e) report left on it (`WarnReason`). Everything
    here is either that record or the declaration's static half of the row,
    which TC3 serves through its manifest and this binding already holds.

    Nothing is accumulated from polls: a step shorter than a poll is still a
    row, because the controller recorded it (AGENTS: never move Visited,
    LastDuration or the marks to client-side accumulation).

    ErrorActive is always false, and truthfully: TC3 marks a row only for a
    §6.9(d) raise, and this binding's step vocabulary has none - an awaited
    child's fault is adopted by rollup, which TC3 does not mark either.
    """
    slots = sequence_slots(app)
    values: dict[str, Any] = {"SequenceViewEnabled": bool(app.chains)}
    # A row's expected time is its step's (decl.expected_member), read from
    # the live recipe; 0 when it states none or the recipe did not read.
    recipe = (record_values or {}).get(app.records[0].name, {}) if app.records else {}
    order = gen.ordered_steps(app)
    chain = next((c for c in app.chains if c.mode_ordinal == unit.get("Mode")),
                 None)
    by_number = {s.number: s for s in chain.steps} if chain else {}
    rows: list[tuple[int, int]] = []          # (row number, step index)
    if chart is not None and chain is not None:
        epoch = chart.get("RowEpoch", 0)
        count = chart.get("RowCount", 0)
        for index, number in enumerate(order):
            row = chart["RowOf"][index]
            if (chart["RowEpochOf"][index] == epoch and 1 <= row <= count
                    and number in by_number):
                rows.append((row, index))
    rows.sort()
    rows = rows[:slots]
    row_of_index = {index: position for position, (_, index) in
                    enumerate(rows, start=1)}
    values["SequenceStepCount"] = len(rows)
    notes: list[tuple[int, int, int]] = []    # (row, reason, source)
    for position in range(1, slots + 1):
        base = f"SequenceSteps[{position}]"
        if position <= len(rows):
            index = rows[position - 1][1]
            step = by_number[order[index]]
            warn = chart["WarnReason"][index]
            if warn:
                notes.append((position, warn, chart["WarnSource"][index]))
            values.update({
                f"{base}/StepNo": step.number,
                f"{base}/Branch": 0,
                f"{base}/StepName": f"project.step.{step.name}",
                f"{base}/AwaitingLabel": (f"{step.module}.{step.command}"
                                          if step.module and step.command else ""),
                f"{base}/AwaitsPath": (f"{app.name}.{step.module}"
                                       if step.module else ""),
                f"{base}/TimeClass": decl.TIME_CLASSES.index(step.time_class),
                f"{base}/ExpectedTime": recipe.get(decl.expected_member(step), 0)
                if decl.expected_member(step) else 0,
                f"{base}/Visited": True,
                f"{base}/LastDuration": chart["LastMs"][index],
                f"{base}/ErrorActive": False,
                f"{base}/WarningActive": bool(warn),
            })
        else:
            values.update({
                f"{base}/StepNo": 0, f"{base}/Branch": 0, f"{base}/StepName": "",
                f"{base}/AwaitingLabel": "", f"{base}/AwaitsPath": "",
                f"{base}/TimeClass": 0, f"{base}/ExpectedTime": 0,
                f"{base}/Visited": False, f"{base}/LastDuration": 0,
                f"{base}/ErrorActive": False, f"{base}/WarningActive": False,
            })
    values["SequenceAnnotationCount"] = len(notes)
    for position in range(1, slots + 1):
        base = f"SequenceAnnotations[{position}]"
        row, reason, source = (notes[position - 1] if position <= len(notes)
                               else (0, 0, 0))
        values.update({
            f"{base}/RowIdx": row,
            f"{base}/IsError": False,
            f"{base}/Key": reason_description(app, reason) if row else "",
            f"{base}/SourcePath": _module_path(app, source + 1) if row else "",
        })
    # One main line, no §6.12 legs: the cursor is live while the chain runs a
    # step - TC3's leg is active exactly while its action keeps recording - and
    # only when the chart's own view is of the step Unit.Step names.
    running = bool(unit.get("Running")) and not unit.get("Error")
    cursor = 0
    if running and chart is not None and \
            chart.get("ActiveStepNumber") == unit.get("Step"):
        index = order.index(unit["Step"]) if unit.get("Step") in order else -1
        cursor = row_of_index.get(index, 0)
    values["ActiveSteps[1]/RowIdx"] = cursor
    values["ActiveSteps[1]/Elapsed"] = (chart or {}).get("CurrentStepMs", 0) if cursor else 0
    values["ActiveSteps[1]/TimedOut"] = False
    return values


def condition_records(step, unit: dict[str, int],
                      chart: dict[str, Any] | None) -> dict[str, Any]:
    """Core §6.9(b): what the step is waiting for, one record per condition.

    The label is the declaration's; Ok is what the step itself wrote into
    Chart.CondOk this scan - the controller's evaluation, not one repeated
    here. They are joined only when the chart's ActiveStepNumber, read in the
    same tag as CondOk, is the step being named: for the one scan after a
    transition the chart still holds the previous step's view, and labelling
    it with the new step's names would state a condition nobody evaluated.

    Every slot is published every time, like the alarm log, so the path set
    does not change when the step does.
    """
    records = decl.step_conditions(step) if step else ()
    coherent = (chart is not None and step is not None
                and chart.get("ActiveStepNumber") == unit.get("Step"))
    ok = chart.get("CondOk", []) if coherent else []
    values: dict[str, Any] = {}
    for i in range(decl.MAX_STEP_CONDS):
        label = records[i][1] if coherent and i < len(records) else ""
        values[f"CurrentStep/Conds[{i + 1}]/Label"] = label
        values[f"CurrentStep/Conds[{i + 1}]/Ok"] = bool(label) and bool(
            ok[i] if i < len(ok) else 0)
    return values


# lib/domain/types.dart: enum AccessLevel { none, operator, technician,
# engineer, admin } and GatedAction's twelve members. Pinned like E_Mode.
ACCESS_NONE = 0
ACCESS_OPERATOR = 1
ACCESS_TECHNICIAN = 2
ACCESS_ENGINEER = 3
ACCESS_ADMIN = 4

# The ladder by name, for a deployment to name its own principal.
ACCESS_LEVELS = {
    "none": ACCESS_NONE,
    "operator": ACCESS_OPERATOR,
    "technician": ACCESS_TECHNICIAN,
    "engineer": ACCESS_ENGINEER,
    "admin": ACCESS_ADMIN,
}
GATED_ACTION_COUNT = 12


def access_status(app, level: int = ACCESS_OPERATOR, held=None) -> dict[str, Any]:
    """Project the controller-owned session and policy without granting a role.

    Missing enabled-provider state fails closed. The deployment level only
    bounds the pre-login display; authenticated roles come from the PLC.
    Legacy declarations (access_users=None) retain their explicit deployment
    display level and open policy, with LOGIN refused by name.
    """
    if app.access_users is not None:
        import fraktal_ab_access as access
        values = access.status(app, held)
        # The deployment level is now a pre-login display ceiling. It never
        # creates PLC authority; a logged-in user's level is the PLC's alone.
        if values and not values['Access/CurrentUser']:
            values['Access/CurrentLevel'] = min(level, values['Access/CurrentLevel'])
        return values
    values: dict[str, Any] = {
        "Access/CurrentLevel": level,
        "Access/CurrentUser": "",
        # No login to fail, and no session to time out: both are false rather
        # than absent, because the mapper reads a missing flag as a default
        # and a missing timeout as zero anyway - saying so is honest and
        # keeps the gate able to check it.
        "Access/LoginFailed": False,
        "Access/Policy/SessionTimeout": 0,
    }
    for index in range(1, GATED_ACTION_COUNT + 1):
        values[f"Access/Policy/Required[{index}]"] = ACCESS_NONE
    return values


CFG_TYPE_DURATION = 3


def config_page(app, rows: dict[str, Any],
                record_values: dict[str, dict[str, int]] | None,
                model_values: list[dict[str, int]] | None = None,
                model: int = 0, data_levels=None) -> dict[str, Any]:
    """Core 3.10.2 — the configuration page a client reads after QUERY_CONFIG.

    Assembled from the controller's own WriteCapabilities and Localization
    tables, read in this same snapshot, plus the live value out of the record
    tag. Not from the local declaration: a numeric key means something only
    within the revision that published it, and the whole claim of this binding
    is that a client discovers the station from the controller.

    It is published unpaged because it fits: the page contract carries a
    PageCount so a client loops, and this station answers 1. A binding that
    outgrows one page pages here, and the client needs no change for it.

    The value travels as TEXT in the entry, which is the shape the client
    reads, and an entry whose value could not be read is left out entirely
    rather than shown as zero — a dwell time an operator believes is 0 ms is
    worse than a field that is missing.
    """
    capabilities = rows.get("WriteCapabilities") or []
    if not capabilities:
        return {}
    catalogue = {row["NumericKey"]: row["PortableKey"]
                 for row in rows["Localization"]}
    values = record_values or {}
    records = {r.name: r for r in app.records}

    entries: list[dict[str, Any]] = []
    for row in capabilities:
        if app.access_users is not None:
            import fraktal_ab_data_access as data
            read_level, write_level, readable = data.entry_levels(data_levels, row['CapabilityIndex'], app=app)
        else:
            read_level, write_level, readable = -1, -1, True
        path = catalogue.get(row["PathKey"], "")
        if not path:
            continue
        # `<Record>.<Member>`, relative to the root (manifest.field_path). It
        # was `<App>.<Record>.<Member>` and this tested for three parts - which
        # after the relative-key change would have dropped EVERY entry without
        # a word, the page empty and the configuration tab blank.
        parts = path.split(".")
        if len(parts) < 2:
            continue
        record, member = parts[-2], parts[-1]
        held = values.get(record, {})
        # Core §3.8a: a model-scoped value has one set of numbers per model.
        # `model` 0 is the RUNNING record - what the press is configured as
        # now - and 1..N is that model's stored values, which is what the
        # client asks for when an operator picks another model to edit.
        declared = records.get(record)
        scoped = declared is not None and gen.is_model_scoped(app, declared, member)
        if readable and scoped and model:
            stored = (model_values or [])
            if not 1 <= model <= len(stored) or member not in stored[model - 1]:
                continue
            held = stored[model - 1]
        elif readable and member not in held:
            continue
        entries.append({
            "Scope": app.name,
            # The browse fragment the client files this under. Config/<leaf>
            # rather than the record's type name: an operator reads "the dwell
            # time of this press", not which UDT it happens to live in.
            "Item": f"Config/{member}",
            "ValueText": str(held[member]) if readable else "",
            "WriteKey": catalogue.get(row["WriteKeyKey"], ""),
            # The published revision, so a client cannot write against a
            # capability from a build this controller no longer runs. It must
            # be non-zero or the client treats the value as read-only.
            "WriteRevision": manifest.config_revision(app),
            "ConfigKind": row["ConfigKind"],
            "ValueType": row["ValueType"],
            "Writable": True,
            "RequiresReady": row["RequiresReady"] != 0,
            "HasMinimum": True,
            "HasMaximum": True,
            "Minimum": row["Minimum"],
            "Maximum": row["Maximum"],
            "Unit": "",
            "LabelKey": catalogue.get(row["LabelKey"], ""),
            "EnumDomain": "",
            "UnitCode": row["UnitCode"],
            "EnumLabelKey": "",
            "ClassId": catalogue.get(row.get("ClassKey", 0), ""),
            "ReadLevel": read_level,
            "WriteLevel": write_level,
            "Readable": readable,
            # The client offers "another model" only when the controller says
            # something is model-scoped, and then asks for that model's page.
            "ModelScoped": scoped,
            "CaptureSource": catalogue.get(row.get("CaptureSourceKey", 0), ""),
            "CanCapture": bool(row.get("CaptureSourceKey", 0)),
        })

    out: dict[str, Any] = {
        # HMI_CONTRACT: "cache manifest values and re-fetch on
        # Status/ConfigRev". Without it the client computes an empty signature
        # and never asks for the page at all - the whole surface is served and
        # nothing requests it, which is exactly how editable configuration
        # first shipped invisible.
        #
        # It covers the VALUES as well as the build, because this binding puts
        # the live value in the entry. A revision that moved only on a new
        # download would leave an accepted edit showing its old number until
        # the next one.
        "Status/ConfigRev": _config_revision(app, entries),
        "HmiResponse/ConfigPage/PageCount": 1,
        "HmiResponse/ConfigPage/EntryCount": len(entries),
    }
    for index, entry in enumerate(entries, start=1):
        for name, value in entry.items():
            out[f"HmiResponse/ConfigPage/Entries[{index}]/{name}"] = value
    return out


def _controller_time(date: int, time: int) -> Any:
    """The controller clock's two DINTs as ISO 8601 UTC, or 0 for "none".

    `yyyymmdd` and `hhmmssmmm` from WallClockTime.DateTime, which is UTC. 0 is
    what an unset stamp holds, and it decodes as "no time" in the client -
    which for GoneAt means "still open", as it should. A stamp that does not
    decode to a real date is reported as none rather than guessed at.
    """
    if date <= 0:
        return 0
    year, month, day = date // 10000, (date // 100) % 100, date % 100
    hour, minute = time // 10_000_000, (time // 100_000) % 100
    second, millis = (time // 1000) % 100, time % 1000
    if not (1 <= month <= 12 and 1 <= day <= 31 and hour < 24
            and minute < 60 and second < 60):
        return 0
    return (f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:"
            f"{second:02d}.{millis:03d}Z")


def _alarm_event(app, columns: dict[str, list[int]], prefix: str,
                 index: int) -> dict[str, Any]:
    """One event, in the field set the client's _alarmEvent reads."""
    def col(name: str) -> int:
        return columns[f"{prefix}{name}"][index]

    reason = col("ReasonCode")
    source = _module_path(app, col("SourceModuleId"))
    io_tag, io_address = io_join(app, source.rsplit(".", 1)[-1],
                                 col("IoRoles") if f"{prefix}IoRoles" in columns
                                 else 0)
    return {
        "State": col("State"),
        "ReasonCode": reason,
        # A registered project reason names its own text; a Core reason is
        # described by the client from the code (reasonDescriptionKey), and an
        # unregistered one has nothing true to say.
        "Description": reason_description(app, reason),
        "Severity": col("Severity"),
        "ResetClass": col("ResetClass"),
        "SourcePath": source,
        "ComeAt": _controller_time(col("ComeDate"), col("ComeTime")),
        "GoneAt": _controller_time(col("GoneDate"), col("GoneTime")),
        "Duration": col("DurationMs"),
        "Shelved": bool(col('Shelved')),
        "IoTag": io_tag,
        "IoAddress": io_address,
        "ComeTimeSynchronized": TIME_SYNCHRONIZED,
        "GoneTimeSynchronized": TIME_SYNCHRONIZED,
        "ResetTimeSynchronized": TIME_SYNCHRONIZED,
        "ShelfTimeSynchronized": TIME_SYNCHRONIZED,
    }


def alarm_meta_status(rows: dict[str, Any]) -> dict[str, Any]:
    """Core §8.9 rationalization, per reason: what to do and what it means.

    From the controller's Rationalization table, resolved through the
    controller's OWN Localization table read in the same snapshot, the same
    rule config_page follows. This is what turns an alarm on the panel from a
    reason code into an instruction: every row carries the operator action and
    the consequence of leaving it.
    """
    catalogue = {row["NumericKey"]: row["PortableKey"]
                 for row in rows["Localization"]}
    meta = rows.get("Rationalization") or []
    out: dict[str, Any] = {"AlarmLog/MetaCount": len(meta)}
    for index, row in enumerate(meta, start=1):
        base = f"AlarmLog/Meta[{index}]"
        out[f"{base}/ReasonCode"] = row["ReasonCode"]
        out[f"{base}/OperatorAction"] = catalogue.get(row["ActionKey"], "")
        out[f"{base}/Consequence"] = catalogue.get(row["ConsequenceKey"], "")
        out[f"{base}/Priority"] = row["Priority"]
        out[f"{base}/Category"] = row["Category"]
        out[f"{base}/Shelvable"] = bool(row["Shelvable"])
    return out


def alarm_log_status(app, active: dict[str, Any] | None,
                     ring: dict[str, Any] | None) -> dict[str, Any]:
    """Core §8.3 — the alarm log, in the shape the client reads.

    EVERY slot is published every time, empty or not. The client skips a
    closed active slot and a ring slot with no source or time, so empty slots
    cost nothing to show - and publishing only the occupied ones would make
    the path set change whenever an alarm came or went, which moves
    discoveryRevision and invalidates every targeted read in flight.

    A log that did not read publishes nothing, rather than an empty log: "no
    alarms" and "could not read the alarms" must not look the same.
    """
    if active is None:
        return {}
    # Truncated is kept on the controller and described in the manifest, and
    # NOT published here: no client reads it, and a published field nobody
    # reads is surface everyone pays for.
    out: dict[str, Any] = {
        "AlarmLog/RingHead": active.get("RingHead", 0),
        "AlarmLog/Blocking": bool(active.get("Blocking", 0)),
    }
    for index in range(gen.ALARM_ACTIVE):
        for key, value in _alarm_event(app, active, "Act", index).items():
            out[f"AlarmLog/Active[{index + 1}]/{key}"] = value
    if ring is not None:
        for index in range(gen.ALARM_RING):
            for key, value in _alarm_event(app, ring, "Ring", index).items():
                out[f"AlarmLog/Ring[{index + 1}]/{key}"] = value
    return out


def config_persist_status(app, persist: dict[str, int] | None) -> dict[str, Any]:
    """Core §3.8b — whether this station's configuration is actually safe.

    Published on every root, including when everything is fine, because a
    client renders "no problem" and "no answer" identically and only one of
    them is something anyone can check.

    Restore and document durability are controller-owned status:

    * **Restore** is real. On its first scan the controller compares the
      retained StationCfg's SchemaVersion against the declared contract and
      raises ``RestoreLost`` when a commissioned image was rejected.
    * **Document durability** waits for a gateway file-store receipt when
      parameter sets are enabled. Failure or expiry remains visible here.
      This does not establish physical retention of ordinary live writes.

    ``LostModuleId`` travels as a manifest ordinal and is resolved to a
    canonical path here, the way every other identity on this binding is: the
    controller carries numbers, the client is handed paths.
    """
    if persist is None:
        return {}
    return {
        "ConfigPersist/Pending": bool(persist.get("Pending", 0)),
        "ConfigPersist/Failed": bool(persist.get("Failed", 0)),
        "ConfigPersist/WindowMs": persist.get("WindowMs", 0),
        # Zero decodes as "nothing pending" in the client's timestamp reader,
        # which is exactly what it means.
        "ConfigPersist/PendingSince": persist.get("PendingSince", 0),
        "ConfigPersist/StorePresent": bool(persist.get("StorePresent", 0)),
        "ConfigPersist/StoreKind": persist.get("StoreKind", 0),
        "ConfigPersist/RestoreLost": bool(persist.get("RestoreLost", 0)),
        "ConfigPersist/RestoreAcknowledged":
            bool(persist.get("RestoreAcknowledged", 0)),
        "ConfigPersist/LostPath":
            _module_path(app, persist.get("LostModuleId", 0)),
        "ConfigPersist/RestorePolicy": persist.get("RestorePolicy", 0),
    }


def _config_revision(app, entries: list[dict[str, Any]]) -> int:
    """A positive DINT that changes whenever the served configuration does.

    Derived, never counted: a counter would have to be stored somewhere, and
    the one place that survives a restart is the controller, which has no
    business tracking what a client cached.
    """
    import hashlib

    material = "|".join(
        [str(manifest.config_revision(app))]
        + [f"{e['WriteKey']}={e['ValueText']}:{e['ReadLevel']}:{e['WriteLevel']}:{e['Readable']}" for e in entries])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


def _module_path(app, ordinal: int) -> str:
    """Canonical path of a declared module by 1-based ordinal, or ''.

    Ordinal 1 is the root itself; the declared modules follow in order, which
    is the order the manifest's Modules table carries them in.
    """
    if ordinal <= 0:
        return ""
    if ordinal == 1:
        return app.name
    index = ordinal - 2
    if index < len(app.modules):
        return f"{app.name}.{app.modules[index].name}"
    return ""


def decision_status(app, unit: dict[str, int]) -> dict[str, Any]:
    """The question the chain is waiting on, if it is waiting on one.

    The HMI shows a decision card only when a PROMPT is present, so a chain
    parked on a decision with nothing published looks exactly like a chain
    that stopped. The controller publishes the ID; the text is declared, and
    resolved here against it.
    """
    if not app.decisions:
        return {}
    identifier = unit.get("DecisionId", 0)
    decision = next((d for d in app.decisions if d.identifier == identifier),
                    None)

    # The SAME KEYS every cycle, empty when nothing is pending. Publishing
    # them only while a decision is live changes the path set, and the gateway
    # raises its discovery revision whenever that set changes - which
    # invalidates every targeted read a client has in flight. The HMI polls
    # HmiResponse/AckSequence that way, so a decision appearing or ending
    # mid-request made it miss the acknowledgement and report a command that
    # had actually succeeded as blocked. A stable surface is not a nicety
    # here; a conditional one breaks unrelated commands.
    width = max(len(d.option_keys) for d in app.decisions)
    values: dict[str, Any] = {
        "Decision/Prompt": decision.prompt_key if decision else "",
    }
    for index in range(1, width + 1):
        key = ""
        if decision and index <= len(decision.option_keys):
            key = decision.option_keys[index - 1]
        values[f"Decision/Options[{index}]"] = key
    return values


def project(header: dict[str, Any], rows: dict[str, Any],
            unit: dict[str, int], contexts: dict[str, dict[str, int]],
            chart: dict[str, Any] | None = None,
            mailbox_state: dict[str, Any] | None = None,
            io_state: dict[str, dict[str, int]] | None = None,
            persist: dict[str, int] | None = None,
            record_values: dict[str, dict[str, int]] | None = None,
            access_level: int = ACCESS_OPERATOR,
            model_values: list[dict[str, int]] | None = None,
            alarm_state: tuple | None = None,
            oee_state: dict[str, Any] | None = None,
            profiler_state: dict[str, Any] | None = None,
            flags_state: dict[str, Any] | None = None,
            health_state: tuple | None = None,
            access_state: dict[str, Any] | None = None,
            access_audit: dict[str, Any] | None = None,
            data_policy: dict[str, Any] | None = None,
            data_levels: dict[str, Any] | None = None,
            model_codes: list[str] | None = None,
            line_state: tuple | None = None) -> dict[str, Any]:
    """The snapshot document, from a validated manifest and the live contexts."""
    validate(header)

    values: dict[str, Any] = {}
    values[f"{APP.name}/Features/CaptureEnabled"] = any(
        row.get("CaptureSourceKey", 0) for row in rows.get("WriteCapabilities", []))
    values[f"{APP.name}/Features/ExportCurrentConfig"] = APP.config_sets
    model_pages: dict[int, dict[str, Any]] = {}
    described = modules(rows)
    for module in described:
        base = module["base"]
        values[f"{base}/Status/Name"] = module["identity"]
        values[f"{base}/Status/ModuleType"] = module["type"]
        values[f"{base}/Status/DisplayNameKey"] = module["displayNameKey"]
        if module["typeKey"]:
            values[f"{base}/Status/TypeKey"] = module["typeKey"]
        if module["type"] == MODULE_TYPE_UNIT:
            for suffix, value in unit_status(unit, chart).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in mode_policy(APP).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in model_status(APP, unit, model_codes).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in step_status(APP, unit, chart).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in sequence_status(APP, unit, chart,
                                                 record_values).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in access_status(APP, access_level, access_state).items():
                values[f"{base}/{suffix}"] = value
            if APP.access_users is not None:
                import fraktal_ab_data_access as data
                for suffix, value in data.policy_status(APP, rows, data_policy).items():
                    values[f"{base}/{suffix}"] = value
            for suffix, value in config_persist_status(APP, persist).items():
                values[f"{base}/{suffix}"] = value
            if APP.config_sets:
                import fraktal_ab_sets as sets
                values.update(sets.empty_values(base))
            active_log, ring_log = alarm_state or (None, None)
            for suffix, value in alarm_log_status(APP, active_log, ring_log).items():
                values[f"{base}/{suffix}"] = value
            if APP.access_users is not None:
                import fraktal_ab_access as access
                for suffix, value in access.audit_status(APP, rows, access_audit, ring_log).items():
                    values[f"{base}/{suffix}"] = value
            for suffix, value in machine_state(APP, unit, active_log).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in alarm_meta_status(rows).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in oee_status(APP, oee_state, unit,
                                            record_values).items():
                values[f"{base}/{suffix}"] = value
            if APP.line is not None:
                import fraktal_ab_line as line
                for suffix, value in line.projection(APP, *(line_state or (None, None)), rows=rows).items():
                    values[f'{base}/{suffix}'] = value
            for suffix, value in profiler_status(APP, profiler_state).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in state_flags_status(APP, flags_state).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in system_health_status(
                    APP, *(health_state or (None, None))).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in config_page(APP, rows, record_values,
                                             model_values, 0, data_levels).items():
                values[f"{base}/{suffix}"] = value
            # Every other model's page, computed now from values already read,
            # so a client that asks for one is answered without a second trip
            # to the controller. Only the model-scoped entries differ; the path
            # set is identical for every model, so answering a different model
            # never moves discoveryRevision.
            for number in range(1, len(model_values or []) + 1):
                page = config_page(APP, rows, record_values, model_values,
                                   number, data_levels)
                if page:
                    model_pages[number] = {
                        f"{base}/{suffix}": value
                        for suffix, value in page.items()}
            for suffix, value in decision_status(APP, unit).items():
                values[f"{base}/{suffix}"] = value
            if mailbox_state is not None:
                for suffix, value in mailbox_values(
                        rows, mailbox_state["response"],
                        mailbox_state["requestSequence"],
                        mailbox_state.get("report")).items():
                    values[f"{base}/{suffix}"] = value
        else:
            name = module["identity"].rsplit(".", 1)[-1]
            context = contexts.get(name)
            if context is None:
                raise ProjectionRefused(
                    f"module {module['identity']} is published but its context "
                    "was not read; refusing to project a module without state")
            catalogue = {row["NumericKey"]: row["PortableKey"]
                         for row in rows["Localization"]}
            for suffix, value in module_status(context, APP, name, catalogue).items():
                values[f"{base}/{suffix}"] = value

    # The fieldbus hangs off its own root, not under a module, exactly as TC3
    # publishes GVL_<Project>Fieldbus.Topology: a bus node is not a Fraktal
    # module and giving it a module's browse path would make the HMI treat it
    # as one.
    values.update(topology(APP, io_state))

    return {
        "schema": SCHEMA,
        "schemaVersion": SCHEMA_VERSION,
        "values": values,
        # Not sent to a client: the gateway picks the page for the model each
        # connection last asked about and overlays it, then drops this key.
        "configPages": model_pages,
        "dataValues": {},
        # The mapper's fail-closed guard reads this. The manifest already says
        # whether it fits, so the two agree by construction rather than by a
        # second opinion.
        "truncated": header["Truncated"] != 0,
        "nodeCount": len(values),
        "moduleCount": len(described),
        "configRevision": header["ConfigRevision"],
        "contentHash": header["ContentHash"],
        "absent": [{"path": path, "reason": reason} for path, reason in ABSENT],
    }


def verify_serial(comm: Any, expected: str) -> tuple[str, bool]:
    """The controller's serial, and whether it is the one we were told to read.

    Read-only: the same ``GetDeviceProperties`` identity read the S1 tools use.
    A gateway pins one controller and checks before it trusts a manifest, whose
    ContentHash is identical across builds and cannot by itself tell two
    controllers apart.
    """
    from fraktal_ab_s16_execute import _normalize_serial, _status, _value

    identity = comm.GetDeviceProperties()
    device = _value(identity)
    if device is None:
        raise ReadFailed(f"identity read failed: {_status(identity)}")
    serial = _normalize_serial(getattr(device, "SerialNumber", 0))
    return serial, serial == _normalize_serial(expected)


class ReadPlan:
    """Per-connection native caches; tiers are intersections of all viewers.

    Logix reads whole native records. A group stays fast when any of its
    projected leaves is fast. Excluded groups refresh only for targeted reads;
    slow groups have a one-second heartbeat. Core contexts remain cyclic.
    """

    def __init__(self, clock=None, budget=None):
        import time
        self.clock = clock or time.monotonic
        self.budget = budget if budget is not None else APP.read_budget
        self.slow, self.excluded, self.paths, self.forced = frozenset(), frozenset(), (), frozenset()
        self.manifest = None
        self.groups = {}

    def set_tiers(self, slow, excluded, paths):
        self.slow, self.excluded, self.paths = frozenset(slow), frozenset(excluded), tuple(paths)

    def targeted(self, paths):
        self.forced = frozenset(paths)

    def group(self, name, prefixes, read):
        import time
        paths = {p for p in self.paths if any(p.startswith(prefix) for prefix in prefixes)}
        old = self.groups.get(name)
        forced = any(any(p.startswith(prefix) for prefix in prefixes) for p in self.forced)
        excluded = bool(paths) and paths <= self.excluded
        slow = bool(paths) and paths <= (self.slow | self.excluded)
        due = (old is None or forced or not slow or
               (not excluded and self.clock() - old[1] >=
                (self.budget.slow_period_ms / 1000 if self.budget else 1)))
        if due:
            tick, stamp = self.clock(), str(time.time_ns() // 1000)
            value = read()
            old = (value, tick, stamp, prefixes)
            self.groups[name] = old
        return old[0]

    def metadata(self, doc):
        for value, tick, stamp, prefixes in self.groups.values():
            paths = {p for p in self.paths if any(p.startswith(prefix) for prefix in prefixes)}
            tier = 'slow' if paths and paths <= (self.slow | self.excluded) else 'fast'
            for path, scalar in doc['values'].items():
                if any(path.startswith(prefix) for prefix in prefixes):
                    doc['dataValues'][path] = dict(value=scalar, status=0 if value is not None else 0x80320000,
                                                  serverTimestampUs=stamp,
                                                  ageMs=max(0, (self.clock() - tick) * 1000), tier=tier)
        self.paths = tuple(doc['values'])
        self.forced = frozenset()
        return doc


def read_document(comm: Any,
                  access_level: int = ACCESS_OPERATOR, *, plan=None) -> dict[str, Any]:
    """Read the live station off an open controller and project it. Read-only.

    The imports are deferred so the pure ``project`` stays importable without
    pylogix or the reader/execute tools - the projection unit test relies on
    that - while this stays the single source of the live-read sequence, shared
    by the CLI below and by the gateway.
    """
    import fraktal_ab_manifest_read as reader
    import fraktal_ab_press_execute as execute

    payload, status, _ = reader._read_raw(comm, manifest.header_tag(APP))
    if payload is None:
        raise ReadFailed(f"manifest header did not read: {status}")
    header = reader.decode_header(payload)
    validate(header)
    plan = plan or ReadPlan()
    if plan.manifest is None or plan.manifest[0] != header:
        rows = {table.name: reader.read_table(comm, table)["rows"]
                for table in manifest.tables(APP)}
        rows = {name: read[:header[f"{name}Count"]] for name, read in rows.items()}
    else:
        rows = plan.manifest[1]

    unit = execute.read_unit(comm)
    chart = execute.read_chart(comm)
    contexts = {m.name: execute.read_module(comm, m.name) for m in APP.modules}
    if unit is None or any(c is None for c in contexts.values()):
        raise ReadFailed("a live context did not read; refusing to project")

    import fraktal_ab_models as models
    codes = models.read(comm, APP)
    # Core 3.8b live documents are rendered from these same reads; nothing is
    # read twice and the read order is the one the projection always had.
    kept: dict[str, Any] = {}

    def keep(name, value):
        kept[name] = value
        return value
    doc = project(header, rows, unit, contexts, chart, read_mailbox(comm),
                   plan.group('io', (APP.name + 'Fieldbus/',), lambda: read_io(comm)), read_persist(comm),
                   keep('records', read_records(comm)),
                   access_level, keep('banks', read_models(comm, len(codes))), read_alarm_log(comm),
                   read_oee(comm), plan.group('profiler', (APP.name + '/Profiler/',), lambda: read_profiler(comm)), read_state_flags(comm),
                   read_system_health(comm), keep('access', read_access(comm)),
                   plan.group('accessAudit', (APP.name + '/AlarmLog/Ring[',), lambda: read_access(comm, audit=True)),
                   read_data_access(comm, policy=True), read_data_access(comm), codes,
                   read_line(comm))
    if decl.live_documents(APP):
        import fraktal_ab_live as live
        # Not sent to a client: the gateway's document keeper consumes it.
        doc["liveConfig"] = live.capture(APP, unit, kept['records'], kept['banks'], codes, kept['access'])
    # Validate the same coherence token after all table AND live reads. Cache a
    # manifest only after both headers agree; a torn station never becomes Good.
    after, status, _ = reader._read_raw(comm, manifest.header_tag(APP))
    if after is None:
        raise ReadFailed(f'manifest trailing header did not read: {status}')
    if reader.decode_header(after) != header:
        raise ProjectionRefused('manifest changed during the station read; rediscover')
    plan.manifest = (header, rows)
    return plan.metadata(doc)


def read_data_access(comm, policy=False):
    if APP.access_users is None:
        return None
    import fraktal_ab_data_access as data
    import fraktal_ab_press_execute as execute
    return execute.read_layout(comm, data.tag(APP, 'Policy' if policy else 'Levels'),
                               data.policy_members(APP) if policy else data.levels_members(APP))


def read_access(comm, audit=False):
    if APP.access_users is None:
        return None
    import fraktal_ab_access as access
    import fraktal_ab_press_execute as execute
    return execute.read_layout(comm, access.tag(APP, 'Audit' if audit else 'State'),
                               access.audit_members() if audit else access.state_members(APP))


def read_config_audit(comm):
    # Host/on-demand read. Growing audit history must not change the HMI's
    # discovered path set while it is waiting for a command acknowledgement,
    # or add an unconsumed table to every cyclic snapshot (Core O4).
    import fraktal_ab_config as config
    import fraktal_ab_press_execute as execute
    if not gen.editable_values(APP):
        return None
    return execute.read_layout(comm, config.audit_tag(APP), config.audit_members())


def config_audit_status(app, rows, audit):
    """Resolve the PLC's bounded write audit through its own manifest keys."""
    if not gen.editable_values(app):
        return {}
    import fraktal_ab_config as config
    import fraktal_ab_mailbox as mailbox
    held = audit or {}
    catalogue = {r["NumericKey"]: r["PortableKey"] for r in rows.get("Localization", [])}
    caps = {r["CapabilityIndex"]: r for r in rows.get("WriteCapabilities", [])}
    count = min(max(held.get("Count", 0), 0), config.AUDIT_CAPACITY)
    head = held.get("Head", 0)
    out = {"ConfigAudit/Present": audit is not None, "ConfigAudit/EntryCount": count}
    for row in range(count):
        slot = (head - 1 - row) % config.AUDIT_CAPACITY
        cap = caps.get(held["Capability"][slot], {})
        offset = slot * mailbox.USER_LENGTH
        length = min(max(held["UserLength"][slot], 0), mailbox.USER_LENGTH)
        entry = {"Sequence": held["Sequence"][slot], "Kind": held["Kind"][slot],
                 "Scope": app.name, "WriteKey": catalogue.get(cap.get("WriteKeyKey"), ""),
                 "ValueText": str(held["Value"][slot]),
                 "CaptureSource": catalogue.get(held["SourceKey"][slot], ""),
                 "Source": "capture" if held["Kind"][slot] == mailbox.CAPTURE_CONFIG else "client",
                 "ModelOrdinal": held['ModelOrdinal'][slot], "WriteRevision": held['Revision'][slot],
                 "Timestamp": _controller_time(held["Date"][slot], held["Clock"][slot]),
                 "User": bytes(v & 255 for v in held["UserBytes"][offset:offset + length]).decode("utf-8", errors="replace")}
        for name, value in entry.items():
            out[f"ConfigAudit/Entries[{row + 1}]/{name}"] = value
    return out


def oee_factors(run_ms: int, down_ms: int, good: int, nok: int,
                ideal_ms: int) -> dict[str, Any]:
    """TC3's _M_OeeCompute, for the live figure and every sample alike.

    Availability = run / (run + down); idle is published but excluded.
    Performance = ideal x parts / run, capped at 1, only with an ideal cycle.
    Quality = good / parts. OEE is the product of the VALID factors only; an
    invalid factor is omitted and published as 0, never assumed 100 % (O7)."""
    good, nok = max(good, 0), max(nok, 0)
    parts = good + nok
    a_valid = run_ms + down_ms > 0
    p_valid = ideal_ms > 0 and run_ms > 0
    q_valid = parts > 0
    a = run_ms / (run_ms + down_ms) if a_valid else 0.0
    p = min(1.0, ideal_ms * parts / run_ms) if p_valid else 0.0
    q = good / parts if q_valid else 0.0
    oee, valid = 1.0, False
    for ok, factor in ((a_valid, a), (p_valid, p), (q_valid, q)):
        if ok:
            oee, valid = oee * factor, True
    return {"Availability": a, "AvailValid": a_valid, "Performance": p,
            "PerfValid": p_valid, "Quality": q, "QualValid": q_valid,
            "Oee": oee if valid else 0.0, "OeeValid": valid}


def _ms(oee: dict[str, Any], bucket: str, index: int | None = None) -> int:
    if index is None:
        return oee[f"{bucket}S"] * 1000 + oee[f"{bucket}Ms"]
    return oee[f"Smp{bucket}S"][index] * 1000 + oee[f"Smp{bucket}Ms"][index]


def oee_status(app, oee: dict[str, Any] | None, unit: dict[str, int],
               record_values: dict[str, dict[str, int]] | None) -> dict[str, Any]:
    """TC3's Oee and OeeTrend[1..60], as the HMI's OEE card reads them.

    Nothing when the OEE tag did not answer: a card of zeros would be a figure
    nobody read. A sample is shown only from the current reset epoch, which
    is how RESET_OEE clears the ring without touching sixty slots.

    Two of TC3's members are deliberately not published. A sample's own A, P
    and Q: nothing reads them (the HMI's sparkline is OEE alone), they are 180
    paths in every snapshot, and the ring keeps the accounting they derive
    from, so they come back in three lines the day a reader does (O4). And
    Oee.IdealCycleMs: the ideal cycle is published once already, as the
    model's editable value on the configuration page (O9)."""
    import fraktal_ab_generate as gen

    if oee is None:
        return {}
    ideal = 0
    if app.ideal_cycle_member and app.records:
        ideal = (record_values or {}).get(app.records[0].name, {}).get(
            app.ideal_cycle_member, 0)
    run, down = _ms(oee, "Run"), _ms(oee, "Down")
    values: dict[str, Any] = {"Oee/RunMs": run, "Oee/DownMs": down,
                              "Oee/IdleMs": _ms(oee, "Idle")}
    for name, value in oee_factors(run, down, unit["GoodCount"] - oee["GoodBase"],
                                   unit["ScrapCount"] - oee["NokBase"], ideal).items():
        values[f"Oee/{name}"] = value
    values["OeeTrendHead"] = oee["Head"]
    for slot in range(gen.OEE_SAMPLES):
        current = oee["SmpEpoch"][slot] == oee["Epoch"]
        factors = oee_factors(_ms(oee, "Run", slot), _ms(oee, "Down", slot),
                              oee["SmpGood"][slot], oee["SmpNok"][slot],
                              oee["SmpIdealMs"][slot]) if current else {}
        values[f"OeeTrend[{slot + 1}]/Oee"] = factors.get("Oee", 0.0)
        values[f"OeeTrend[{slot + 1}]/OeeValid"] = factors.get("OeeValid", False)
    return values


def step_by_number(app, number: int):
    """The declared step with this number, the first chain's where several
    share it (each chain's init step is 0)."""
    return next((s for c in app.chains for s in c.steps if s.number == number), None)


def profiler_status(app, prof: dict[str, Any] | None) -> dict[str, Any]:
    """TC3's Profiler, as the HMI's cycle view reads it: the last cycle's
    waterfall, the per-step aggregates and the 60-cycle trend.

    Every slot is published every time, empty past the count, so the path set
    never moves with a cycle's length (see `alarm_log_status`). Names and time
    classes come from the declaration, as the step view's do; the controller
    keeps only numbers and times. Nothing when the profile did not read.

    Not published, because nothing reads them: TC3's live `Current` cycle, a
    step row's Last and Minimum (the module command rows publish theirs, which
    the HMI does read), and the Truncated flags, which stay on the controller
    beside the manifest that describes them."""
    import fraktal_ab_generate as gen

    if prof is None:
        return {}
    classes = len(decl.TIME_CLASSES)
    values: dict[str, Any] = {}
    base = "Profiler/LastCycle"
    last = prof["LastCycleNo"]
    count = prof["LastN"] if last else 0
    buffer = (1 - prof["CurBuf"]) * gen.PROFILE_STEPS
    values[f"{base}/CycleNo"] = last
    values[f"{base}/NSteps"] = count
    values[f"{base}/Total"] = prof["LastTotal"] if last else 0
    values[f"{base}/WorkTime"] = prof["LastWork"] if last else 0
    values[f"{base}/WaitTime"] = prof["LastTotal"] - prof["LastWork"] if last else 0
    for slot in range(gen.PROFILE_STEPS):
        row = f"{base}/Steps[{slot + 1}]"
        if slot < count:
            number = prof["WfStepNo"][buffer + slot]
            step = step_by_number(app, number)
            values.update({
                f"{row}/StepNo": number,
                f"{row}/StepName": f"project.step.{step.name}" if step else "",
                f"{row}/TimeClass": decl.TIME_CLASSES.index(step.time_class) if step else 0,
                f"{row}/Duration": prof["WfDurMs"][buffer + slot],
                f"{row}/Expected": prof["WfExpMs"][buffer + slot]})
        else:
            values.update({f"{row}/StepNo": 0, f"{row}/StepName": "",
                           f"{row}/TimeClass": 0, f"{row}/Duration": 0,
                           f"{row}/Expected": 0})
    values["Profiler/LastCycleTime"] = prof["LastCycleTime"]
    values["Profiler/MinCycleTime"] = prof["MinCycleTime"]
    order = gen.ordered_steps(app)
    for row_index in range(gen.PROFILE_STEPS):
        row = f"Profiler/StepStats[{row_index + 1}]"
        visited = row_index < len(order) and prof["StatCount"][row_index] > 0
        step = step_by_number(app, order[row_index]) if visited else None
        values.update({
            f"{row}/Id": order[row_index] if visited else 0,
            f"{row}/Label": f"project.step.{step.name}" if step else "",
            f"{row}/TimeClass": decl.TIME_CLASSES.index(step.time_class) if step else 0,
            f"{row}/Count": prof["StatCount"][row_index] if visited else 0,
            f"{row}/Avg": prof["StatAvg"][row_index] if visited else 0,
            f"{row}/Maximum": prof["StatMax"][row_index] if visited else 0})
    values["Profiler/HistoryHead"] = prof["HistoryHead"]
    for slot in range(gen.CYCLE_HISTORY):
        row = f"Profiler/History[{slot + 1}]"
        total, work = prof["HisTotal"][slot], prof["HisWork"][slot]
        values.update({f"{row}/CycleNo": prof["HisCycleNo"][slot],
                       f"{row}/Total": total, f"{row}/WorkTime": work,
                       f"{row}/WaitTime": total - work})
        for k in range(classes):
            values[f"{row}/ByClass[{k}]"] = prof["HisByClass"][slot * classes + k]
    return values


def state_flags_status(app, flags: dict[str, Any] | None) -> dict[str, Any]:
    """TC3's StateFlags and StateFlagCount, on the Unit that declares them.

    Stale is always FALSE, and truthfully: TC3's Stale catches a flag whose
    `_M_State` call sat behind an IF that stopped running. AB's flags are
    declared and emitted unconditionally, every scan, so none can stop being
    computed. Nothing when the table did not read."""
    if not app.state_flags or flags is None:
        return {}
    values: dict[str, Any] = {"StateFlagCount": len(app.state_flags)}
    for i, flag in enumerate(app.state_flags):
        base = f"StateFlags[{i + 1}]"
        values[f"{base}/Key"] = flag.key
        values[f"{base}/Value"] = bool(flags["Value"][i])
        values[f"{base}/Since"] = _controller_time(flags["SinceDate"][i],
                                                   flags["SinceTime"][i])
        values[f"{base}/Stale"] = False
    return values


def system_health_status(app, health: dict[str, Any] | None,
                         probe: dict[str, Any] | None) -> dict[str, Any]:
    """TC3's SystemHealth, as the HMI's health facet reads it, over AB S3's
    subset. A group this controller cannot measure is published unavailable
    with zeros, and never as healthy: TC3's own rule for an unsupported metric.
    Nothing when the status or the probe did not read."""
    if app.system_health is None or health is None or probe is None:
        return {}
    sync = bool(probe["TimeIsSynchronized"])
    values = {
        "Present": bool(health["Present"]), "Healthy": bool(health["Healthy"]),
        "TaskAvailable": bool(health["TaskAvailable"]),
        "TaskCycleUs": probe["IntervalUs"], "TaskJitterUs": probe["JitterUs"],
        "TaskOverrun": bool(health["TaskOverrun"]),
        "ControllerAvailable": False, "CpuLoadPct": 0.0, "MemoryAvailableMb": 0,
        "IpcAvailable": False, "IpcTemperatureC": 0.0, "FanHealthy": False,
        "StorageHealthPct": 0.0,
        "FieldbusAvailable": False, "FieldbusMasterHealthy": False,
        "LostFrameCount": 0, "SlaveErrorCount": 0,
        "DcAvailable": False, "DcSynchronized": False,
        "TimeQuality/Available": True, "TimeQuality/Synchronized": sync,
        "TimeQuality/Source": "PTP" if probe["TimePtpEnable"] else "",
        "TimeQuality/OffsetUs": 0,
    }
    return {f"SystemHealth/{k}": v for k, v in values.items()}


def read_system_health(comm: Any) -> tuple:
    """The §8.12 status and the probe it reads, each in one request."""
    import fraktal_ab_generate as gen
    import fraktal_ab_press_execute as execute

    if APP.system_health is None:
        return None, None
    return (execute.read_layout(comm, gen.system_health_tag(APP), gen.system_health_members()),
            execute.read_layout(comm, gen.health_probe_tag(APP), gen.health_probe_members()))


def read_state_flags(comm: Any) -> dict[str, Any] | None:
    """The §3.12 table in one request. Read-only, never fatal."""
    import fraktal_ab_generate as gen
    import fraktal_ab_press_execute as execute

    if not APP.state_flags:
        return None
    return execute.read_layout(comm, gen.state_flags_tag(APP),
                               gen.state_flags_members(APP))


def read_profiler(comm: Any) -> dict[str, Any] | None:
    """The §8.11.4 profile in one request. Read-only, never fatal."""
    import fraktal_ab_generate as gen
    import fraktal_ab_press_execute as execute

    return execute.read_layout(comm, gen.profiler_tag(APP), gen.profiler_members(APP))


def read_oee(comm: Any) -> dict[str, Any] | None:
    """The §8.5.1 accounting in one request. Read-only, never fatal."""
    import fraktal_ab_generate as gen
    import fraktal_ab_press_execute as execute

    return execute.read_layout(comm, gen.oee_tag(APP), gen.oee_members())


def read_line(comm: Any) -> tuple:
    if APP.line is None:
        return None, None
    import fraktal_ab_line as line
    import fraktal_ab_press_execute as execute
    return (execute.read_layout(comm, line.tag(APP, 'State'), line.state_members()),
            execute.read_layout(comm, line.tag(APP, 'Shift'), line.shift_members()))


def read_alarm_log(comm: Any) -> tuple:
    """The §8.3 log's two halves, each in ONE request. Read-only, never fatal.

    Two requests, not one, because they change at different rates - but each
    is atomic on the wire, so an event is never read half-closed.
    """
    import fraktal_ab_generate as gen
    import fraktal_ab_press_execute as execute

    active = execute.read_layout(comm, gen.alarm_active_tag(APP),
                                 gen.alarm_active_members())
    ring = execute.read_layout(comm, gen.alarm_ring_tag(APP),
                               gen.alarm_ring_members())
    return active, ring


def read_models(comm: Any, count=None) -> list[dict[str, int]] | None:
    """Each declared model's stored values, in model order. Read-only.

    None when the array does not answer, and then only the running model's
    page is offered: a model whose stored numbers could not be read is not
    shown as its declared defaults, because a commissioned M-200 that reads
    back as the shipped M-200 is the confidently-wrong case.
    """
    import fraktal_ab_generate as gen
    import fraktal_ab_press_execute as execute

    members = tuple(m.name for m in gen.model_cfg_members(APP))
    if not members:
        return None
    out: list[dict[str, int]] = []
    for index in range(len(APP.models) if count is None else count):
        held = execute.read_flat(
            comm, f"{gen.model_cfg_tag(APP)}[{index}]", members)
        if held is None:
            return None
        out.append(held)
    return out


def read_records(comm: Any) -> dict[str, dict[str, int]]:
    """The declared configuration records' live values, by record name.

    Read-only, and never fatal. A record that does not answer is omitted, and
    config_page then leaves its values out of the page entirely: a field the
    operator cannot see is better than one showing a number nobody read.
    """
    import fraktal_ab_press_execute as execute

    out: dict[str, dict[str, int]] = {}
    for record in APP.records:
        held = execute.read_flat(comm, f"{record.name}Tag",
                                 tuple(m.name for m in record.members))
        if held is not None:
            out[record.name] = held
    return out


def read_persist(comm: Any) -> dict[str, int] | None:
    """The §3.8b durability record. Read-only, and never fatal.

    A build emitted before §3.8b existed carries no such tag, and a station
    that cannot answer is not the same as one reporting trouble — so a failed
    read omits the record rather than inventing zeroes, and the client renders
    a root that says nothing about durability instead of a healthy one.
    """
    import fraktal_ab_generate as gen
    import fraktal_ab_press_execute as execute

    return execute.read_flat(
        comm, gen.config_persist_tag(APP),
        tuple(m.name for m in gen.config_persist_members()))


def read_io(comm: Any) -> dict[str, dict[str, int]]:
    """The declared I/O modules' live words. Read-only, and never fatal.

    A module that does not answer is omitted, which publishes its channels with
    their identity and `Quality` FALSE rather than a confident zero. An I/O
    read has to be allowed to fail on its own: the fieldbus view is a
    diagnostic, and refusing the whole station snapshot because one chassis
    word did not come back would take the operator's process screens away to
    report a broken sensor list.
    """
    import fraktal_ab_generate as gen

    # §10.5.1 state, and it belongs to the controller, not to this reader: the
    # HMI must be told forcing is available only when the machine says so.
    # Absent words leave `forcePermitted` 0, so the affordance disappears
    # rather than appearing on a guess.
    force: dict[str, int] = {}
    for tag in gen.force_tags(APP):
        answer = comm.Read(tag)
        if getattr(answer, "Status", None) == "Success":
            force[tag.rsplit("_Force", 1)[-1]] = int(
                getattr(answer, "Value", 0) or 0)

    state: dict[str, dict[str, int]] = {}
    for module in APP.io_modules:
        words: dict[str, int] = {
            "forced": force.get("Mask", 0),
            "forcePermitted": force.get("Permitted", 0),
        }
        for key, tag in (("input", module.input_tag),
                         ("output", module.output_tag),
                         ("fault", module.fault_tag)):
            answer = comm.Read(tag)
            if getattr(answer, "Status", None) != "Success":
                break
            words[key] = int(getattr(answer, "Value", 0) or 0) &                 ((1 << module.data_width) - 1)
        else:
            state[module.address] = words
    return state


MAILBOX_CONTROL_LEAVES = (
    'HmiRequest/Sequence', 'HmiResponse/AckSequence',
    'HmiResponse/Accepted', 'HmiResponse/Diagnostic',
)


def read_mailbox_document(comm: Any, plan: ReadPlan) -> dict[str, Any]:
    """Fresh command control values without rereading the station's live tree.

    Both headers must match the already validated manifest. The response is
    still one native structure; its diagnostic uses that manifest's catalogue.
    This partial document is internal to command preflight/targeted reads and
    must never replace a complete snapshot or its discovery path set.
    """
    import fraktal_ab_manifest_read as reader

    payload, status, _ = reader._read_raw(comm, manifest.header_tag(APP))
    if payload is None:
        raise ReadFailed(f'manifest header did not read: {status}')
    header = reader.decode_header(payload)
    validate(header)
    if plan.manifest is None or plan.manifest[0] != header:
        raise ProjectionRefused('manifest changed before the mailbox read; rediscover')
    mailbox = read_mailbox(comm, include_report=False)
    values = mailbox_values(plan.manifest[1], mailbox['response'], mailbox['requestSequence'])
    after, status, _ = reader._read_raw(comm, manifest.header_tag(APP))
    if after is None:
        raise ReadFailed(f'manifest trailing header did not read: {status}')
    if reader.decode_header(after) != header:
        raise ProjectionRefused('manifest changed during the mailbox read; rediscover')
    return {'values': {f'{APP.name}/{leaf}': values[leaf]
                       for leaf in MAILBOX_CONTROL_LEAVES}}


def read_mailbox(comm: Any, *, include_report: bool = True) -> dict[str, Any]:
    """The mailbox answer in one request, plus the request's own sequence.

    The response is read as a whole structure rather than member by member.
    The controller writes ``AckSequence`` last precisely so a client can trust
    a matching ack to mean the rest is present, and three separate reads are
    three separate scans - S9's lesson - so they could straddle a command and
    pair one request's ack with another's verdict.
    """
    import struct

    import fraktal_ab_manifest_read as reader
    import fraktal_ab_mailbox as mailbox

    payload, status, _ = reader._read_raw(comm, mailbox.response_tag_name(APP))
    members = [name for name, _, _, _ in mailbox.RESPONSE_MEMBERS]
    if payload is None or len(payload) < 4 * len(members):
        raise ReadFailed(f"the mailbox answer did not read: {status}")
    response = dict(zip(members, struct.unpack_from(f"<{len(members)}i", payload, 0)))

    import fraktal_ab_press_execute as execute
    value = execute.read_scalar(comm, f'{mailbox.request_tag_name(APP)}.Sequence')
    if value is None:
        raise ReadFailed('the mailbox request sequence did not read')
    # The report the answer carries, in one request. The controller writes it
    # in the scan it acknowledges, before AckSequence, so a matching ack read
    # with it is this answer's report.
    report = (execute.read_layout(comm, gen.release_report_tag(APP),
                                  gen.release_report_members()) if include_report else None)
    return {"response": response, "requestSequence": value, "report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="controller IPv4 address or path")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--slot", type=int, default=0)
    args = parser.parse_args(argv)

    from pylogix import PLC

    from fraktal_ab_s16_execute import _normalize_serial

    with PLC() as comm:
        comm.IPAddress = args.target
        comm.ProcessorSlot = args.slot
        try:
            serial, ok = verify_serial(comm, args.expect_serial)
        except ReadFailed as failure:
            print(str(failure), file=sys.stderr)
            return 2
        if not ok:
            print(f"serial {serial} is not the expected "
                  f"{_normalize_serial(args.expect_serial)}; refusing",
                  file=sys.stderr)
            return 2

        try:
            document = read_document(comm)
        except ReadFailed as failure:
            print(str(failure), file=sys.stderr)
            return 2
        except ProjectionRefused as refusal:
            print(json.dumps({"schema": SCHEMA, "projected": False,
                              "reason": str(refusal)}, indent=2))
            return 1

    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

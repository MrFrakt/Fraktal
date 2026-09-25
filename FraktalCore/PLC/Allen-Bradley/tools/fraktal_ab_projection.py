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

import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo

SCHEMA = "fraktal.ab.projection"
SCHEMA_VERSION = 1

APP = demo.application()

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
    ("Status/Diagnostic/IoTag",
     "the press demo declares no physical I/O, deliberately"),
    ("Status/Diagnostic/IoAddress",
     "the press demo declares no physical I/O, deliberately"),
    ("Status/Diagnostic/Since",
     "no per-module event timestamp is published; S1 proved the clock, the "
     "binding does not yet stamp reasons with it"),
    ("Status/Diagnostic/TimeSynchronized",
     "follows Diagnostic/Since"),
    ("Status/ControlDomainId",
     "the control-power domain is a recorded Phase 4 deferral"),
    ("AlarmLog/*", "the event core is owed work, not published"),
    ("HostEvents/*", "the event core is owed work, not published"),
    ("Access/*", "release and access enforcement are owed work"),
    ("ControlPower/*", "out of scope: no control-power domain"),
    ("Oee/*", "not published by this binding"),
    ("Nameplate/*", "no module in this application declares a nameplate"),
    ("Model/*", "recipes and changeover are a recorded deferral"),
    ("AvailableModels", "recipes and changeover are a recorded deferral"),
)


class ProjectionRefused(Exception):
    """Discovery failed its own validity check, so nothing is projected."""


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
    if header.get("ContentHash") != manifest.content_hash(APP):
        reasons.append(
            f"content hash {header.get('ContentHash')!r} does not match the "
            f"declaration {manifest.content_hash(APP)!r}")
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
        })
    return out


def module_status(context: dict[str, int]) -> dict[str, Any]:
    """One module's Status members, from its contract context."""
    return {
        "Status/State": context["OutImm_ExecState"],
        "Status/FaultActive": context["Error"] != 0,
        "Status/Diagnostic/ReasonCode": context["OutImm_Reason"],
    }


def unit_status(unit: dict[str, int], chart: dict[str, Any] | None) -> dict[str, Any]:
    """The root Unit's own members, beyond the Status every module carries."""
    values: dict[str, Any] = {
        "Status/State": (gen.STATE_ERROR if unit["Error"] else
                         gen.STATE_BUSY if unit["Running"] else
                         gen.STATE_DONE if unit["Complete"] else gen.STATE_READY),
        "Status/FaultActive": unit["Error"] != 0,
        "Status/Diagnostic/ReasonCode": unit["HeldReason"] or unit["ReportedReason"],
        # Core E_Mode ordinals, published verbatim: the HMI resolves them
        # against the same enum, which is why they have to be the same numbers.
        "ModeActivePublished": unit["Mode"],
        "GoodCount": unit["GoodCount"],
        "NokCount": unit["ScrapCount"],
        "CurrentStep/StepNo": unit["Step"],
        "Decision/Default": unit["DecisionAnswer"],
    }
    if chart is not None:
        values["CurrentStepElapsed"] = chart["CurrentStepMs"]
        values["CurrentStepTimedOut"] = chart["StallReason"] != 0
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
    for chain in app.chains:
        index = chain.mode_ordinal + 1
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
    return values


def mailbox_values(rows: dict[str, Any], response: dict[str, int],
                   request_sequence: int) -> dict[str, Any]:
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
        "HmiRequest/Sequence": request_sequence,
        "HmiResponse/AckSequence": response.get("AckSequence", 0),
        "HmiResponse/Accepted": response.get("Accepted", 0) != 0,
        # An unresolvable key is reported as such rather than as no reason at
        # all: blank would read as "accepted without comment".
        "HmiResponse/Diagnostic": (
            "" if key == 0
            else catalogue.get(key, f"{mailbox.UNKNOWN_KEY}#{key}")),
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
                f"{leaf}/Address": f"{module.address}:"
                                   f"{'O' if outward else 'I'}.{channel.bit}",
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
                # §10.5.1 forcing is a write, and the mailbox is the only
                # command surface this binding has (AB §11.2.1). Publishing
                # Forceable TRUE would offer the operator an affordance that
                # cannot be honoured.
                f"{leaf}/Forced": False,
                f"{leaf}/Forceable": False,
            })
    return values


def project(header: dict[str, Any], rows: dict[str, Any],
            unit: dict[str, int], contexts: dict[str, dict[str, int]],
            chart: dict[str, Any] | None = None,
            mailbox_state: dict[str, Any] | None = None,
            io_state: dict[str, dict[str, int]] | None = None) -> dict[str, Any]:
    """The snapshot document, from a validated manifest and the live contexts."""
    validate(header)

    values: dict[str, Any] = {}
    described = modules(rows)
    for module in described:
        base = module["base"]
        values[f"{base}/Status/Name"] = module["identity"]
        values[f"{base}/Status/ModuleType"] = module["type"]
        values[f"{base}/Status/DisplayNameKey"] = module["displayNameKey"]
        if module["type"] == MODULE_TYPE_UNIT:
            for suffix, value in unit_status(unit, chart).items():
                values[f"{base}/{suffix}"] = value
            for suffix, value in mode_policy(APP).items():
                values[f"{base}/{suffix}"] = value
            if mailbox_state is not None:
                for suffix, value in mailbox_values(
                        rows, mailbox_state["response"],
                        mailbox_state["requestSequence"]).items():
                    values[f"{base}/{suffix}"] = value
        else:
            name = module["identity"].rsplit(".", 1)[-1]
            context = contexts.get(name)
            if context is None:
                raise ProjectionRefused(
                    f"module {module['identity']} is published but its context "
                    "was not read; refusing to project a module without state")
            for suffix, value in module_status(context).items():
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


def read_document(comm: Any) -> dict[str, Any]:
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
    rows = {table.name: reader.read_table(comm, table)["rows"]
            for table in manifest.tables(APP)}
    rows = {name: read[:header[f"{name}Count"]] for name, read in rows.items()}

    unit = execute.read_unit(comm)
    chart = execute.read_chart(comm)
    contexts = {m.name: execute.read_module(comm, m.name) for m in APP.modules}
    if unit is None or any(c is None for c in contexts.values()):
        raise ReadFailed("a live context did not read; refusing to project")

    return project(header, rows, unit, contexts, chart, read_mailbox(comm),
                   read_io(comm))


def read_io(comm: Any) -> dict[str, dict[str, int]]:
    """The declared I/O modules' live words. Read-only, and never fatal.

    A module that does not answer is omitted, which publishes its channels with
    their identity and `Quality` FALSE rather than a confident zero. An I/O
    read has to be allowed to fail on its own: the fieldbus view is a
    diagnostic, and refusing the whole station snapshot because one chassis
    word did not come back would take the operator's process screens away to
    report a broken sensor list.
    """
    state: dict[str, dict[str, int]] = {}
    for module in APP.io_modules:
        words: dict[str, int] = {}
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


def read_mailbox(comm: Any) -> dict[str, Any]:
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

    sequence, status, _ = reader._read_raw(
        comm, f"{mailbox.request_tag_name(APP)}.Sequence")
    if sequence is None or len(sequence) < 4:
        # A scalar read comes back as an int on this client; fall back to it.
        raw = comm.Read(f"{mailbox.request_tag_name(APP)}.Sequence")
        value = getattr(raw, "Value", None)
        if not isinstance(value, int):
            raise ReadFailed(f"the mailbox request sequence did not read: {status}")
    else:
        (value,) = struct.unpack_from("<i", sequence, 0)
    return {"response": response, "requestSequence": value}


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

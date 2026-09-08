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


def project(header: dict[str, Any], rows: dict[str, Any],
            unit: dict[str, int], contexts: dict[str, dict[str, int]],
            chart: dict[str, Any] | None = None) -> dict[str, Any]:
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
        else:
            name = module["identity"].rsplit(".", 1)[-1]
            context = contexts.get(name)
            if context is None:
                raise ProjectionRefused(
                    f"module {module['identity']} is published but its context "
                    "was not read; refusing to project a module without state")
            for suffix, value in module_status(context).items():
                values[f"{base}/{suffix}"] = value

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="controller IPv4 address or path")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--slot", type=int, default=0)
    args = parser.parse_args(argv)

    import fraktal_ab_manifest_read as reader
    import fraktal_ab_press_execute as execute
    from pylogix import PLC

    from fraktal_ab_s16_execute import _normalize_serial, _status, _value

    expected = _normalize_serial(args.expect_serial)
    with PLC() as comm:
        comm.IPAddress = args.target
        comm.ProcessorSlot = args.slot
        identity = comm.GetDeviceProperties()
        device = _value(identity)
        if device is None:
            print(f"identity read failed: {_status(identity)}", file=sys.stderr)
            return 2
        serial = _normalize_serial(getattr(device, "SerialNumber", 0))
        if serial != expected:
            print(f"serial {serial} is not the expected {expected}; refusing",
                  file=sys.stderr)
            return 2

        payload, status, _ = reader._read_raw(comm, manifest.header_tag(APP))
        if payload is None:
            print(f"manifest header: {status}", file=sys.stderr)
            return 2
        header = reader.decode_header(payload)
        rows = {table.name: reader.read_table(comm, table)["rows"]
                for table in manifest.tables(APP)}
        rows = {name: read[:header[f"{name}Count"]] for name, read in rows.items()}

        unit = execute.read_unit(comm)
        chart = execute.read_chart(comm)
        contexts = {m.name: execute.read_module(comm, m.name) for m in APP.modules}
        if unit is None or any(c is None for c in contexts.values()):
            print("a live context did not read; refusing to project",
                  file=sys.stderr)
            return 2

    try:
        document = project(header, rows, unit, contexts, chart)
    except ProjectionRefused as refusal:
        print(json.dumps({"schema": SCHEMA, "projected": False,
                          "reason": str(refusal)}, indent=2))
        return 1

    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

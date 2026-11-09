#!/usr/bin/env python3
"""Read the manifest from the bench controller and check it against the source.

This is the other half of publication. ``fraktal_ab_manifest.py`` proves the
manifest is *in the project*; nothing until now proved a client can take it off
a running controller and get back what the declaration says. A manifest that
cannot be read is not a discovery surface, it is a tag.

**Read-only, and structurally so.** There is no write path in this file: it
opens a connection, reads, and closes. The serial guard is required rather than
optional, for the same reason every other harness here demands one - a fixed
vector aimed at the wrong controller is not a failed test, it is an incident.

**The coherence protocol is S7's, not a new one.** Read `ConfigRevision`, read
every table, read `ConfigRevision` again, and accept the snapshot only if it did
not move. That needs difference and never ordering, which is exactly what
`ConfigRevision` guarantees - it is derived from the content hash, so a later
revision may be numerically smaller than an earlier one.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from typing import Any

import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_station as station
from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value

SCHEMA = "fraktal.ab.manifest-read"
SCHEMA_VERSION = 1

APP = station.application()
WIDTH = manifest.key_string_length(APP)
CONTROLLER_IDENTITY = gen.CONTROLLER_IDENTITY

# A Logix string member is LEN (DINT) followed by DATA (SINT[width]); every
# other published member is a DINT. Those two facts are the whole layout.
DINT_BYTES = 4
STRING_BYTES = DINT_BYTES + WIDTH


def member_bytes(logical_type: str) -> int:
    return STRING_BYTES if logical_type == manifest.KEY32 else DINT_BYTES


def row_bytes(table: manifest.Table) -> int:
    return sum(member_bytes(dt) for _, dt in table.members)


def decode_string(payload: bytes, offset: int) -> str:
    """One Logix string member: a length, then that many characters of DATA."""
    (length,) = struct.unpack_from("<i", payload, offset)
    length = max(0, min(length, WIDTH))
    raw = payload[offset + DINT_BYTES:offset + DINT_BYTES + length]
    return raw.decode("ascii", errors="replace")


def decode_row(table: manifest.Table, payload: bytes, offset: int) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for name, logical_type in table.members:
        if logical_type == manifest.KEY32:
            row[name] = decode_string(payload, offset)
        else:
            (row[name],) = struct.unpack_from("<i", payload, offset)
        offset += member_bytes(logical_type)
    return row


def header_layout() -> list[tuple[str, str]]:
    """The header's members, in the order ``fraktal_ab_manifest`` emits them."""
    layout: list[tuple[str, str]] = [(n, "DINT") for n in manifest.HEADER_SCALARS]
    layout.append(("ContentHash", manifest.KEY32))
    layout.append(("ControllerIdentity", manifest.KEY32))
    for table in manifest.tables(APP):
        layout.append((f"{table.name}Count", "DINT"))
        layout.append((f"{table.name}Capacity", "DINT"))
    return layout


def decode_header(payload: bytes) -> dict[str, Any]:
    header: dict[str, Any] = {}
    offset = 0
    for name, logical_type in header_layout():
        if logical_type == manifest.KEY32:
            header[name] = decode_string(payload, offset)
        else:
            (header[name],) = struct.unpack_from("<i", payload, offset)
        offset += member_bytes(logical_type)
    return header


def header_bytes() -> int:
    return sum(member_bytes(dt) for _, dt in header_layout())


def _read_raw(comm: Any, tag: str,
              count: int | None = None) -> tuple[bytes | None, str, float]:
    """One read, returning the raw payload, the CIP status and the elapsed ms.

    An array tag needs its element count. Asking for an array without one
    returns element zero and succeeds, which reads like a short reply rather
    than like the wrong question - so the count is passed explicitly wherever
    the tag is an array, and never inferred from the size that came back.
    """
    started = time.perf_counter()
    reply = comm.Read(tag) if count is None else comm.Read(tag, count)
    elapsed = (time.perf_counter() - started) * 1000.0
    if not _success(reply):
        return None, _status(reply), elapsed
    value = _value(reply)
    if not isinstance(value, (bytes, bytearray)):
        return None, f"expected raw structure bytes, got {type(value).__name__}", elapsed
    return bytes(value), "Success", elapsed


def read_table(comm: Any, table: manifest.Table) -> dict[str, Any]:
    """A whole table in one request, falling back to per element if that fails.

    The fallback is not decoration. The first bench run took the whole manifest
    element by element - 526 requests and 1.5 seconds - because the array read
    was issued without an element count and came back holding row zero. That
    looked exactly like a controller that would not serve a whole array, and it
    was a harness defect. So the path taken is recorded rather than assumed, and
    a run that falls back says so instead of quietly costing 500 requests.
    """
    tag = manifest.manifest_tag(APP, table)
    width = row_bytes(table)
    payload, status, elapsed = _read_raw(comm, tag, table.capacity)

    if payload is not None and len(payload) >= width * table.capacity:
        rows = [decode_row(table, payload, index * width)
                for index in range(table.capacity)]
        return {"tag": tag, "path": "whole-tag", "requests": 1,
                "ms": round(elapsed, 3), "bytes": len(payload), "rows": rows}

    rows = []
    started = time.perf_counter()
    for index in range(table.capacity):
        element, element_status, _ = _read_raw(comm, f"{tag}[{index}]")
        if element is None or len(element) < width:
            return {"tag": tag, "path": "per-element", "requests": index + 1,
                    "ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "error": f"{tag}[{index}]: {element_status}", "rows": rows}
        rows.append(decode_row(table, element, 0))
    return {"tag": tag, "path": "per-element", "requests": table.capacity,
            "ms": round((time.perf_counter() - started) * 1000.0, 3),
            "bytes": width * table.capacity, "rows": rows}


def compare(header: dict[str, Any], tables: dict[str, Any]) -> dict[str, Any]:
    """What the controller returned against what the declaration says.

    Only the declared rows are compared. The slots past a table's count are
    capacity, not content, and demanding they match would be asserting that
    unused space has a value.
    """
    expected = manifest.content(APP)
    findings: list[str] = []

    if header.get("ContentHash") != manifest.content_hash(APP):
        findings.append(
            f"ContentHash {header.get('ContentHash')!r} != "
            f"{manifest.content_hash(APP)!r}")
    if header.get("ConfigRevision") != manifest.config_revision(APP):
        findings.append(
            f"ConfigRevision {header.get('ConfigRevision')} != "
            f"{manifest.config_revision(APP)}")
    if header.get("ControllerIdentity") != CONTROLLER_IDENTITY:
        findings.append(
            f"ControllerIdentity {header.get('ControllerIdentity')!r} != "
            f"{CONTROLLER_IDENTITY!r}")
    if header.get("Magic") != manifest.MANIFEST_MAGIC:
        findings.append(f"Magic {header.get('Magic')} is not the manifest magic")
    if header.get("Valid") != 1:
        findings.append("Valid is not 1")
    if header.get("Truncated") != 0:
        findings.append("Truncated is not 0")
    if header.get("KeyLength") != WIDTH:
        findings.append(f"KeyLength {header.get('KeyLength')} != {WIDTH}")

    per_table: dict[str, Any] = {}
    for table in manifest.tables(APP):
        want = expected[table.name]
        read = tables.get(table.name, {}).get("rows", [])
        count = header.get(f"{table.name}Count")
        matched = read[:len(want)] == want
        per_table[table.name] = {
            "declaredRows": len(want),
            "publishedCount": count,
            "rowsRead": len(read),
            "rowsMatch": matched,
        }
        capacity = header.get(f"{table.name}Capacity")
        per_table[table.name]["publishedCapacity"] = capacity
        if capacity != table.capacity:
            findings.append(
                f"{table.name}Capacity {capacity} != {table.capacity} declared")
        if count != len(want):
            findings.append(
                f"{table.name}Count {count} != {len(want)} declared")
        if not matched:
            # Report the short read explicitly. Walking the pairs alone finds
            # nothing when the table came back empty, which would let a table
            # that failed to read at all pass as equal - the exact shape of a
            # check that cannot fail.
            if len(read) < len(want):
                findings.append(
                    f"{table.name} read {len(read)} rows, needs {len(want)}")
            for index, (got, wanted) in enumerate(zip(read, want)):
                if got != wanted:
                    findings.append(
                        f"{table.name}[{index}] {got!r} != {wanted!r}")
                    break

    return {"tables": per_table, "findings": findings, "equal": not findings}


def run(comm: Any) -> dict[str, Any]:
    header_tag = manifest.header_tag(APP)

    payload, status, first_ms = _read_raw(comm, header_tag)
    if payload is None or len(payload) < header_bytes():
        return {"read": False, "error": f"{header_tag}: {status}"}
    header = decode_header(payload)

    tables: dict[str, Any] = {}
    started = time.perf_counter()
    for table in manifest.tables(APP):
        tables[table.name] = read_table(comm, table)
    tables_ms = (time.perf_counter() - started) * 1000.0

    # S7's coherence check: the revision must not have moved underneath the read.
    recheck, recheck_status, recheck_ms = _read_raw(comm, header_tag)
    if recheck is None or len(recheck) < header_bytes():
        return {"read": False, "error": f"{header_tag} recheck: {recheck_status}"}
    after = decode_header(recheck)
    coherent = after["ConfigRevision"] == header["ConfigRevision"]

    result = compare(header, tables)
    total_bytes = header_bytes() + sum(
        t.get("bytes", 0) for t in tables.values())
    requests = 2 + sum(t.get("requests", 0) for t in tables.values())

    return {
        "read": True,
        "header": header,
        "coherent": coherent,
        "requests": requests,
        "bytesRead": total_bytes,
        "timingMs": {
            "header": round(first_ms, 3),
            "tables": round(tables_ms, 3),
            "recheck": round(recheck_ms, 3),
            "total": round(first_ms + tables_ms + recheck_ms, 3),
        },
        "tableReads": {name: {k: v for k, v in detail.items() if k != "rows"}
                       for name, detail in tables.items()},
        "comparison": result,
        "passed": bool(coherent and result["equal"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="controller IPv4 address or path")
    parser.add_argument("--expect-serial", required=True, type=_normalize_serial)
    parser.add_argument("--slot", type=int, default=0)
    args = parser.parse_args(argv)

    from pylogix import PLC

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "schemaVersion": SCHEMA_VERSION,
        "target": args.target,
        "expectedSerial": args.expect_serial,
        "keyLength": WIDTH,
    }

    with PLC() as comm:
        comm.IPAddress = args.target
        comm.ProcessorSlot = args.slot
        identity = comm.GetDeviceProperties()
        device = _value(identity)
        if not _success(identity) or device is None:
            record["error"] = f"identity read failed: {_status(identity)}"
            print(json.dumps(record, indent=2, sort_keys=True))
            return 2
        serial = _normalize_serial(getattr(device, "SerialNumber", 0))
        record["serial"] = serial
        record["productName"] = getattr(device, "ProductName", "")
        record["revision"] = getattr(device, "Revision", "")
        if serial != args.expect_serial:
            record["error"] = (
                f"serial {serial} is not the expected {args.expect_serial}; "
                "refusing to read a controller this vector was not aimed at")
            print(json.dumps(record, indent=2, sort_keys=True))
            return 2

        record.update(run(comm))

    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())


def _config_revision(app, entries: list[dict[str, Any]]) -> int:
    import hashlib
    material = "|".join(
        [str(manifest.config_revision(app))]
        + [f"{e['WriteKey']}={e['ValueText']}:{e['ReadLevel']}:{e['WriteLevel']}:{e['Readable']}" for e in entries])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


def config_page(app, rows: dict[str, Any],
                record_values: dict[str, dict[str, int]] | None,
                model_values: list[dict[str, int]] | None = None,
                model: int = 0, data_levels=None) -> dict[str, Any]:
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
        parts = path.split(".")
        if len(parts) < 2:
            continue
        record, member = parts[-2], parts[-1]
        held = values.get(record, {})
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
            "Item": f"Config/{member}",
            "ValueText": str(held[member]) if readable else "",
            "WriteKey": catalogue.get(row["WriteKeyKey"], ""),
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
            "ModelScoped": scoped,
            "CaptureSource": catalogue.get(row.get("CaptureSourceKey", 0), ""),
            "CanCapture": bool(row.get("CaptureSourceKey", 0)),
        })

    out: dict[str, Any] = {
        "Status/ConfigRev": _config_revision(app, entries),
        "HmiResponse/ConfigPage/PageCount": 1,
        "HmiResponse/ConfigPage/EntryCount": len(entries),
    }
    for index, entry in enumerate(entries, start=1):
        for name, value in entry.items():
            out[f"HmiResponse/ConfigPage/Entries[{index}]/{name}"] = value
    return out


def _controller_time(date: int, clock: int) -> str:
    from datetime import datetime, timezone
    if not date or not clock:
        return ""
    year = date // 10000
    month = (date % 10000) // 100
    day = date % 100
    hour = clock // 10000000
    minute = (clock % 10000000) // 100000
    second = (clock % 100000) // 1000
    ms = clock % 1000
    try:
        dt = datetime(year, month, day, hour, minute, second, ms * 1000, tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        return ""


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

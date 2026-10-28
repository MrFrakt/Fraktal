#!/usr/bin/env python3
"""Read-only supplementary S0 acquisition, pinned to local Echo 601FC87B.

Records Symbol/Template metadata, native byte sizes, precision vectors, denied
reads and actual Read Tag/Read Tag Fragmented service offsets at 500/4000-byte
connection settings. No write, download, mode or fault-clear path exists.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import struct
import time

import fraktal_ab_s0_supplementary_probe as probe
from fraktal_ab_s0_canonical_measure import discover_templates, member_table
from fraktal_ab_canonical_reader import decode_record, template_byte_size


def guard(comm):
    response = comm.GetDeviceProperties()
    value = response.Value
    if response.Status != "Success" or value is None or (
            str(value.SerialNumber).lower(), value.ProductName, value.ProductCode, value.Revision
    ) != ("0x601fc87b", "Emulate 5580 Controller", 288, "38.11"):
        raise ValueError("exact local Echo identity guard failed")
    reply = comm.Read(probe.IDENTITY)
    if reply.Status != "Success" or reply.Value != probe.MAGIC:
        raise ValueError("loaded controller image is not the supplementary S0 probe")


class ReadTrace:
    """Trace only tag reads; no mutation service can pass this connection seam."""
    def __init__(self, comm):
        self.comm, self.rows = comm, []

    def __enter__(self):
        self.original = self.comm.conn.send
        self.comm.conn.send = self.send
        return self.rows

    def __exit__(self, *unused):
        self.comm.conn.send = self.original

    def send(self, request, *args, **kwargs):
        if not request or request[0] not in (0x4C, 0x52):
            raise ValueError("non-read service rejected by supplementary tracer")
        start = 2 + request[1] * 2
        if len(request) != start + (6 if request[0] == 0x52 else 2):
            raise ValueError("malformed read request")
        offset = struct.unpack_from("<I", request, start + 2)[0] if request[0] == 0x52 else 0
        status, packet = self.original(request, *args, **kwargs)
        payload = 0
        if packet and len(packet) >= 54 and status in (0, 6):
            at = 50 + packet[49] * 2
            type_bytes = 4 if packet[at] == 0xA0 else 2
            payload = len(packet) - at - type_bytes
        self.rows.append(dict(service=hex(request[0]), offset=offset, status=status,
                              payloadBytes=payload, requestHex=request.hex(),
                              responseSha256=hashlib.sha256(packet).hexdigest() if packet else None))
        if len(self.rows) > 8192:
            raise ValueError("fragment trace exceeded packet budget")
        return status, packet


def verify_trace(rows, byte_count):
    """The last initial read begins the actual stream (pylogix also does a type read)."""
    starts = [i for i, row in enumerate(rows) if row["service"] == "0x4c"]
    if not starts:
        raise ValueError("no initial Read Tag service recorded")
    stream, offset = rows[starts[-1]:], 0
    fragments = stream
    # Logix may answer Read Tag with status 6 and only the type header,
    # requiring Read Tag Fragmented to start at byte zero. This initial
    # negotiation is not an empty data fragment; every 0x52 must carry data.
    if stream[0]["status"] == 6 and stream[0]["payloadBytes"] == 0:
        fragments = stream[1:]
        if not fragments or fragments[0]["service"] != "0x52":
            raise ValueError("empty initial read lacks a fragmented continuation")
    for i, row in enumerate(fragments):
        if row["offset"] != offset or row["payloadBytes"] <= 0 \
                or row["status"] != (0 if i == len(fragments) - 1 else 6):
            raise ValueError("fragment stream has a gap, overlap, empty fragment or wrong status")
        offset += row["payloadBytes"]
    if offset != byte_count:
        raise ValueError("fragment byte total differs from returned record")
    return dict(packets=len(stream), fragmented=len(stream) > 1, bytes=offset)


def check_size_bytes(raw, blocks):
    expected = bytearray(blocks * probe.BLOCK_BYTES)
    positions = (0, (blocks // 2) * probe.BLOCK_WORDS + 17, blocks * probe.BLOCK_WORDS - 1)
    for index, value in zip(positions, probe.SENTINELS):
        struct.pack_into("<i", expected, index * 4, value)
    return raw == expected


def read_attribute(comm, instance, attribute, service=0x0E):
    # Attribute 10 is only an observation candidate on this family; never infer
    # Logix access semantics from Micro800's similarly numbered PPD attribute.
    if service not in (0x0E, 0x03, 0x55):
        raise ValueError("non-read Symbol service rejected")
    request = comm._cip_message(service, 0x6B, instance,
                               attribute if service == 0x0E else [attribute])
    status, packet = comm.conn.send(request)
    return dict(service=hex(service), attribute=attribute, status=status,
                requestHex=request.hex(), responseHex=packet.hex() if packet else None)


def template_definition(comm, handle):
    """Preserve the raw definition, including metadata beyond member offsets."""
    attributes = comm._get_template_attribute(handle)
    # Same documented Template attribute-4 extent used by pylogix discovery.
    words = struct.unpack_from("<I", attributes, 56)[0]
    size = ((words * 4 - 23 + 3) // 4) * 4
    if not 0 < size <= 65536:
        raise ValueError("invalid supplementary Template definition size")
    return dict(attributesHex=attributes.hex(),
                definitionHex=comm._get_template(handle, size).hex())


def acquire(comm, connection_size, progress=None):
    result = progress if progress is not None else {}
    result.update(connectionSize=connection_size, passed=False, reads=[])
    guard(comm)
    answer = comm.GetTagList(allTags=False)
    if answer.Status != "Success":
        raise ValueError("Symbol discovery failed")
    objects = discover_templates(comm)
    templates = []
    for handle, udt in objects.items():
        templates.append(dict(handle=handle, name=udt.Name, byteSize=template_byte_size(comm, handle),
                              rawDefinition=template_definition(comm, handle),
                              members=member_table(udt),
                              access=[dict(name=f.TagName, driverAccess=getattr(f, "AccessRight", None),
                                           scope0=getattr(f, "Scope0", None), scope1=getattr(f, "Scope1", None))
                                      for f in udt.Fields]))
    symbols = [dict(name=t.TagName, instance=t.InstanceID, handle=t.DataTypeValue,
                    structure=bool(t.Struct), arrayRank=t.Array,
                    driverAccess=getattr(t, "AccessRight", None)) for t in answer.Value]
    by_name = {row["name"]: row for row in symbols}
    result.update(symbols=symbols, templates=templates)
    if probe.ROOT not in by_name:
        raise ValueError("browse-name root not discovered")
    reads = result["reads"]
    for tag, blocks in ((probe.ROOT, None), (probe.STATS, None),
                        *(("FRK_S0S_" + name, blocks) for name, blocks in probe.SIZES)):
        tick = time.monotonic()
        row = dict(tag=tag, trace=[])
        reads.append(row)
        with ReadTrace(comm) as trace:
            row["trace"] = trace
            response = comm.Read(tag)
        row["status"] = response.Status
        if response.Status != "Success" or not isinstance(response.Value, (bytes, bytearray)):
            raise ValueError(f"structured read failed: {tag}: {response.Status}")
        raw = bytes(response.Value)
        stream = verify_trace(trace, len(raw))
        row.update(bytes=len(raw), stream=stream, rawHex=raw.hex(),
                   elapsedMs=round((time.monotonic()-tick)*1000,3))
        if blocks:
            row["allBytesEqual"] = check_size_bytes(raw, blocks)
        else:
            row["decoded"] = decode_record(raw, by_name[tag]["handle"], templates)
    root = reads[0]["decoded"]
    scalars = {}
    for tag in ("FRK_S0S_WideInit", "FRK_S0S_NextInit"):
        response = comm.Read(tag)
        scalars[tag] = dict(status=response.Status, value=response.Value)
    access = []
    for tag in probe.ACCESS_TAGS:
        attributes = ([read_attribute(comm, by_name[tag]["instance"], attribute, service)
                       for service in (0x0E, 0x03, 0x55) for attribute in (2, 8, 10)]
                      if tag in by_name else [])
        for suffix in ("", ".Readback", ".HmiRequest", ".Private"):
            if suffix == ".Private" and not tag.endswith("Private"):
                continue
            response = comm.Read(tag + suffix)
            value = response.Value
            access.append(dict(path=tag+suffix, status=response.Status,
                               value=value.hex() if isinstance(value,(bytes,bytearray)) else value,
                               declaredTopAccess=probe.ACCESS_TAGS[tag], symbolAttributes=attributes))
    checks = dict(rootNamedAsBrowse=bytes.fromhex(root["Status"]["Name"]["bytes"]).decode()==probe.ROOT,
                  typedLrealExact=root["WideTyped"]==probe.PI,
                  nextLrealExact=root["WideNext"]==probe.NEXT,
                  piInitializerExact=scalars["FRK_S0S_WideInit"]==dict(status="Success",value=probe.PI),
                  nextInitializerExact=scalars["FRK_S0S_NextInit"]==dict(status="Success",value=probe.NEXT),
                  sizeBytesExact=all(row.get("allBytesEqual",True) for row in reads),
                  fragmentationObserved=all(row["stream"]["fragmented"] for row in reads if row["tag"].startswith("FRK_S0S_") and row.get("allBytesEqual") is not None))
    result.update(scalars=scalars, accessReads=access, checks=checks, passed=all(checks.values()),
                  note="Access outcomes are findings; a separate authorized write vector establishes effective write access.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-serial", required=True, choices=("601FC87B",))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing existing measurement output")
    from pylogix import PLC
    report = dict(schema="fraktal.ab.s0-supplementary-measurement", schemaVersion=1,
                  capturedUtc=datetime.now(timezone.utc).isoformat(), serial=args.expect_serial,
                  readOnly=True, runtimeAccepted=False, connections=[])
    try:
        for size in (500, 4000):
            progress = {}
            report["connections"].append(progress)
            with PLC("127.0.0.1") as comm:
                comm.ProcessorSlot, comm.ConnectionSize, comm.SocketTimeout = 0, size, 10
                acquire(comm, size, progress)
        report["passed"] = all(row["passed"] for row in report["connections"])
    except Exception as error:
        report.update(passed=False, error=f"{type(error).__name__}: {error}")
    opener = gzip.open if args.output.suffix == ".gz" else open
    with opener(args.output, "xt", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=report["passed"], connections=len(report["connections"]),
                          error=report.get("error"))))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only S0 measurement: decode the probe record from its CIP template alone.

This is the question canonical publication depends on (design note D2-D7): can
a client that knows nothing about the station recover every value from the
controller's own Symbol and Template objects? The record is decoded purely from
the template's member table - type code, byte offset, BOOL bit number, array
count, nested structure handle - and only afterwards compared with the values
the probe logic assigns (generation report). A member whose type code this
decoder does not know is reported with its raw bytes, never guessed.

Serial-guarded to the local Echo, and refuses unless the loaded image is the S0
probe. Issues Read, Get_Instance_Attribute_List and template reads only: no
write, mode change or download path exists here.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import time

TAG = "FRK_S12_Probe"
RECORD = "FRK_T_S0Probe"
ATOMIC = {0xC1: ("BOOL", 1), 0xC2: ("SINT", 1), 0xC3: ("INT", 2), 0xC4: ("DINT", 4),
          0xC5: ("LINT", 8), 0xC6: ("USINT", 1), 0xC7: ("UINT", 2), 0xC8: ("UDINT", 4),
          0xC9: ("ULINT", 8), 0xCA: ("REAL", 4), 0xCB: ("LREAL", 8), 0xD3: ("DWORD", 4)}
UNPACK = {"SINT": "<b", "INT": "<h", "DINT": "<i", "LINT": "<q", "USINT": "<B",
          "UINT": "<H", "UDINT": "<I", "ULINT": "<Q", "REAL": "<f", "LREAL": "<d",
          "DWORD": "<I"}


def member_table(udt) -> list[dict]:
    """Every member of a template, from its raw 8-byte definition."""
    rows = []
    for field in udt.Fields:
        info, code, offset = struct.unpack("<HHI", field.Bytes)
        rows.append(dict(name=field.TagName, info=info, code=code, offset=offset,
                         atomic=code & 0xFF if not code & 0x8000 else None,
                         struct=bool(code & 0x8000), handle=code & 0x0FFF,
                         array=(code & 0x6000) >> 13, typeName=field.DataType))
    return sorted(rows, key=lambda r: (r["offset"], r["info"]))


def discover_templates(comm) -> dict:
    """Complete discovery by the structure bit and full 12-bit handle.

    pylogix's recursive walk checks a handle's low byte against atomic codes;
    a structure whose handle ends in e.g. D1 is then omitted as if it were BYTE.
    Request those structures explicitly, retaining the already acquired cache.
    """
    found = dict(comm.UDT)
    while True:
        missing = []
        for udt in found.values():
            for field in udt.Fields:
                _, code, _ = struct.unpack("<HHI", field.Bytes)
                if code & 0x8000 and (code & 0x0FFF) not in found:
                    missing.append(field)
        if not missing:
            break
        prior = set(found)
        comm._get_udt(missing)  # Read-only Template services; pylogix replaces its cache.
        found.update(comm.UDT)
        if set(found) == prior:
            raise ValueError("Template discovery did not resolve the referenced structures")
    comm.UDT = found
    comm.UDTByName = {udt.Name: udt for udt in found.values()}
    for udt in found.values():
        for field in udt.Fields:
            _, code, _ = struct.unpack("<HHI", field.Bytes)
            if code & 0x8000:
                field.DataType = found[code & 0x0FFF].Name
    return found


def is_string(rows: list[dict]) -> int | None:
    """A StringFamily shape: exactly LEN DINT then DATA SINT[n]. Returns n."""
    named = [r for r in rows if not r["name"].startswith("ZZZZZZZZZZ")]
    if [r["name"] for r in named] == ["LEN", "DATA"] and named[0]["atomic"] == 0xC4 \
            and not named[0]["array"] and named[1]["atomic"] == 0xC2 and named[1]["array"] == 1:
        return named[1]["info"]
    return None


def decode(raw: bytes, base: int, rows: list[dict], udts_by_handle: dict, size: int,
           *, template_sizes=None, strict=False, native_times=False, _stack=()) -> dict:
    """Shared physical decoder; S0's diagnostic defaults preserve its findings.

    Canonical acquisition uses strict=True and authoritative Template byte sizes.
    A gap to the next member is not a structure-array stride: it includes padding.
    native_times decodes the measured native representations without normalizing
    their units. Logical conversion belongs to the canonical publication layer.
    """
    if base < 0 or size <= 0 or base + size > len(raw) or len(_stack) > 64:
        raise ValueError("invalid record extent or recursive template")
    time_types = {0xC0: ("DT", 8), 0xCC: ("LDT", 8), 0xD6: ("TIME32", 4),
                  0xD7: ("TIME", 8), 0xDF: ("LTIME", 8)}
    def require(at, length):
        if at < base or length < 0 or at + length > base + size:
            raise ValueError("member exceeds its template extent")
    out = {}
    named = [r for r in rows if not r["name"].startswith("ZZZZZZZZZZ")]
    for index, row in enumerate(named):
        at = base + row["offset"]
        later = [r["offset"] for r in rows if r["offset"] > row["offset"]]
        width = (min(later) if later else size) - row["offset"]
        count = row["info"] if row["array"] else 1
        if row["array"] > 1 or count <= 0 or row["name"] in out:
            raise ValueError("unsupported array rank, empty array or duplicate member")
        if row["struct"]:
            child = udts_by_handle.get(row["handle"])
            if child is None or row["handle"] in _stack:
                raise ValueError("missing or recursive template reference")
            child_rows = member_table(child)
            child_size = (template_sizes or {}).get(row["handle"])
            if child_size is None:
                if strict:
                    raise ValueError("canonical decoding requires Template structure byte sizes")
                child_size = width // count  # Historical S0 capture lacks attribute 3.
            require(at, child_size * count)
            n = is_string(child_rows)
            items = []
            for k in range(count):
                start = at + k * child_size
                if n is not None:
                    length_row, data_row = [r for r in child_rows
                                            if not r["name"].startswith("ZZZZZZZZZZ")]
                    if length_row["offset"] + 4 > child_size or data_row["offset"] + n > child_size:
                        raise ValueError("StringFamily exceeds template extent")
                    length = struct.unpack_from("<i", raw, start + length_row["offset"])[0]
                    data = raw[start + data_row["offset"]: start + data_row["offset"] + n]
                    if strict:
                        if not 0 <= length <= n:
                            raise ValueError("StringFamily LEN outside byte capacity")
                        data[:length].decode("utf-8", errors="strict")
                    items.append({"string": True, "width": n, "LEN": length,
                                  "bytes": data[:max(0, min(length, n))].hex()})
                else:
                    items.append(decode(raw, start, child_rows, udts_by_handle, child_size,
                                        template_sizes=template_sizes, strict=strict,
                                        native_times=native_times, _stack=(*_stack, row["handle"])))
            out[row["name"]] = items if row["array"] else items[0]
            continue
        code = row["atomic"]
        if code == 0xC1 and not row["array"]:
            if row["info"] > 31:
                raise ValueError("invalid BOOL bit number")
            require(at, row["info"] // 8 + 1)
            out[row["name"]] = bool(raw[at + row["info"] // 8] >> (row["info"] % 8) & 1)
        elif code == 0xC1:                      # BOOL[n] packs into DWORDs
            word_count = (count + 31) // 32
            require(at, word_count * 4)
            words = struct.unpack_from(f"<{word_count}I", raw, at)
            out[row["name"]] = [k for k in range(count) if words[k // 32] >> (k % 32) & 1]
        elif code in ATOMIC:
            name, step = ATOMIC[code]
            require(at, step * count)
            values = [struct.unpack_from(UNPACK[name], raw, at + k * step)[0] for k in range(count)]
            if strict and any(isinstance(v, float) and not math.isfinite(v) for v in values):
                raise ValueError("non-finite floating-point member")
            out[row["name"]] = values if row["array"] else values[0]
        elif native_times and code in time_types:
            _, step = time_types[code]
            require(at, step * count)
            values = [int.from_bytes(raw[at + k * step:at + (k + 1) * step],
                                     "little", signed=True) for k in range(count)]
            out[row["name"]] = values if row["array"] else values[0]
        else:
            if strict:
                raise ValueError(f"unsupported native type {hex(row['code'])}")
            # Not a type this decoder knows: report it, do not guess.
            out[row["name"]] = {"unknownTypeCode": hex(row["code"]), "bytes": raw[at:at + width].hex(),
                                "asSignedLE": int.from_bytes(raw[at:at + width], "little", signed=True)
                                if width in (4, 8) else None, "width": width}
    return out


def compare(expected: dict, decoded: dict, template=()) -> list[dict]:
    rows = []
    def check(path, want, got, native_type=None):
        if isinstance(want, float):
            # A REAL tolerance hides an implicit REAL-to-LREAL literal conversion.
            ok = isinstance(got, float) and (want == got if native_type == 0xCB
                                             else math.isclose(want, got, rel_tol=1e-6))
        elif isinstance(got, dict) and "unknownTypeCode" in got:
            ok, got = got["asSignedLE"] == want, got
        else:
            ok = want == got
        rows.append(dict(path=path, expected=want, decoded=got, equal=ok))
    for family, values in expected.items():
        for name, want in values.items():
            got = decoded.get(name)
            if name == "FlagsSet":
                flags = decoded.get("Flags")
                row = next((r for r in template if r["name"] == "Flags"), None)
                if row and row["atomic"] == 0xD3 and row["array"]:
                    # This probe declares BOOL[n]; v38 describes its storage as
                    # DWORD[n/32]. Keep the generic decoder's native word array;
                    # only the probe oracle compares the declared logical bits.
                    flags = [k for k in range(len(flags) * 32)
                             if flags[k // 32] >> (k % 32) & 1]
                check(f"{family}.Flags", want, flags)
            elif name in ("Words",):
                for k, v in want.items():
                    check(f"{family}.Words[{k}]", v, got[int(k)])
            elif name == "Kids":
                for k, fields in want.items():
                    for f, v in fields.items():
                        check(f"{family}.Kids[{k}].{f}", v, got[int(k)][f])
            elif isinstance(want, list):         # strings: [LEN, {index: byte}]
                data = bytes.fromhex(got["bytes"]) if got else b""
                check(f"{family}.{name}.LEN", want[0], got["LEN"] if got else None)
                for k, v in want[1].items():
                    check(f"{family}.{name}.DATA[{k}]", v, data[int(k)] if int(k) < len(data) else None)
            else:
                row = next((r for r in template if r["name"] == name), None)
                check(f"{family}.{name}", want, got, row["atomic"] if row else None)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--generation", type=Path, required=True,
                        help="combined.json from fraktal_ab_s0_canonical_probe.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing existing output")
    from pylogix import PLC
    case = json.loads(args.generation.read_text(encoding="utf-8"))["Cases"][0]
    with PLC("127.0.0.1") as comm:
        comm.ProcessorSlot, comm.SocketTimeout, comm.ConnectionSize = 0, 10, 4000
        identity = comm.GetDeviceProperties().Value
        if (identity is None or int(str(identity.SerialNumber), 0) != int(args.expect_serial, 16)
                or identity.ProductName != "Emulate 5580 Controller" or identity.Revision != "38.11"):
            raise SystemExit("exact local Echo identity guard failed")
        started = time.perf_counter()
        tags = comm.GetTagList(allTags=False).Value
        discovery_ms = (time.perf_counter() - started) * 1000
        probe = next((t for t in tags if t.TagName == TAG), None)
        if probe is None or probe.DataType != RECORD:
            raise SystemExit("the loaded image is not the S0 probe; refusing to measure")
        scan = [comm.Read("FRK_S12_Scan").Value]
        time.sleep(0.2)
        scan.append(comm.Read("FRK_S12_Scan").Value)
        by_handle = discover_templates(comm)
        udt = comm.UDTByName[RECORD]
        rows = member_table(udt)
        reply = comm.Read(TAG)
        raw = bytes(reply.Value) if isinstance(reply.Value, (bytes, bytearray)) else b""
        decoded = decode(raw, 0, rows, by_handle, len(raw))
        singles = {}
        for name in ("DurUs", "Dur32", "DurNs", "StampUs", "StampNs", "StampUsFromLint", "StampNsFromLint"):
            if any(r["name"] == name for r in rows):
                answer = comm.Read(f"{TAG}.{name}")
                singles[name] = dict(status=answer.Status, value=answer.Value
                                     if isinstance(answer.Value, (int, float, type(None))) else repr(answer.Value))
    expected = {k: v for k, v in case["Expected"].items()}
    checks = compare(expected, decoded, rows)
    report = dict(schema="fraktal.ab.s0-canonical-measurement", schemaVersion=1,
                  serial=args.expect_serial, readOnly=True, discoveryMs=round(discovery_ms, 1),
                  controllerTags=len(tags), scanAdvancing=scan[1] > scan[0], recordBytes=len(raw),
                  template=rows, decoded=decoded, memberReads=singles, checks=checks,
                  allEqual=all(c["equal"] for c in checks))
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(dict(allEqual=report["allEqual"], checks=len(checks),
                          failed=[c["path"] for c in checks if not c["equal"]],
                          unknownTypes={n: v["unknownTypeCode"] for n, v in decoded.items()
                                        if isinstance(v, dict) and "unknownTypeCode" in v})))
    return 0 if report["allEqual"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

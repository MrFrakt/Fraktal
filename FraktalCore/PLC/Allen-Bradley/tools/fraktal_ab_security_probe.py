#!/usr/bin/env python3
"""Probe the controller for CIP Security capability. Read-only, fixed classes.

AB §11.2.1 makes CIP Security the recommended posture and zone-and-conduit the
legacy one. Which posture a controller is *entitled* to is a property of the
hardware, and asserting "this family does not support CIP Security" from a
datasheet is weaker than asking the controller.

This probe issues `Get_Attribute_Single` against exactly the three CIP Security
object classes and nothing else:

* `0x5D` CIP Security
* `0x5E` EtherNet/IP Security
* `0x5F` Certificate Management

A controller that implements them answers; one that does not returns a CIP
general status (typically `0x05` path destination unknown, or `0x08` service
not supported). Either answer is evidence. Absence across all three is the
evidence a legacy zone-and-conduit deployment record needs.

The probe deliberately exposes **no arbitrary class, instance, attribute or
service input**: the three classes are constants here, the service is read-only,
and there is no write path of any kind. It does not attempt to configure, enable
or negotiate security - it only asks whether the objects exist.
"""

from __future__ import annotations

import argparse
import json
import socket
import string
import struct
import sys
from typing import Any


# (class id, attribute, human name) - fixed, not caller-supplied
SECURITY_OBJECTS: tuple[tuple[int, int, str], ...] = (
    (0x5D, 1, "CIP Security"),
    (0x5E, 1, "EtherNet/IP Security"),
    (0x5F, 1, "Certificate Management"),
)

GET_ATTRIBUTE_SINGLE = 0x0E
CIP_STATUS_MEANING = {
    0x00: "success",
    0x05: "path destination unknown (object class not implemented)",
    0x08: "service not supported",
    0x09: "invalid attribute value",
    0x14: "attribute not supported",
}


def _normalize_serial(value: Any) -> str:
    serial = str(value).removeprefix("0x").removeprefix("0X").upper()
    if len(serial) != 8 or any(
        character not in string.hexdigits for character in serial
    ):
        raise argparse.ArgumentTypeError("serial must be eight hexadecimal digits")
    return serial


def _register_session(sock: socket.socket) -> int:
    request = struct.pack("<HHIIQI", 0x0065, 4, 0, 0, 0, 0) + struct.pack("<HH", 1, 0)
    sock.sendall(request)
    header = sock.recv(24)
    if len(header) < 24:
        raise OSError("short RegisterSession reply")
    command, length, session = struct.unpack("<HHI", header[:8])
    if length:
        sock.recv(length)
    if command != 0x0065 or session == 0:
        raise OSError("RegisterSession refused")
    return session


def _unregister_session(sock: socket.socket, session: int) -> None:
    sock.sendall(struct.pack("<HHIIQI", 0x0066, 0, session, 0, 0, 0))


def _send_rr(sock: socket.socket, session: int, payload: bytes) -> bytes:
    cpf = struct.pack("<HH", 0x0000, 0) + struct.pack("<HH", 0x00B2, len(payload)) + payload
    body = struct.pack("<IH", 0, 0) + struct.pack("<H", 2) + cpf
    sock.sendall(struct.pack("<HHIIQI", 0x006F, len(body), session, 0, 0, 0) + body)
    header = sock.recv(24)
    if len(header) < 24:
        raise OSError("short SendRRData reply")
    _, length, _ = struct.unpack("<HHI", header[:8])
    return sock.recv(length) if length else b""


def _probe_class(
    sock: socket.socket, session: int, class_id: int, attribute: int
) -> dict[str, Any]:
    path = struct.pack("<BBBB", 0x20, class_id, 0x24, 1) + struct.pack(
        "<BB", 0x30, attribute
    )
    request = struct.pack("<BB", GET_ATTRIBUTE_SINGLE, len(path) // 2) + path
    reply = _send_rr(sock, session, request)
    # locate the CIP response inside the CPF item
    marker = reply.find(struct.pack("<HH", 0x00B2, 0))
    body = reply[reply.find(b"\xb2\x00") + 4:] if b"\xb2\x00" in reply else reply
    status = body[2] if len(body) > 2 else None
    return {
        "class": f"0x{class_id:02X}",
        "attribute": attribute,
        "cipStatus": None if status is None else f"0x{status:02X}",
        "meaning": CIP_STATUS_MEANING.get(status, "unrecognized status"),
        "implemented": status == 0x00,
        "_marker": marker,
    }


def probe(target: str, timeout: float) -> dict[str, Any]:
    results = []
    with socket.create_connection((target, 44818), timeout=timeout) as sock:
        sock.settimeout(timeout)
        session = _register_session(sock)
        try:
            for class_id, attribute, name in SECURITY_OBJECTS:
                entry = _probe_class(sock, session, class_id, attribute)
                entry.pop("_marker", None)
                entry["name"] = name
                results.append(entry)
        finally:
            _unregister_session(sock, session)
    implemented = [item["name"] for item in results if item["implemented"]]
    return {
        "schema": "fraktal.ab.security-capability-probe",
        "schema_version": 1,
        "target": target,
        "objectsProbed": results,
        "cipSecurityObjectsImplemented": implemented,
        "cipSecurityAvailable": bool(implemented),
        "posture": (
            "CIP Security posture is available; AB §11.2.1 recommends it"
            if implemented
            else "no CIP Security object answered; AB §11.2.1 legacy "
            "zone-and-conduit posture applies and shall be documented"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    _normalize_serial(args.expect_serial)
    try:
        evidence = probe(args.target, args.timeout)
    except (OSError, struct.error) as exc:
        print(f"ERROR [ab-security-probe] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    evidence["expected_serial"] = _normalize_serial(args.expect_serial)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

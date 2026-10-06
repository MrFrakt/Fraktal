#!/usr/bin/env python3
"""Read-only EtherNet/IP identity and TCP/IP-interface probe.

The tool deliberately exposes no generic CIP service option. It sends only:

* EtherNet/IP ListIdentity;
* RegisterSession / UnregisterSession; and
* CIP Get_Attribute_Single (0x0E) to TCP/IP Interface Object 0xF5 and Time
  Sync Object 0x43, instance 1.

It never opens an I/O connection and contains no tag-write, download, mode,
reset, or configuration service.
"""
from __future__ import annotations

import argparse
import json
import socket
import statistics
import struct
import sys
import time
from dataclasses import dataclass
from typing import Any


ENCAP_HEADER = struct.Struct("<HHII8sI")
ENCAP_LIST_IDENTITY = 0x0063
ENCAP_REGISTER_SESSION = 0x0065
ENCAP_UNREGISTER_SESSION = 0x0066
ENCAP_SEND_RR_DATA = 0x006F

CIP_GET_ATTRIBUTE_SINGLE = 0x0E
CIP_TCPIP_INTERFACE_CLASS = 0xF5
CIP_TCPIP_INTERFACE_INSTANCE = 1
CIP_TIME_SYNC_CLASS = 0x43
CIP_TIME_SYNC_INSTANCE = 1


class ProbeError(RuntimeError):
    """Raised when an EtherNet/IP or CIP response is malformed or unsuccessful."""


@dataclass(frozen=True)
class EncapReply:
    command: int
    session: int
    payload: bytes


def _recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ProbeError("connection closed before the complete response arrived")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _exchange(
    sock: socket.socket,
    command: int,
    payload: bytes = b"",
    session: int = 0,
    context: bytes = b"FRKPROBE",
) -> EncapReply:
    sock.sendall(ENCAP_HEADER.pack(command, len(payload), session, 0, context, 0) + payload)
    header = _recv_exact(sock, ENCAP_HEADER.size)
    reply_command, length, reply_session, status, reply_context, _ = ENCAP_HEADER.unpack(header)
    reply_payload = _recv_exact(sock, length)
    if reply_command != command:
        raise ProbeError(f"encapsulation command mismatch: 0x{reply_command:04X}")
    if reply_context != context:
        raise ProbeError("encapsulation sender context mismatch")
    if status:
        raise ProbeError(f"encapsulation status 0x{status:08X}")
    return EncapReply(reply_command, reply_session, reply_payload)


def _parse_identity(payload: bytes) -> dict[str, Any]:
    if len(payload) < 4:
        raise ProbeError("short ListIdentity payload")
    item_count = struct.unpack_from("<H", payload)[0]
    offset = 2
    for _ in range(item_count):
        if offset + 4 > len(payload):
            raise ProbeError("truncated ListIdentity item header")
        item_type, item_length = struct.unpack_from("<HH", payload, offset)
        offset += 4
        item = payload[offset:offset + item_length]
        offset += item_length
        if item_type != 0x000C:
            continue
        if len(item) < 34:
            raise ProbeError("short CIP identity item")
        protocol_version = struct.unpack_from("<H", item, 0)[0]
        family, port = struct.unpack_from(">HH", item, 2)
        socket_address = socket.inet_ntoa(item[6:10])
        vendor_id, device_type, product_code = struct.unpack_from("<HHH", item, 18)
        major, minor = item[24], item[25]
        device_status = struct.unpack_from("<H", item, 26)[0]
        serial = struct.unpack_from("<I", item, 28)[0]
        name_length = item[32]
        if 33 + name_length >= len(item):
            raise ProbeError("truncated product name in CIP identity item")
        product_name = item[33:33 + name_length].decode("utf-8", errors="replace")
        state = item[33 + name_length]
        return {
            "protocol_version": protocol_version,
            "socket_family": family,
            "socket_address": socket_address,
            "socket_port": port,
            "vendor_id": vendor_id,
            "device_type": device_type,
            "product_code": product_code,
            "revision": f"{major}.{minor:03d}",
            "device_status": device_status,
            "serial_number": f"{serial:08X}",
            "product_name": product_name,
            "state": state,
        }
    raise ProbeError("ListIdentity response contains no CIP identity item")


def list_identity(target: str, port: int, timeout: float) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    with socket.create_connection((target, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        reply = _exchange(sock, ENCAP_LIST_IDENTITY)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return _parse_identity(reply.payload), elapsed_ms


def _register_session(sock: socket.socket) -> int:
    reply = _exchange(sock, ENCAP_REGISTER_SESSION, struct.pack("<HH", 1, 0))
    if len(reply.payload) != 4 or struct.unpack("<HH", reply.payload) != (1, 0):
        raise ProbeError("unexpected RegisterSession response")
    if reply.session == 0:
        raise ProbeError("controller returned a zero session handle")
    return reply.session


def _cip_attribute(
    sock: socket.socket,
    session: int,
    attribute: int,
    *,
    class_id: int = CIP_TCPIP_INTERFACE_CLASS,
    instance_id: int = CIP_TCPIP_INTERFACE_INSTANCE,
) -> bytes:
    # Three one-byte logical segments: class, instance, attribute.
    path = bytes((0x20, class_id,
                  0x24, instance_id,
                  0x30, attribute))
    cip = bytes((CIP_GET_ATTRIBUTE_SINGLE, len(path) // 2)) + path
    cpf = struct.pack("<IHHHHHH", 0, 0, 2, 0x0000, 0, 0x00B2, len(cip)) + cip
    reply = _exchange(sock, ENCAP_SEND_RR_DATA, cpf, session)
    if len(reply.payload) < 8:
        raise ProbeError("short SendRRData response")
    item_count = struct.unpack_from("<H", reply.payload, 6)[0]
    offset = 8
    for _ in range(item_count):
        if offset + 4 > len(reply.payload):
            raise ProbeError("truncated CPF item header")
        item_type, item_length = struct.unpack_from("<HH", reply.payload, offset)
        offset += 4
        item = reply.payload[offset:offset + item_length]
        offset += item_length
        if item_type not in (0x00B1, 0x00B2):
            continue
        if len(item) < 4:
            raise ProbeError("short CIP response")
        service, _, general_status, additional_words = struct.unpack_from("BBBB", item)
        if service != (CIP_GET_ATTRIBUTE_SINGLE | 0x80):
            raise ProbeError(f"unexpected CIP reply service 0x{service:02X}")
        if general_status:
            additional = item[4:4 + additional_words * 2].hex().upper()
            raise ProbeError(
                f"CIP class 0x{class_id:02X} attribute {attribute} "
                f"status 0x{general_status:02X}; "
                f"additional={additional or 'none'}"
            )
        return item[4 + additional_words * 2:]
    raise ProbeError("SendRRData response contains no unconnected-data item")


def _cip_string(data: bytes) -> str:
    if len(data) < 2:
        raise ProbeError("short CIP STRING value")
    length = struct.unpack_from("<H", data)[0]
    if 2 + length > len(data):
        raise ProbeError("truncated CIP STRING value")
    return data[2:2 + length].decode("utf-8", errors="replace")


def _ipv4_fields(data: bytes, expected_address: str) -> dict[str, Any]:
    if len(data) < 20:
        raise ProbeError("short TCP/IP Interface Configuration value")
    direct_address = socket.inet_ntoa(data[0:4])
    reverse_address = socket.inet_ntoa(data[0:4][::-1])
    reverse = reverse_address == expected_address and direct_address != expected_address

    def decode(chunk: bytes) -> str:
        return socket.inet_ntoa(chunk[::-1] if reverse else chunk)

    domain = _cip_string(data[20:]) if len(data) > 20 else ""
    return {
        "address": decode(data[0:4]),
        "network_mask": decode(data[4:8]),
        "gateway": decode(data[8:12]),
        "primary_name_server": decode(data[12:16]),
        "secondary_name_server": decode(data[16:20]),
        "domain_name": domain,
        "byte_order": "reversed-per-field" if reverse else "network",
    }


def read_tcpip_interface(target: str, port: int, timeout: float) -> dict[str, Any]:
    with socket.create_connection((target, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        session = _register_session(sock)
        try:
            status = _cip_attribute(sock, session, 1)
            capability = _cip_attribute(sock, session, 2)
            control = _cip_attribute(sock, session, 3)
            configuration = _cip_attribute(sock, session, 5)
            host_name = _cip_attribute(sock, session, 6)
        finally:
            # UnregisterSession has no response by specification.
            sock.sendall(ENCAP_HEADER.pack(
                ENCAP_UNREGISTER_SESSION, 0, session, 0, b"FRKPROBE", 0
            ))
    if min(len(status), len(capability), len(control)) < 4:
        raise ProbeError("short TCP/IP Interface scalar attribute")
    control_value = struct.unpack_from("<I", control)[0]
    return {
        "status_raw": struct.unpack_from("<I", status)[0],
        "configuration_capability_raw": struct.unpack_from("<I", capability)[0],
        "configuration_control_raw": control_value,
        "startup_configuration_raw": control_value & 0x0F,
        "interface_configuration": _ipv4_fields(configuration, target),
        "host_name": _cip_string(host_name),
    }


def read_time_sync(target: str, port: int, timeout: float) -> dict[str, Any]:
    """Read the fixed PTP-enable and synchronized status attributes."""
    with socket.create_connection((target, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        session = _register_session(sock)
        try:
            ptp_enable = _cip_attribute(
                sock, session, 1,
                class_id=CIP_TIME_SYNC_CLASS,
                instance_id=CIP_TIME_SYNC_INSTANCE,
            )
            synchronized = _cip_attribute(
                sock, session, 2,
                class_id=CIP_TIME_SYNC_CLASS,
                instance_id=CIP_TIME_SYNC_INSTANCE,
            )
        finally:
            sock.sendall(ENCAP_HEADER.pack(
                ENCAP_UNREGISTER_SESSION, 0, session, 0, b"FRKPROBE", 0
            ))
    if len(ptp_enable) not in (1, 2, 4) or len(synchronized) not in (1, 2, 4):
        raise ProbeError("unexpected Time Sync scalar attribute size")
    return {
        "ptp_enabled": bool(int.from_bytes(ptp_enable, "little", signed=True)),
        "ptp_enable_size": len(ptp_enable),
        "is_synchronized": bool(int.from_bytes(synchronized, "little", signed=True)),
        "is_synchronized_size": len(synchronized),
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="single controller IPv4 address or host name")
    parser.add_argument("--port", type=int, default=44818)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--expect-serial", help="eight-digit hexadecimal CIP serial")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if not 1 <= args.samples <= 100:
        parser.error("--samples must be between 1 and 100")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main() -> int:
    args = _arguments()
    try:
        identities: list[dict[str, Any]] = []
        latencies: list[float] = []
        for _ in range(args.samples):
            identity, latency = list_identity(args.target, args.port, args.timeout)
            identities.append(identity)
            latencies.append(latency)
        if any(item != identities[0] for item in identities[1:]):
            raise ProbeError("identity changed between samples")
        expected = args.expect_serial.upper() if args.expect_serial else None
        serial_matches = expected is None or identities[0]["serial_number"] == expected
        evidence = {
            "schema": "fraktal.ab.eip-read-probe",
            "schema_version": 1,
            "target": args.target,
            "port": args.port,
            "samples": args.samples,
            "identity": identities[0],
            "expected_serial": expected,
            "serial_matches": serial_matches,
            "identity_latency_ms": {
                "minimum": round(min(latencies), 3),
                "median": round(statistics.median(latencies), 3),
                "maximum": round(max(latencies), 3),
            },
            "tcpip_interface": read_tcpip_interface(args.target, args.port, args.timeout),
            "time_sync": read_time_sync(args.target, args.port, args.timeout),
        }
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0 if serial_matches else 1
    except (OSError, ProbeError) as exc:
        print(f"ERROR [eip-read-probe] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

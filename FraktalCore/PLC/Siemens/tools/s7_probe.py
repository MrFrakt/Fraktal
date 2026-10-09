"""Fraktal/TIA bench probe over classic S7comm (ISO-on-TCP, port 102).

Read-only by construction: the only services sent are COTP connect, S7
setup-communication, SZL read (identification) and ReadVar on a data block.
There is no write, no PLC-control and no download code in this file.

    python s7_probe.py ident   [--host 192.168.0.10]
    python s7_probe.py szl     --id 0x0424 [--index 0]
    python s7_probe.py harvest --tcp 2000 [--host ...] [--junit out.xml]
    python s7_probe.py harvest --db N     [--host ...] [--junit out.xml]

`ident` works on an S7-1200/1500 with PUT/GET disabled (SZL identification).
`harvest` reads the Phase 0 self-test result table ("SpkResults".T, standard
layout, Spikes/S2_Shape/05_GlobalData.db): with --tcp from the test image's
own result server (no licence, no PUT/GET; the host only receives), or with
--db over PUT/GET where a project permits it (Part IV §5.7).
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys
import xml.sax.saxutils as su

RESULT_MAGIC = 0x46524B31  # 'FRK1'
RESULT_ROWS = 32
ROW_BYTES = 12
HEADER_BYTES = 12

CASES = {
    1: "T1 CylA EXTEND completes",
    2: "T1 idle after Execute drop",
    3: "T4 abort mid-move: Aborted, coils off",
    4: "T4 no self-resume",
    5: "T2 feedback withheld -> ErrorID 2001",
    6: "T2 SourcePath = SpikeUnit.CylB",
    7: "Execute drop clears ERROR and first-out",
    8: "T3 interlock open -> HELD: busy, coils off, 2003 at LOW",
    9: "identity from GetInstancePath",
    10: "registry rows and parentage",
    11: "mailbox SET_MODE AUTO acknowledged",
    12: "mailbox START -> Unit BUSY",
    13: "S11 chain trace 0,100,110,120,100,110",
    14: "STOP -> Unit READY, child commands released",
    15: "T6 Unit adopts CylA first-out verbatim",
    16: "OPERATOR_RESET -> Unit and CylA READY",
    17: "T3 interlock restored -> resumes to DONE",
}


class S7Session:
    """One ISO-on-TCP connection with a negotiated S7 PDU size."""

    def __init__(self, host: str, rack: int = 0, slot: int = 1, timeout: float = 3.0):
        self.sock = socket.create_connection((host, 102), timeout=timeout)
        self.ref = 0
        cr = bytes([0x11, 0xE0, 0, 0, 0, 1, 0, 0xC0, 1, 0x0A, 0xC1, 2, 1, 0,
                    0xC2, 2, 1, rack * 32 + slot])
        self._send(cr)
        cc = self._recv()
        if cc[1] != 0xD0:
            raise ConnectionError("COTP connection refused: " + cc.hex())
        setup = self._header(1, 8, 0) + bytes([0xF0, 0, 0, 1, 0, 1, 0x03, 0xC0])
        self._send_dt(setup)
        reply = self._recv()[3:]
        self.pdu = struct.unpack(">H", reply[-2:])[0]

    def close(self) -> None:
        self.sock.close()

    def _send(self, payload: bytes) -> None:
        self.sock.sendall(struct.pack(">BBH", 3, 0, len(payload) + 4) + payload)

    def _send_dt(self, s7: bytes) -> None:
        self._send(bytes([0x02, 0xF0, 0x80]) + s7)

    def _recv(self) -> bytes:
        header = self._read_exact(4)
        return self._read_exact(struct.unpack(">H", header[2:4])[0] - 4)

    def _read_exact(self, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("connection closed")
            data += chunk
        return data

    def _header(self, rosctr: int, plen: int, dlen: int) -> bytes:
        self.ref = (self.ref + 1) & 0xFFFF
        return struct.pack(">BBHHHH", 0x32, rosctr, 0, self.ref, plen, dlen)

    def szl(self, szl_id: int, index: int) -> list[bytes] | None:
        params = bytes([0x00, 0x01, 0x12, 0x04, 0x11, 0x44, 0x01, 0x00])
        data = bytes([0xFF, 0x09]) + struct.pack(">HHH", 4, szl_id, index)
        self._send_dt(self._header(7, len(params), len(data)) + params + data)
        reply = self._recv()[3:]
        plen, dlen = struct.unpack(">HH", reply[6:10])
        d = reply[10 + plen:10 + plen + dlen]
        if d[0] != 0xFF:
            return None
        body = d[4:]
        _, _, rec_len, count = struct.unpack(">HHHH", body[:8])
        return [body[8 + i * rec_len:8 + (i + 1) * rec_len] for i in range(count)]

    def read_db(self, db: int, start: int, length: int) -> bytes:
        out = b""
        step = self.pdu - 18 - 4
        while length > 0:
            n = min(step, length)
            item = bytes([0x12, 0x0A, 0x10, 0x02]) + struct.pack(">HH", n, db) + bytes([0x84]) \
                + (start * 8).to_bytes(3, "big")
            params = bytes([0x04, 0x01]) + item
            self._send_dt(self._header(1, len(params), 0) + params)
            reply = self._recv()[3:]
            if reply[1] != 0x03:
                raise IOError("unexpected S7 reply " + reply[:12].hex())
            err_class, err_code = reply[10], reply[11]
            if err_class or err_code:
                raise IOError("S7 error class %d code %d" % (err_class, err_code))
            plen = struct.unpack(">H", reply[6:8])[0]
            d = reply[12 + plen:]
            if d[0] != 0xFF:
                raise IOError("read refused (return code 0x%02X): PUT/GET disabled, wrong DB "
                              "number, or the DB is optimized" % d[0])
            nbytes = struct.unpack(">H", d[2:4])[0] // 8
            out += d[4:4 + nbytes]
            start += n
            length -= n
        return out


def cmd_ident(args) -> int:
    s = S7Session(args.host)
    try:
        print("pdu", s.pdu)
        for rec in s.szl(0x0011, 0) or []:
            idx = struct.unpack(">H", rec[:2])[0]
            mlfb = rec[2:22].decode("ascii", "replace").strip()
            tail = rec[22:28]
            version = ""
            if idx == 7 and tail[2:3] == b"V":
                version = "V%d.%d.%d" % (tail[3], tail[4], tail[5])
            print("module idx=%04x order=%s %s raw=%s" % (idx, mlfb, version, tail.hex()))
    finally:
        s.close()
    return 0


def cmd_szl(args) -> int:
    """Raw SZL record dump (read-only). 0x0232/4 = protection: level set by
    the access configuration and the current level, among others."""
    s = S7Session(args.host)
    try:
        recs = s.szl(int(args.id, 0), int(args.index, 0))
    finally:
        s.close()
    if recs is None:
        print("SZL %s index %s refused" % (args.id, args.index))
        return 3
    for rec in recs:
        words = [struct.unpack(">H", rec[i:i + 2])[0] for i in range(0, len(rec) - 1, 2)]
        print("record %s  words=%s" % (rec.hex(), " ".join("%04x" % w for w in words)))
    return 0


def read_table_tcp(host: str, port: int, timeout: float = 5.0) -> bytes:
    """Receive one result table from the test image's FB_SpkResultServer
    (passive TSEND_C): connect, read exactly one table, close. Sends nothing."""
    size = HEADER_BYTES + RESULT_ROWS * ROW_BYTES
    with socket.create_connection((host, port), timeout=timeout) as sock:
        data = b""
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("result server closed after %d of %d bytes" % (len(data), size))
            data += chunk
    return data


def cmd_harvest(args) -> int:
    size = HEADER_BYTES + RESULT_ROWS * ROW_BYTES
    if args.tcp:
        raw = read_table_tcp(args.host, args.tcp)
    else:
        if args.db is None:
            print("harvest: give --tcp PORT (result server) or --db N (PUT/GET)")
            return 2
        s = S7Session(args.host)
        try:
            raw = s.read_db(args.db, 0, size)
        finally:
            s.close()
    magic, = struct.unpack(">I", raw[0:4])
    done = bool(raw[4] & 1)
    passed, failed, count = struct.unpack(">hhh", raw[6:12])
    if magic != RESULT_MAGIC:
        print("result table not initialized (magic %08X)" % magic)
        return 3
    rows = []
    for i in range(min(count, RESULT_ROWS)):
        r = raw[HEADER_BYTES + i * ROW_BYTES:HEADER_BYTES + (i + 1) * ROW_BYTES]
        case_id, = struct.unpack(">h", r[0:2])
        ok = bool(r[2] & 1)
        expected, actual = struct.unpack(">ii", r[4:12])
        rows.append((case_id, ok, expected, actual))
        print("case %2d %-4s expected=%d actual=%d  %s"
              % (case_id, "PASS" if ok else "FAIL", expected, actual, CASES.get(case_id, "")))
    print("done=%s passed=%d failed=%d rows=%d" % (done, passed, failed, count))
    if args.junit:
        with open(args.junit, "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            fh.write('<testsuite name="Fraktal.TIA.S2" tests="%d" failures="%d">\n' % (len(rows), failed))
            for case_id, ok, expected, actual in rows:
                name = su.quoteattr("%02d %s" % (case_id, CASES.get(case_id, "case")))
                fh.write('  <testcase classname="S2_Shape" name=%s>' % name)
                if not ok:
                    fh.write('<failure message=%s/>' % su.quoteattr("expected %d actual %d" % (expected, actual)))
                fh.write('</testcase>\n')
            fh.write('</testsuite>\n')
    if not done:
        return 4
    return 0 if failed == 0 and count > 0 else 1


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ident")
    pi.add_argument("--host", default="192.168.0.10")
    pz = sub.add_parser("szl")
    pz.add_argument("--host", default="192.168.0.10")
    pz.add_argument("--id", required=True, help="SZL id, e.g. 0x0232")
    pz.add_argument("--index", default="0", help="SZL index, e.g. 4")
    ph = sub.add_parser("harvest")
    ph.add_argument("--host", default="192.168.0.10")
    ph.add_argument("--db", type=int, help="result DB number (PUT/GET path)")
    ph.add_argument("--tcp", type=int, help="result-server TCP port (test image, e.g. 2000)")
    ph.add_argument("--junit")
    args = p.parse_args(argv)
    return {"ident": cmd_ident, "szl": cmd_szl, "harvest": cmd_harvest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

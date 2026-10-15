"""S11 only: guarded STOP/RUN on the authorized, disconnected 1214C bench.

The read-only s7_probe stays read-only. This tool offers no download, memory
reset, tag write or configuration change. It confirms the fixed IP, order and
firmware before either control request, then checks the returned operating state.
Run s7_probe.py ident immediately before each invocation, as the handover requires.

Wire layouts: Snap7's primary source, src/core/s7_micro_client.cpp (opPlcStop /
opPlcHotStart) and src/core/s7_types.h (TReqFunPlcStop / TReqFunPlcHotStart).
https://github.com/SCADACS/snap7/tree/master/src/core
"""
import argparse
import datetime
import json
import struct
import time

from s7_probe import S7Session

HOST = "192.168.0.10"
ORDER = "6ES7 214-1AG40-0XB0"
FIRMWARE = b"V\x04\x07\x03"


def emit(event, **values):
    print(json.dumps(dict(t=datetime.datetime.now(datetime.timezone.utc).isoformat(), event=event, **values)), flush=True)


def confirm(session, target):
    if target != HOST:
        raise ValueError("--confirm-target must name the authorized bench " + HOST)
    records = session.szl(0x0011, 0) or []
    firmware = next((r for r in records if len(r) >= 28 and r[:2] == b"\x00\x07"), None)
    if firmware is None or firmware[2:22].decode("ascii").strip() != ORDER or firmware[24:28] != FIRMWARE:
        raise ValueError("bench order/firmware does not match the authorized 1214C V4.7.3")
    emit("target-confirmed", host=HOST, order=ORDER, firmware="V4.7.3")


def state(session):
    records = session.szl(0x0424, 0) or []
    if not records or len(records[0]) < 4:
        raise ValueError("operating-state SZL unavailable")
    code = records[0][3]
    # Native web STOP on the 1214C V4.7.3 reports 03, verified against its
    # authenticated page (S11 native evidence). Snap7 also accepts this STOP form.
    if code not in (3, 4, 6, 8):
        raise ValueError("unknown operating-state code 0x%02x" % code)
    return "run" if code == 8 else "startup" if code == 6 else "stop"


def change(session, mode, target):
    confirm(session, target)
    before = state(session)
    emit("before", mode=before)
    if before not in ("run", "stop"):
        raise ValueError("CPU is starting; wait for a stable operating mode")
    if before == mode:
        raise ValueError("bench already in requested mode; no transition measured")
    params = (b"\x29" + bytes(5) + b"\x09P_PROGRAM" if mode == "stop"
              else b"\x28" + bytes(6) + b"\xfd\x00\x00\x09P_PROGRAM")
    session._send_dt(session._header(1, len(params), 0) + params)
    reply = session._recv()[3:]
    if len(reply) < 12 or reply[1] not in (2, 3):
        raise ValueError("unexpected control response " + reply.hex())
    error = struct.unpack(">H", reply[10:12])[0]
    emit("control-response", requested=mode, error=error, response=reply.hex())
    if error:
        raise ValueError("CPU refused the mode change (0x%04x)" % error)
    if reply[1] != 3:
        raise ValueError("control response has no acknowledgement data")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        after = state(session)
        if after == mode:
            emit("after", mode=after)
            return
        time.sleep(0.05)
    raise TimeoutError("mode change not confirmed")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("mode", choices=("status", "stop", "run"))
    parser.add_argument("--confirm-target")
    args = parser.parse_args()
    if args.mode != "status" and args.confirm_target != HOST:
        parser.error("--confirm-target " + HOST + " is required")
    session = S7Session(HOST)
    try:
        if args.mode == "status":
            emit("state", mode=state(session))
        else:
            change(session, args.mode, args.confirm_target)
    finally:
        session.close()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TimeoutError) as error:
        emit("failed", message=str(error))
        raise SystemExit(1)

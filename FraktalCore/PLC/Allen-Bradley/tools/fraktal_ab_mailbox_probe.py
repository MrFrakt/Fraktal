#!/usr/bin/env python3
"""Measure whether pylogix can write a user ``StringFamily`` member.

The command-mailbox handover names this as the one assumption behind the write
path that is **reasoned rather than measured**: ``MailboxWriter`` writes a
string argument as ``LEN`` plus ``DATA`` because these are user
``StringFamily`` types and not the built-in ``STRING``. The HMI writes five
string members on every command - usually empty - so if this does not work,
nothing works. It is the same class of assumption that string-literal
assignment in ST turned out to violate: the SDK imported 21 of those at 0
errors and Studio Verify rejected exactly 21.

So it is measured here, on its own, before a command is ever committed.

**Nothing here commands the machine.** Every write targets an ``HmiRequest``
*argument*. The controller's handler consumes a request only when ``Sequence``
changes, and this probe never writes ``Sequence`` - there is no code path in
this file that can. Arguments left behind are restored, and the final read
shows what the mailbox was left holding.

Writing still changes a controller, so the serial guard is required rather than
optional and the writes are armed explicitly: a tool that writes by default is
one accident away from writing to the wrong controller.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import fraktal_ab_mailbox as mailbox
import fraktal_ab_projection as projection

REQUEST_TAG = "FRK_Press_HmiRequest"

# The member this probe exercises. TargetPath is the right choice: it is the one
# string a routed kind actually reads (MANUAL_COMMAND refuses a non-empty one),
# so both its empty and non-empty forms matter to real behaviour.
PROBE_MEMBER = "TargetPath"
PROBE_TEXT = "Press.PressRam"


def _read(comm: Any, *tags: str) -> dict[str, tuple[Any, Any]]:
    out: dict[str, tuple[Any, Any]] = {}
    for tag in tags:
        # An array read issued without an element count returns element zero and
        # *succeeds* - the defect the manifest read recorded in
        # AB_MANIFEST_CONTROLLER_READ_2026-09-08 §4. DATA is an array, so it is
        # read with a count or the readback would silently mean nothing.
        if tag.endswith(".DATA"):
            reply = comm.Read(tag, len(PROBE_TEXT))
        else:
            reply = comm.Read(tag)
        value = getattr(reply, "Value", None)
        if isinstance(value, list):
            value = "".join(chr(c) for c in value if 0 < c < 128) or value[:16]
        out[tag] = (getattr(reply, "Status", "?"), value)
    return out


def _show(comm: Any, label: str, *tags: str) -> None:
    print(f"  {label}")
    for tag, (status, value) in _read(comm, *tags).items():
        print(f"    {tag} -> {status} {value!r}")


def _write(comm: Any, tag: str, payload: Any) -> bool:
    from fraktal_ab_s16_execute import _success

    reply = comm.Write(tag, payload)
    ok = _success(reply)
    print(f"    write {tag} := {payload!r} -> "
          f"{getattr(reply, 'Status', '?')} {'OK' if ok else 'FAILED'}")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="controller IPv4 address")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--slot", type=int, default=0)
    parser.add_argument("--arm-writes", action="store_true",
                        help="actually write. Without it this reports read-only.")
    args = parser.parse_args(argv)

    from pylogix import PLC

    from fraktal_ab_s16_execute import _normalize_serial

    len_tag = f"{REQUEST_TAG}.{PROBE_MEMBER}.LEN"
    data_tag = f"{REQUEST_TAG}.{PROBE_MEMBER}.DATA"
    findings: list[str] = []

    with PLC() as comm:
        comm.IPAddress = args.target
        comm.ProcessorSlot = args.slot

        serial, ok = projection.verify_serial(comm, args.expect_serial)
        if not ok:
            print(f"serial {serial} is not the expected "
                  f"{_normalize_serial(args.expect_serial)}; refusing",
                  file=sys.stderr)
            return 2
        print(f"identity verified: serial={serial}")

        print("\n=== baseline (read-only) ===")
        _show(comm, "mailbox as found:",
              f"{REQUEST_TAG}.Sequence", f"{REQUEST_TAG}.Kind", len_tag, data_tag)

        if not args.arm_writes:
            print("\nnot armed: no write was issued. Re-run with --arm-writes "
                  "to measure the StringFamily write.")
            return 0

        try:
            # 1. A scalar DINT member first. If this fails the string question is
            #    moot, and separating them keeps a failure attributable.
            print("\n=== 1. scalar DINT member (Kind := 0, inert) ===")
            if not _write(comm, f"{REQUEST_TAG}.Kind", 0):
                findings.append("a DINT member of the mailbox did not write")

            # 2. LEN only. This is the common path: every routed kind takes no
            #    string content, so a command writes one length per string.
            print(f"\n=== 2. StringFamily LEN ({PROBE_MEMBER} := '', inert) ===")
            if not _write(comm, len_tag, 0):
                findings.append("LEN of a StringFamily member did not write")
            _show(comm, "read back:", len_tag)

            # 3. LEN + DATA, the addressed form. MANUAL_COMMAND's refusal path
            #    depends on LEN reflecting a non-empty TargetPath.
            print(f"\n=== 3. StringFamily LEN+DATA "
                  f"({PROBE_MEMBER} := {PROBE_TEXT!r}, inert) ===")
            payload = [ord(c) for c in PROBE_TEXT]
            if not _write(comm, data_tag, payload):
                findings.append("DATA of a StringFamily member did not write")
            if not _write(comm, len_tag, len(PROBE_TEXT)):
                findings.append("LEN did not write after DATA")
            _show(comm, "read back:", len_tag, data_tag)
        finally:
            # Leave the mailbox as it was found, whatever happened above.
            print(f"\n=== restore ({PROBE_MEMBER} := '') ===")
            _write(comm, len_tag, 0)
            _write(comm, data_tag, [0] * len(PROBE_TEXT))
            _show(comm, "final:", f"{REQUEST_TAG}.Sequence",
                  f"{REQUEST_TAG}.Kind", len_tag, data_tag)

    print("\nSequence was never written, so no request was ever committed and "
          "the controller has not been commanded.")
    if findings:
        print("\nFINDINGS:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("\nNo findings: the StringFamily write path is measured, not reasoned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

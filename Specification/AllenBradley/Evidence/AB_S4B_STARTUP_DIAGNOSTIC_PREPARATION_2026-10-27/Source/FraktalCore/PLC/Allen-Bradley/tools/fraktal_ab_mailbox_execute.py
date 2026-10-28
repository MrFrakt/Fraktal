#!/usr/bin/env python3
"""Drive the controller-resident command mailbox through the gateway.

This is the mailbox's evidence harness. It speaks the HMI's own
``fraktal.opcua.gateway.v1`` protocol to a running ``fraktal_ab_gateway``,
commits requests exactly the way ``opcua_repository.dart`` does - every argument
first, ``Sequence`` last as the commit marker - and then proves each command by
reading the controller's own acknowledgement back. A write that returned true is
not evidence; a matching ``AckSequence`` is.

It exists because the Flutter HMI cannot be the client on every host. The HMI
refuses to attach a bearer token to a ``ws://`` endpoint, and where TLS is
intercepted by endpoint security the HMI cannot verify a loopback gateway at
all. That is a transport narrowing, not a mailbox one: everything the controller
and the gateway do is identical whoever holds the socket, and this harness
proves that half on hardware.

**This writes to a controller.** It is armed explicitly, it refuses unless the
gateway reports the expected content hash, and the gateway re-checks the
controller serial immediately before every write it forwards.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Optional

import fraktal_ab_mailbox as mailbox

# The same variable the HMI client reads its bearer from, so one exported secret
# serves both and neither needs it on a command line (Core §14.2/§14.3).
BEARER_ENV = "FRAKTAL_GATEWAY_BEARER_TOKEN"

UNIT = "Press"
REQUEST = f"{UNIT}/HmiRequest"
RESPONSE = f"{UNIT}/HmiResponse"
ACK = f"{RESPONSE}/AckSequence"
ACCEPTED = f"{RESPONSE}/Accepted"
DIAGNOSTIC = f"{RESPONSE}/Diagnostic"
MODE = f"{UNIT}/ModeActivePublished"

PROTOCOL = "fraktal.opcua.gateway.v1"


class Client:
    """The gateway protocol, as the HMI speaks it."""

    def __init__(self, socket: Any) -> None:
        self._socket = socket
        self._id = 0
        self._paths: list[str] = []
        self._revision = 0

    async def call(self, method: str, params: Optional[dict] = None) -> Any:
        self._id += 1
        await self._socket.send(json.dumps({
            "protocol": PROTOCOL, "id": self._id,
            "method": method, "params": params or {}}))
        reply = json.loads(await self._socket.recv())
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error", "refused"))
        return reply.get("result")

    async def refused(self, method: str, params: Optional[dict] = None) -> str:
        """The error text, for a call that is supposed to be refused."""
        self._id += 1
        await self._socket.send(json.dumps({
            "protocol": PROTOCOL, "id": self._id,
            "method": method, "params": params or {}}))
        reply = json.loads(await self._socket.recv())
        if reply.get("ok"):
            raise RuntimeError(f"{method} was accepted but should be refused")
        return reply.get("error", "")

    async def discover(self) -> None:
        result = await self.call("discoverPaths")
        self._revision = result["revision"]
        self._paths = list(result["paths"])

    async def read(self, *paths: str) -> dict[str, Any]:
        indices = [self._paths.index(p) for p in paths]
        return await self.call(
            "readValues", {"revision": self._revision, "indices": indices})

    async def snapshot(self) -> dict[str, Any]:
        return await self.call("snapshot")

    def commit_writes(self, sequence: int, kind: int, *, int_value: int = 0,
                      target_path: str = "", bool_value: bool = False,
                      duration_ms: int = 0, name_value: str = "",
                      text_value: str = "", user: str = "",
                      secret: str = "") -> list[dict]:
        """The ten writes a command is, in the HMI's order."""
        def w(member: str, vtype: str, value: Any) -> dict:
            return {"path": f"{REQUEST}/{member}",
                    "valueType": vtype, "value": value}

        return [
            w("Kind", "int32", kind),
            w("TargetPath", "string", target_path),
            w("NameValue", "string", name_value),
            w("TextValue", "string", text_value),
            w("User", "string", user),
            w("Secret", "string", secret),
            w("IntValue", "int32", int_value),
            w("BoolValue", "boolean", bool_value),
            w("DurationMs", "uint32", duration_ms),
            # Last, always: the commit marker.
            w("Sequence", "uint32", sequence),
        ]


async def await_ack(client: Client, sequence: int,
                    timeout: float = 5.0) -> dict[str, Any]:
    """Poll until the controller acknowledges this sequence."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        values = await client.read(ACK, ACCEPTED, DIAGNOSTIC, MODE)
        if values.get(ACK) == sequence:
            return values
        await asyncio.sleep(0.1)
    raise TimeoutError(f"no acknowledgement of sequence {sequence}")


class Run:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, label: str, ok: bool, detail: str) -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: {detail}")
        if not ok:
            self.failures.append(f"{label}: {detail}")


async def command(client: Client, run: Run, label: str, sequence: int,
                  kind: int, *, expect_accepted: bool,
                  expect_diagnostic: str = "", **kwargs: Any) -> dict[str, Any]:
    ok = await client.call(
        "writeBatch",
        {"writes": client.commit_writes(sequence, kind, **kwargs)})
    if not ok:
        run.check(label, False, "the gateway did not commit the batch")
        return {}
    answer = await await_ack(client, sequence)
    accepted = bool(answer.get(ACCEPTED))
    diagnostic = answer.get(DIAGNOSTIC, "")
    detail = (f"seq={sequence} ack={answer.get(ACK)} accepted={accepted} "
              f"diag='{diagnostic}' mode={answer.get(MODE)}")
    good = accepted == expect_accepted
    if expect_diagnostic:
        good = good and diagnostic == expect_diagnostic
    run.check(label, good, detail)
    return answer


async def main_async(args: argparse.Namespace) -> int:
    from websockets.asyncio.client import connect

    endpoint = args.endpoint
    origin = args.origin
    headers = {"Origin": origin}
    token = args.token
    run = Run()

    print(f"=== gateway {endpoint} ===")

    # 1. The §14 gate, before anything is committed. An anonymous session must
    #    not be able to write at all, and it must be refused by the gateway
    #    rather than by the controller.
    print("\n=== negatives at the gate (no controller write occurs) ===")
    async with connect(endpoint, additional_headers=headers) as anon_socket:
        anon = Client(anon_socket)
        await anon.discover()
        error = await anon.refused("writeBatch", {
            "writes": anon.commit_writes(1, mailbox.START)})
        run.check("anonymous write refused", "anonymous" in error.lower(), error)

    async with connect(endpoint,
                       additional_headers={**headers,
                                           "Authorization": f"Bearer {token}"}) as socket:
        client = Client(socket)
        await client.discover()

        document = await client.snapshot()
        content_hash = document.get("contentHash")
        print(f"\ncontroller contentHash={content_hash} "
              f"configRevision={document.get('configRevision')}")
        if args.expect_content_hash and content_hash != args.expect_content_hash:
            print(f"content hash {content_hash} is not the expected "
                  f"{args.expect_content_hash}; refusing", file=sys.stderr)
            return 2

        # A write outside the mailbox is refused by scope, never forwarded.
        error = await client.refused("write", {
            "path": f"{UNIT}/Status/State", "valueType": "int32", "value": 1})
        run.check("off-mailbox write refused", "scope" in error.lower(), error)

        values = await client.read(f"{REQUEST}/Sequence", ACK, ACCEPTED,
                                   DIAGNOSTIC, MODE)
        print(f"\nmailbox as found: {values}")
        start_seq = max(int(values.get(f"{REQUEST}/Sequence") or 0),
                        int(values.get(ACK) or 0))

        # A sequence the controller has already answered must be refused.
        error = await client.refused("writeBatch", {
            "writes": client.commit_writes(start_seq, mailbox.START)})
        run.check("replayed sequence refused", "stale" in error.lower(), error)

        if not args.arm_writes:
            print("\nnot armed: no command was committed. Re-run with "
                  "--arm-writes to drive the mailbox.")
            return 1 if run.failures else 0

        seq = start_seq
        print("\n=== the six kinds this binding routes ===")
        seq += 1
        answer = await command(client, run, "SET_MODE(MANUAL)", seq,
                               mailbox.SET_MODE, int_value=1,
                               expect_accepted=True)
        run.check("mode published is the mode asked for",
                  answer.get(MODE) == 1, f"ModeActivePublished={answer.get(MODE)}")

        for label, kind, kwargs in (
            ("START", mailbox.START, {}),
            ("STOP", mailbox.STOP, {}),
            ("OPERATOR_RESET", mailbox.OPERATOR_RESET, {}),
            ("DECISION_ANSWER(1)", mailbox.DECISION_ANSWER, {"int_value": 1}),
            ("MANUAL_COMMAND(unaddressed)", mailbox.MANUAL_COMMAND, {}),
        ):
            seq += 1
            await command(client, run, label, seq, kind,
                          expect_accepted=True, **kwargs)

        print("\n=== refusals: named, not silent and not falsely accepted ===")
        seq += 1
        await command(client, run, "LAMP_TEST refused", seq, mailbox.LAMP_TEST,
                      expect_accepted=False,
                      expect_diagnostic="project.mailbox.refused.no_signal_tower")
        seq += 1
        await command(client, run, "MANUAL_COMMAND(addressed) refused", seq,
                      mailbox.MANUAL_COMMAND, target_path="Press.PressRam",
                      expect_accepted=False,
                      expect_diagnostic="project.mailbox.refused.target_not_addressable")
        seq += 1
        await command(client, run, "SET_MODE(undeclared) refused", seq,
                      mailbox.SET_MODE, int_value=3, expect_accepted=False,
                      expect_diagnostic="project.mailbox.refused.mode_not_declared")

        print("\n=== restore ===")
        seq += 1
        answer = await command(client, run, "SET_MODE(AUTO)", seq,
                               mailbox.SET_MODE, int_value=0,
                               expect_accepted=True)
        run.check("restored to AUTO", answer.get(MODE) == 0,
                  f"ModeActivePublished={answer.get(MODE)}")

    print("\n" + ("FAILURES:" if run.failures else "No findings."))
    for failure in run.failures:
        print(f"  - {failure}")
    return 1 if run.failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="ws://127.0.0.1:8080/fraktal")
    parser.add_argument("--origin", default="http://127.0.0.1:8080")
    parser.add_argument("--token", default=os.environ.get(BEARER_ENV, ""),
                        help=f"the gateway's Core §14 bearer token. Prefer "
                             f"{BEARER_ENV} in the environment: argv is "
                             f"world-readable in a process listing.")
    parser.add_argument("--expect-content-hash", default="",
                        help="refuse unless the controller publishes this")
    parser.add_argument("--arm-writes", action="store_true",
                        help="actually command. Without it only the gate "
                             "negatives run, which write nothing.")
    args = parser.parse_args(argv)
    if not args.token:
        parser.error(f"no bearer token: export {BEARER_ENV} (preferred) or "
                     f"pass --token. Without one every write is refused.")
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Serve the Allen-Bradley projection to the Fraktal HMI over its own protocol.

The generic Fraktal HMI speaks one WebSocket protocol, ``fraktal.opcua.gateway.v1``
(see ``FraktalCore/HMI/lib/data/opcua_gateway_client_io.dart`` and the reference
Dart server in ``FraktalCore/HMI/gateway``). It asks for a flat
``{browsePath: value}`` snapshot, discovers the stable path list, and then reads
values by index. ``fraktal_ab_projection`` already turns a live Logix controller
into exactly that flat document. This is the transport in between: it wraps the
projection in the protocol, so no AB-specific screen or repository is needed.

**It is read-only, and it fails closed on writes.** Per AB §11.2.1 the binding
is configured with no write root: ``write`` and ``writeBatch`` are refused with a
clear reason before the controller ever sees them, and the HMI is meant to be
seen degrading gracefully rather than appearing to command a machine it cannot.
Enabling writes is not a change to make here on judgement - it rearms Core §14
in full and is a decision for the user, recorded in the binding record.

The gateway binds loopback only, like the reference server: a remote browser
reaches it through a same-host TLS reverse proxy that owns authentication. It
mirrors the reference server's origin check, revision discipline and health
routes so the HMI cannot tell the two transports apart.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import http
import ipaddress
import json
import logging
import sys
import time
from typing import Any, Callable, Optional
from urllib.parse import urlparse

PROTOCOL = "fraktal.opcua.gateway.v1"
WS_PATH = "/fraktal"
# The client chunks a targeted read into blocks of this size; the reference
# server caps a single read the same way. Kept identical so neither surprises.
MAX_TARGET_READ_PATHS = 512
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
# One controller read serves every request that arrives inside this window, so a
# cyclic snapshot+readValues pair sees one consistent station state and the
# controller is read about once per HMI cycle rather than once per method.
CACHE_TTL_S = 0.25

WRITE_REFUSED = (
    "read-only Allen-Bradley gateway (AB §11.2.1): configured with no write "
    "root; operator commands are refused before the controller sees them"
)

log = logging.getLogger("fraktal.ab.gateway")


class StaleRevision(Exception):
    """The client's discovery revision no longer matches; it must discover again."""


# --- pure protocol bookkeeping, testable without a socket or a controller ---

def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _normalize_origin(value: str) -> str:
    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    default = 443 if scheme == "https" else 80
    port = parsed.port
    if port and port != default:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def accepts_origin(value: Optional[str], allowed: frozenset[str] = frozenset()) -> bool:
    """Mirror of the reference server's ``acceptsOrigin``.

    A missing or ``"null"`` origin is refused, as is anything that is not a bare
    http(s) origin. Otherwise an explicitly allowed origin or any loopback host
    is accepted - the gateway is loopback-only, so the browser and the gateway
    share a host.
    """
    if value is None or value == "null":
        return False
    try:
        origin = urlparse(value)
    except ValueError:
        return False
    if origin.scheme not in ("http", "https"):
        return False
    if origin.path not in ("", "/") or origin.query or origin.fragment \
            or not origin.hostname:
        return False
    if _normalize_origin(value) in allowed:
        return True
    return _is_loopback_host(origin.hostname)


def validate_indices(raw: Any, count: int, *, maximum: Optional[int] = None,
                     require_non_empty: bool = False) -> list[int]:
    """Path indices the client sent, checked against the discovered path count.

    A probe that cannot fail is not evidence: every bound here has a matching
    unit test that drives it past the bound.
    """
    if not isinstance(raw, list):
        raise ValueError("indices must be an array of integers")
    if require_non_empty and not raw:
        raise ValueError("indices must not be empty")
    if maximum is not None and len(raw) > maximum:
        raise ValueError(
            f"a targeted read may name at most {maximum} paths, got {len(raw)}")
    out: list[int] = []
    for item in raw:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError("each index must be an integer")
        if item < 0 or item >= count:
            raise ValueError(f"index {item} is outside 0..{count - 1}")
        out.append(item)
    return out


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Station:
    """The controller's projected state, read on demand and briefly cached.

    ``read_fn`` returns the flat projection document (a blocking call); it is run
    off the event loop and serialized by a lock, because a single pylogix
    connection is not reentrant. The path list and its revision are derived from
    the document: the revision bumps only when the set of published paths
    changes, so a static station holds one stable revision the way the client
    requires.
    """

    def __init__(self, read_fn: Callable[[], dict[str, Any]], *,
                 cache_ttl: float = CACHE_TTL_S,
                 clock: Callable[[], float] = time.monotonic):
        self._read_fn = read_fn
        self._cache_ttl = cache_ttl
        self._clock = clock
        self._lock = asyncio.Lock()
        self._doc: Optional[dict[str, Any]] = None
        self._doc_ts = 0.0
        self._paths: list[str] = []
        self._revision = 0
        self._healthy = False
        self.last_success: Optional[str] = None
        self.last_failure: Optional[str] = None

    @property
    def paths(self) -> list[str]:
        return self._paths

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def healthy(self) -> bool:
        return self._healthy

    async def document(self, *, force: bool = False) -> dict[str, Any]:
        async with self._lock:
            now = self._clock()
            if not force and self._doc is not None \
                    and (now - self._doc_ts) <= self._cache_ttl:
                return self._doc
            try:
                doc = await asyncio.to_thread(self._read_fn)
            except Exception:
                self._healthy = False
                self.last_failure = _utcnow_iso()
                raise
            self._doc = doc
            self._doc_ts = self._clock()
            self._healthy = True
            self.last_success = _utcnow_iso()
            self._apply(doc)
            return doc

    def _apply(self, doc: dict[str, Any]) -> None:
        paths = sorted(doc.get("values", {}).keys())
        if paths != self._paths:
            self._paths = paths
            self._revision = (self._revision + 1) & 0x7FFFFFFF
            if self._revision == 0:
                self._revision = 1


class _ConnState:
    __slots__ = ("configured",)

    def __init__(self) -> None:
        # Once the client has installed a read-tier profile it no longer needs
        # the path list echoed on every snapshot, so we stop resending it - the
        # same optimization the reference server makes.
        self.configured = False


def _ok(rid: int, result: Any) -> str:
    return json.dumps({"id": rid, "ok": True, "result": result})


def _error(rid: Optional[int], message: str) -> str:
    return json.dumps({"id": rid, "ok": False, "error": message})


class Gateway:
    def __init__(self, station: Station, *,
                 allowed_origins: frozenset[str] = frozenset()):
        self.station = station
        self.allowed_origins = allowed_origins
        self._closing = False

    # --- HTTP: health routes and the upgrade gate -------------------------

    async def process_request(self, connection: Any, request: Any):
        path = request.path.split("?", 1)[0]
        if path in ("/healthz", "/livez", "/readyz"):
            return self._health(connection, path)
        if path != WS_PATH:
            return connection.respond(http.HTTPStatus.NOT_FOUND, "not found\n")
        origin = request.headers.get("Origin")
        if not accepts_origin(origin, self.allowed_origins):
            log.warning("stage=upgrade-refused reason=origin origin=%r", origin)
            return connection.respond(
                http.HTTPStatus.FORBIDDEN, "WebSocket origin is not allowed.\n")
        return None

    def _health(self, connection: Any, path: str):
        is_live = path == "/livez"
        is_ready = path == "/readyz"
        ready = (not self._closing) and self.station.healthy
        status = ("stopping" if self._closing
                  else "live" if is_live
                  else "ready" if ready
                  else "degraded")
        body: dict[str, Any] = {
            "protocol": PROTOCOL,
            "status": status,
            "plcReady": self.station.healthy,
        }
        if self.station.last_success is not None:
            body["lastControllerRead"] = self.station.last_success
        if self.station.last_failure is not None:
            body["lastControllerFailure"] = self.station.last_failure
        code = (http.HTTPStatus.SERVICE_UNAVAILABLE
                if (is_ready and not ready) else http.HTTPStatus.OK)
        return connection.respond(code, json.dumps(body) + "\n")

    # --- WebSocket: the protocol ------------------------------------------

    async def handler(self, connection: Any) -> None:
        state = _ConnState()
        peer = getattr(connection, "remote_address", None)
        log.info("stage=connected peer=%s", peer)
        try:
            async for message in connection:
                await self.dispatch(connection.send, state, message)
        except Exception as exc:  # a closed socket is a normal end
            log.info("stage=disconnected peer=%s detail=%s", peer, exc)

    async def dispatch(self, send: Callable[[str], Any], state: _ConnState,
                       message: Any) -> None:
        try:
            decoded = json.loads(message)
        except (ValueError, TypeError):
            await send(_error(None, "Request is not valid JSON."))
            return
        if not isinstance(decoded, dict):
            await send(_error(None, "Request must be a JSON object."))
            return
        rid = decoded.get("id")
        if not isinstance(rid, int) or isinstance(rid, bool) \
                or rid < 0 or rid > 0x7FFFFFFF:
            await send(_error(None, "Request id must be a non-negative integer."))
            return
        if decoded.get("protocol") != PROTOCOL:
            await send(_error(rid, "Unsupported gateway protocol."))
            return
        params = decoded.get("params")
        if not isinstance(params, dict):
            await send(_error(rid, "Request params must be an object."))
            return
        method = decoded.get("method")
        try:
            if method == "snapshot":
                await send(_ok(rid, await self._snapshot(state)))
            elif method == "discoverPaths":
                await send(_ok(rid, await self._discover_paths()))
            elif method == "readValues":
                await send(_ok(rid, await self._read_values(params)))
            elif method == "setReadTiers":
                await send(_ok(rid, await self._set_read_tiers(state, params)))
            elif method in ("write", "writeBatch"):
                await send(_error(rid, WRITE_REFUSED))
            else:
                await send(_error(rid, "Unsupported gateway method."))
        except StaleRevision as exc:
            await send(_error(rid, str(exc)))
        except ValueError as exc:
            await send(_error(rid, str(exc)))
        except Exception as exc:
            log.warning("stage=method-failed method=%s detail=%s", method, exc)
            await send(_error(rid, f"controller read failed: {exc}"))

    async def _snapshot(self, state: _ConnState) -> dict[str, Any]:
        doc = await self.station.document()
        paths = self.station.paths
        result = dict(doc)
        result["discoveryRevision"] = self.station.revision
        result["nodeCount"] = len(paths)
        result["truncated"] = bool(doc.get("truncated", False))
        result["paths"] = [] if state.configured else list(paths)
        result["values"] = doc.get("values", {})
        result["dataValues"] = doc.get("dataValues", {})
        return result

    async def _discover_paths(self) -> dict[str, Any]:
        await self.station.document()
        paths = self.station.paths
        return {
            "revision": self.station.revision,
            "nodeCount": len(paths),
            "paths": list(paths),
        }

    async def _read_values(self, params: dict[str, Any]) -> dict[str, Any]:
        doc = await self.station.document()
        if params.get("revision") != self.station.revision:
            raise StaleRevision(
                "Discovery revision is stale; discover paths again.")
        paths = self.station.paths
        indices = validate_indices(
            params.get("indices"), len(paths),
            maximum=MAX_TARGET_READ_PATHS, require_non_empty=True)
        values = doc.get("values", {})
        return {paths[i]: values.get(paths[i]) for i in indices}

    async def _set_read_tiers(self, state: _ConnState,
                              params: dict[str, Any]) -> bool:
        await self.station.document()
        if params.get("revision") != self.station.revision:
            raise StaleRevision(
                "Discovery revision is stale; discover paths again.")
        count = len(self.station.paths)
        slow = validate_indices(params.get("slow", []), count)
        excluded = validate_indices(params.get("excluded", []), count)
        if set(slow) & set(excluded):
            raise ValueError("A browse path cannot be both slow and excluded.")
        # The AB projection reads the whole station in one poll, so read tiers
        # are nothing to optimize here; the profile is accepted and honoured only
        # by no longer echoing the (small, static) path list on each snapshot.
        state.configured = True
        return True


class SerialMismatch(Exception):
    """The controller answering is not the one this gateway is pinned to."""


def build_reader(target: str, slot: int, expected_serial: str) -> Callable[[], dict[str, Any]]:
    """A blocking read that reuses one pylogix connection and reconnects on drop.

    The identity is checked when the connection is opened, before any manifest is
    trusted; ``read_document`` then validates the manifest content hash on every
    read (fail-closed). A read on a stale reused socket reconnects and retries
    once transparently, so an idle period does not surface a spurious error to
    the HMI. A serial mismatch is a deterministic refusal and is never retried,
    and a freshly opened connection that still fails to read is a real fault, so
    it is not hammered.
    """
    import fraktal_ab_projection as projection
    from pylogix import PLC

    holder: dict[str, Any] = {"plc": None}

    def _open() -> Any:
        plc = PLC()
        plc.IPAddress = target
        plc.ProcessorSlot = slot
        try:
            serial, ok = projection.verify_serial(plc, expected_serial)
        except Exception:
            plc.Close()
            raise
        if not ok:
            plc.Close()
            raise SerialMismatch(
                f"serial {serial} is not the expected controller; refusing")
        log.info("stage=identity-verified serial=%s target=%s", serial, target)
        return plc

    def _drop() -> None:
        plc = holder["plc"]
        if plc is not None:
            try:
                plc.Close()
            except Exception:
                pass
            holder["plc"] = None

    def read() -> dict[str, Any]:
        last_exc: Optional[BaseException] = None
        for _ in range(2):
            opened_now = False
            try:
                plc = holder["plc"]
                if plc is None:
                    plc = _open()
                    holder["plc"] = plc
                    opened_now = True
                return projection.read_document(plc)
            except SerialMismatch:
                _drop()
                raise
            except Exception as exc:
                last_exc = exc
                _drop()
                if opened_now:
                    break  # a fresh connection that failed is a real fault
        assert last_exc is not None
        raise last_exc

    return read


async def serve_gateway(gateway: Gateway, host: str, port: int) -> None:
    from websockets.asyncio.server import serve

    async with serve(gateway.handler, host, port,
                     process_request=gateway.process_request):
        log.info("stage=listening endpoint=ws://%s:%d%s", host, port, WS_PATH)
        await asyncio.Future()  # run until cancelled


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="controller IPv4 address or path")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--slot", type=int, default=0)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--allow-origin", action="append", default=[],
                        help="an extra allowed browser origin (loopback is always allowed)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s")

    if not _is_loopback_host(args.host):
        parser.error(
            "the gateway is loopback-only; put an authenticated TLS reverse "
            "proxy in front of it for remote access")

    station = Station(build_reader(args.target, args.slot, args.expect_serial))
    gateway = Gateway(
        station,
        allowed_origins=frozenset(_normalize_origin(o) for o in args.allow_origin))
    try:
        asyncio.run(serve_gateway(gateway, args.host, args.port))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

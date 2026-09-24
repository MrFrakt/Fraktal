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
import hmac
import http
import ipaddress
import json
import logging
import math
import os
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

# Where the Core §14 write token is read from. An environment variable rather
# than argv: a process listing is readable by any user on the host, and §14.2/
# §14.3 keeps credentials out of literals. The HMI client is symmetric, taking
# its bearer from FRAKTAL_GATEWAY_BEARER_TOKEN.
WRITE_TOKEN_ENV = "FRAKTAL_GATEWAY_WRITE_TOKEN"

# Write refusals. Read-only stays the default: writes are enabled only when a
# write token is configured, and even then never anonymously (Core §14).
READ_ONLY_REFUSED = (
    "read-only Allen-Bradley gateway (AB §11.2.1): no write root is configured; "
    "operator commands are refused before the controller sees them"
)
ANON_WRITE_REFUSED = (
    "write requires authentication; anonymous or unauthenticated write is "
    "prohibited (Core §14)"
)
# The controller exposes no HmiRequest mailbox yet (manifest MailboxId 0), so a
# permitted, authenticated write still has nothing on the controller to target.
# The token proves the Core §14 gate; connecting the write to the controller is
# the owed AB command binding.
WRITE_NOT_CONNECTED = (
    "the write path is not connected to this controller yet: the AB command "
    "binding (an HmiRequest mailbox) is owed work"
)
WRITE_SCOPE_REFUSED = "write path is outside the allowed HmiRequest scope"

WRITE_TYPES = ("boolean", "int32", "uint32", "int64", "doubleValue", "string")
_MAX_BATCH_WRITES = 32
_MAX_STRING_VALUE = 4096
_MAX_WRITE_PATH = 2048

log = logging.getLogger("fraktal.ab.gateway")


class StaleRevision(Exception):
    """The client's discovery revision no longer matches; it must discover again."""


class WriteRefused(ValueError):
    """A write was refused by policy: read-only, unauthenticated, scope or sequence."""


# --- pure protocol bookkeeping, testable without a socket or a controller ---

# --- the controller write path -----------------------------------------------


class MailboxWriter:
    """Map an ``HmiRequest`` browse path to its controller tag and write it.

    This is the only thing in the binding that writes to a controller, and it
    writes to one place: the root Unit's command mailbox. Everything reaching it
    has already passed the Core 14 bearer gate and ``permits_write``.

    **Order is the contract.** ``validate_batch`` puts the ``Sequence`` commit
    last and this preserves that, aborting the moment any payload write fails.
    A commit written after a failed argument would run a command with a stale
    argument - a mode change carrying the previous request's value - which is
    exactly what a commit marker exists to prevent.

    Strings are written as ``LEN`` plus ``DATA`` rather than through the
    client's string handling, because these are user ``StringFamily`` types and
    not the built-in ``STRING``. Every kind this binding routes takes no string
    content, so the common path writes one length per string member.
    """

    def __init__(self, target, slot, expect_serial, app=None):
        self._target = target
        self._slot = slot
        self._expect_serial = expect_serial
        import fraktal_ab_projection as projection

        self._app = app if app is not None else projection.APP

    def tag_for(self, path):
        """``Press/HmiRequest/Kind`` maps to ``FRK_Press_HmiRequest.Kind``."""
        import fraktal_ab_mailbox as mailbox

        parts = path.split("/")
        if len(parts) < 3 or parts[-2] != "HmiRequest":
            raise WriteRefused("not an HmiRequest member: " + path)
        member = parts[-1]
        declared = set(name for name, _, _, _ in mailbox.REQUEST_MEMBERS)
        if member not in declared:
            raise WriteRefused(member + " is not a declared mailbox member")
        root = ".".join(parts[:-2])
        if root != self._app.name:
            raise WriteRefused(root + " is not this controller's root")
        return mailbox.request_tag_name(self._app) + "." + member

    def writes_for(self, tag, vtype, value):
        """The controller writes that one browse-path write becomes.

        Delegated to the contract module: what a member becomes on the wire is a
        property of the mailbox contract, not of this transport, and the
        evidence harnesses command the same mailbox over plain CIP. Two copies
        of the string LEN/DATA rule would be two places to get it wrong.
        """
        import fraktal_ab_mailbox as mailbox

        member = tag.rsplit(".", 1)[-1]
        try:
            return mailbox.member_writes(
                self._app, member,
                bool(value) if vtype == "boolean" else value)
        except ValueError as refusal:
            raise WriteRefused(str(refusal)) from refusal

    def __call__(self, writes, mailbox_path):
        from pylogix import PLC

        from fraktal_ab_s16_execute import _normalize_serial, _success, _value

        planned = [(self.tag_for(path), vtype, value)
                   for path, vtype, value in writes]

        with PLC() as comm:
            comm.IPAddress = self._target
            comm.ProcessorSlot = self._slot
            identity = comm.GetDeviceProperties()
            device = _value(identity)
            if device is None:
                log.error("stage=write-refused detail=identity read failed")
                return False
            serial = _normalize_serial(getattr(device, "SerialNumber", 0))
            if serial != self._expect_serial:
                # An exact target check immediately before the write, every
                # time. A command aimed at the wrong controller is not a failed
                # test, it is an incident.
                log.error("stage=write-refused detail=serial %s is not %s",
                          serial, self._expect_serial)
                return False

            for index, item in enumerate(planned):
                tag, vtype, value = item
                for target, payload in self.writes_for(tag, vtype, value):
                    reply = comm.Write(target, payload)
                    if not _success(reply):
                        log.error(
                            "stage=write-aborted detail=%s failed before the "
                            "commit (%s); no Sequence was written",
                            target, getattr(reply, "Status", "unknown"))
                        return False
                log.info("stage=write-ok detail=%s (%d of %d)",
                         tag, index + 1, len(planned))
        return True


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


def _write_value_ok(vtype: str, value: Any) -> bool:
    if vtype == "boolean":
        return isinstance(value, bool)
    if vtype in ("int32", "uint32", "int64"):
        if not isinstance(value, int) or isinstance(value, bool):
            return False
        if vtype == "int32":
            return -0x80000000 <= value <= 0x7FFFFFFF
        if vtype == "uint32":
            return 0 <= value <= 0xFFFFFFFF
        return True  # int64 accepts any JSON integer
    if vtype == "doubleValue":
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value))
    if vtype == "string":
        return isinstance(value, str) and len(value) <= _MAX_STRING_VALUE
    return False


def validate_write(params: dict[str, Any]) -> tuple[str, str, Any]:
    """One `{path, valueType, value}` write, checked the way the reference does."""
    path = params.get("path")
    vtype = params.get("valueType")
    value = params.get("value")
    if not isinstance(path, str) or not path or len(path) > _MAX_WRITE_PATH \
            or any(ord(ch) < 0x20 for ch in path):
        raise WriteRefused("write path is invalid")
    if vtype not in WRITE_TYPES:
        raise WriteRefused("write valueType is unsupported")
    if not _write_value_ok(vtype, value):
        raise WriteRefused("write value does not match valueType")
    return path, vtype, (float(value) if vtype == "doubleValue" else value)


def validate_batch(params: dict[str, Any]) -> tuple[list[tuple[str, str, Any]], str, int]:
    """A mailbox commit: payload writes then the uint32 `HmiRequest/Sequence`."""
    raw = params.get("writes")
    if not isinstance(raw, list) or not raw:
        raise WriteRefused("writeBatch requires a non-empty writes list")
    if len(raw) > _MAX_BATCH_WRITES:
        raise WriteRefused(f"writeBatch exceeds the {_MAX_BATCH_WRITES}-write limit")
    writes = []
    for item in raw:
        if not isinstance(item, dict):
            raise WriteRefused("each batch write must be an object")
        writes.append(validate_write(item))
    paths = [w[0] for w in writes]
    if len(set(paths)) != len(paths):
        raise WriteRefused("batch write paths must be unique")
    commit_path, commit_type, commit_value = writes[-1]
    if not commit_path.endswith("/HmiRequest/Sequence") or commit_type != "uint32":
        raise WriteRefused(
            "the final batch write must be the uint32 HmiRequest/Sequence commit")
    if any(p.endswith("/HmiRequest/Sequence") for p in paths[:-1]):
        raise WriteRefused("Sequence may appear only as the final write")
    mailbox = commit_path[: -len("/Sequence")]
    if any(not p.startswith(f"{mailbox}/") for p in paths):
        raise WriteRefused("all batch writes must use one HmiRequest mailbox")
    return writes, mailbox, commit_value


def permits_write(path: str, write_roots: frozenset[str] = frozenset(),
                  allow_all_root_mailboxes: bool = False) -> bool:
    """Mirror of the reference server's `permitsWrite`: HmiRequest mailboxes only."""
    parts = path.split("/")
    try:
        mailbox = len(parts) - 1 - parts[::-1].index("HmiRequest")
    except ValueError:
        return False
    if mailbox <= 0 or mailbox >= len(parts) - 1:
        return False
    if any(part in ("", ".", "..") for part in parts):
        return False
    if not write_roots:
        return allow_all_root_mailboxes
    return "/".join(parts[:mailbox]) in write_roots


def resolve_write_token(environ: Any, argv_token: str) -> str:
    """Where the Core §14 write token comes from, environment first.

    §14.2/§14.3 keeps a credential out of literals, and argv is world-readable
    in a process listing, so the environment wins over the flag rather than the
    other way round: a host that configures the secret properly cannot have it
    silently overridden by something left on a command line.
    """
    return environ.get(WRITE_TOKEN_ENV, "") or argv_token


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
    __slots__ = ("configured", "authenticated")

    def __init__(self) -> None:
        # Once the client has installed a read-tier profile it no longer needs
        # the path list echoed on every snapshot, so we stop resending it - the
        # same optimization the reference server makes.
        self.configured = False
        # Set once at connect from the WebSocket's Authorization header; a write
        # is refused unless this is true (Core §14: no anonymous write).
        self.authenticated = False


def _ok(rid: int, result: Any) -> str:
    return json.dumps({"id": rid, "ok": True, "result": result})


def _error(rid: Optional[int], message: str) -> str:
    return json.dumps({"id": rid, "ok": False, "error": message})


class Gateway:
    def __init__(self, station: Station, *,
                 allowed_origins: frozenset[str] = frozenset(),
                 write_token: str = "",
                 write_roots: frozenset[str] = frozenset(),
                 allow_all_root_mailboxes: bool = False,
                 write_fn: Optional[Callable[[list[tuple[str, str, Any]],
                                              Optional[str]], bool]] = None):
        self.station = station
        self.allowed_origins = allowed_origins
        # Writes are off unless a token is configured (read-only default), never
        # anonymous (Core §14), confined to HmiRequest mailboxes (permits_write),
        # and only actually reach the controller when write_fn is wired.
        self._write_token = write_token
        self._write_roots = write_roots
        self._allow_all_root_mailboxes = allow_all_root_mailboxes
        self._write_fn = write_fn
        self._mailbox_sequences: dict[str, int] = {}
        self._closing = False

    def _authenticate(self, connection: Any) -> bool:
        if not self._write_token:
            return False
        try:
            header = connection.request.headers.get("Authorization") or ""
        except Exception:
            header = ""
        return hmac.compare_digest(header, f"Bearer {self._write_token}")

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
        state.authenticated = self._authenticate(connection)
        peer = getattr(connection, "remote_address", None)
        log.info("stage=connected peer=%s authenticated=%s", peer,
                 state.authenticated)
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
            elif method == "write":
                await send(_ok(rid, await self._write(state, params)))
            elif method == "writeBatch":
                await send(_ok(rid, await self._write_batch(state, params)))
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

    def _guard_write(self, state: _ConnState) -> None:
        if not self._write_token:
            raise WriteRefused(READ_ONLY_REFUSED)
        if not state.authenticated:
            raise WriteRefused(ANON_WRITE_REFUSED)

    def seed_sequences(self, doc: dict[str, Any]) -> None:
        """Adopt the sequence the controller has already answered.

        The reference server seeds the same way, and without it the first batch
        after a gateway restart carries no expectation at all: any sequence
        would be accepted, including one the controller has already consumed.
        A client that replayed a stale commit would then re-run a command the
        operator issued once. Seeding makes the guard mean something from the
        first write rather than only from the second.

        ``setdefault``, not assignment: once this gateway has committed a
        sequence its own record is authoritative, and re-reading a controller
        that has not yet scanned the write must not walk it backwards.
        """
        for path, value in doc.get("values", {}).items():
            if (path.endswith("/HmiRequest/Sequence")
                    and isinstance(value, int) and not isinstance(value, bool)):
                self._mailbox_sequences.setdefault(
                    path[: -len("/Sequence")], value)

    async def _write(self, state: _ConnState, params: dict[str, Any]) -> bool:
        self._guard_write(state)
        path, vtype, value = validate_write(params)
        if not permits_write(path, self._write_roots,
                             self._allow_all_root_mailboxes):
            raise WriteRefused(WRITE_SCOPE_REFUSED)
        if path.endswith("/HmiRequest/Sequence"):
            raise WriteRefused("Sequence is a commit field and requires writeBatch")
        if self._write_fn is None:
            raise WriteRefused(WRITE_NOT_CONNECTED)
        return bool(await asyncio.to_thread(self._write_fn, [(path, vtype, value)],
                                            None))

    async def _write_batch(self, state: _ConnState,
                           params: dict[str, Any]) -> bool:
        self._guard_write(state)
        writes, mailbox, sequence = validate_batch(params)
        for path, _vtype, _value in writes:
            if not permits_write(path, self._write_roots,
                                 self._allow_all_root_mailboxes):
                raise WriteRefused(WRITE_SCOPE_REFUSED)
        # Seed from the controller before judging the sequence, so the very
        # first commit is checked against what the machine has actually
        # answered rather than against nothing.
        self.seed_sequences(await self.station.document())
        previous = self._mailbox_sequences.get(mailbox)
        if previous is not None and sequence != ((previous + 1) & 0xFFFFFFFF):
            raise WriteRefused(
                f"stale mailbox sequence: expected "
                f"{(previous + 1) & 0xFFFFFFFF}, got {sequence}")
        if self._write_fn is None:
            raise WriteRefused(WRITE_NOT_CONNECTED)
        accepted = bool(await asyncio.to_thread(self._write_fn, writes, mailbox))
        if accepted:
            self._mailbox_sequences[mailbox] = sequence
        return accepted


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


def tls_context(certfile: str, keyfile: str) -> Any:
    """The server TLS context, when the gateway is asked to serve ``wss``.

    A credential may not cross a plaintext hop. The HMI enforces exactly that
    and refuses to attach a bearer token to a ``ws://`` endpoint
    (``IoGatewaySecurityOptions.validate``), so a gateway that accepts an
    authenticated write has to offer TLS - on loopback too, because the rule is
    about the credential, not about the distance.
    """
    import ssl

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile, keyfile)
    return context


async def serve_gateway(gateway: Gateway, host: str, port: int,
                        ssl_context: Any = None) -> None:
    from websockets.asyncio.server import serve

    async with serve(gateway.handler, host, port,
                     process_request=gateway.process_request,
                     ssl=ssl_context):
        log.info("stage=listening endpoint=%s://%s:%d%s",
                 "wss" if ssl_context else "ws", host, port, WS_PATH)
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
    parser.add_argument("--write-token", default="",
                        help="enable the Core §14 write gate: a client must present "
                             "this as an Authorization: Bearer token. Anonymous "
                             "writes are always refused. Read-only when unset. "
                             "Prefer " + WRITE_TOKEN_ENV + " in the environment: "
                             "argv is world-readable in a process listing, and "
                             "Core §14.2/§14.3 keeps a secret out of literals.")
    parser.add_argument("--write-root", action="append", default=[],
                        help="a root whose HmiRequest mailbox may be written; "
                             "repeatable. With --write-token and none given, all "
                             "root mailboxes are permitted.")
    parser.add_argument("--tls-cert", default="",
                        help="serve wss:// with this PEM certificate. A client "
                             "will not send a bearer token over plaintext, so "
                             "an authenticated write needs this.")
    parser.add_argument("--tls-key", default="",
                        help="the private key for --tls-cert")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s")

    # Core §14.2/§14.3: a credential is a configuration or secret-store value,
    # never a literal. The environment is the supported way in - it keeps the
    # token out of argv, which any user on the host can read from a process
    # listing - and it is symmetric with the HMI client, which takes its bearer
    # from FRAKTAL_GATEWAY_BEARER_TOKEN.
    write_token = resolve_write_token(os.environ, args.write_token)

    if not _is_loopback_host(args.host):
        parser.error(
            "the gateway is loopback-only; put an authenticated TLS reverse "
            "proxy in front of it for remote access")

    if bool(args.tls_cert) != bool(args.tls_key):
        parser.error("--tls-cert and --tls-key are configured together")
    ssl_context = (tls_context(args.tls_cert, args.tls_key)
                   if args.tls_cert else None)

    # The root now publishes a command mailbox, so a write can reach it - and
    # reaches nothing else: the writer maps only HmiRequest members to tags, and
    # every request has already passed the Core §14 bearer gate and
    # permits_write. Without a token there is no writer at all and the gateway
    # is read-only, which stays the default.
    if write_token:
        log.warning("stage=write-gate-enabled source=%s detail=Core §14 write "
                    "gate is on (authenticated writes only); writes reach the "
                    "root command mailbox and nothing else",
                    WRITE_TOKEN_ENV if os.environ.get(WRITE_TOKEN_ENV) else "argv")

    station = Station(build_reader(args.target, args.slot, args.expect_serial))
    gateway = Gateway(
        station,
        allowed_origins=frozenset(_normalize_origin(o) for o in args.allow_origin),
        write_token=write_token,
        write_roots=frozenset(args.write_root),
        allow_all_root_mailboxes=bool(write_token) and not args.write_root,
        write_fn=(MailboxWriter(args.target, args.slot, args.expect_serial)
                  if write_token else None))
    if write_token and ssl_context is None:
        # Not fatal - the gate still refuses anonymous writes - but a client
        # that honours the credential rule cannot authenticate here, so say so
        # rather than let it look like the gate rejected a well-formed command.
        log.warning("stage=write-gate-plaintext detail=the write gate is on but "
                    "this endpoint is ws://; a client that refuses to send a "
                    "bearer over plaintext cannot authenticate. Use --tls-cert.")

    try:
        asyncio.run(serve_gateway(gateway, args.host, args.port, ssl_context))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

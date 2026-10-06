#!/usr/bin/env python3
"""Serve the Allen-Bradley projection to the Fraktal HMI over its own protocol.

The generic Fraktal HMI speaks one WebSocket protocol, ``fraktal.opcua.gateway.v1``
(see ``FraktalCore/HMI/lib/data/opcua_gateway_client_io.dart`` and the reference
Dart server in ``FraktalCore/HMI/gateway``). It asks for a flat
``{browsePath: value}`` snapshot, discovers the stable path list, and then reads
values by index. ``fraktal_ab_projection`` already turns a live Logix controller
into exactly that flat document. This is the transport in between: it wraps the
projection in the protocol, so no AB-specific screen or repository is needed.

**It ships read-only and fails closed on mutations.** Per AB §11.2.1 the binding
is configured with no write root. A complete, inert QUERY_CONFIG batch may use
the root mailbox to fetch a page; every mutation still requires the bearer and
write scope. A query changes only the response page and acknowledgement.
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
# Bound multiplexed requests per viewer. Native reads retain Station's lock;
# every command retains the one shared mailbox transaction lock.
MAX_PENDING_REQUESTS = 16
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

    def __init__(self, target, slot, expect_serial, app=None, set_store=None):
        self._target = target
        self._slot = slot
        self._expect_serial = expect_serial
        import fraktal_ab_projection as projection

        self._app = app if app is not None else projection.APP
        self._set_store = set_store
        if self._app.config_sets and set_store is None:
            from pathlib import Path
            from fraktal_ab_sets import FileStore
            directory = os.environ.get('FRAKTAL_AB_CONFIG_SET_DIR')
            if not directory:
                directory = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Fraktal' / 'ConfigSets' / (expect_serial + '-' + self._app.name)
            self._set_store = FileStore(directory)

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

    def _write_base(self, comm, writes):
        from fraktal_ab_s16_execute import _success
        from fraktal_ab_access import prepare_login
        import fraktal_ab_mailbox as mailbox
        import fraktal_ab_mailbox_frame as frame
        if len(writes) == 1 and writes[0] == (self._app.name + '/HmiRequest/Kind', 'int32', mailbox.NONE):
            # The repository's post-ack cleanup is inert: only a new Sequence
            # consumes a request. Decoded native arguments are private in V3.
            return True
        # Move the expensive KDF prefix off the cyclic task. Authentication and
        # the registered user's level remain exclusively controller decisions.
        try:
            writes = prepare_login(self._app, writes)
        except ValueError as refusal:
            raise WriteRefused(str(refusal)) from refusal
        # Plan every translation before issuing even the first payload write.
        values = {self.tag_for(path).rsplit('.', 1)[-1]: value for path, _type, value in writes}
        if 'Kind' not in values or 'Sequence' not in values:
            raise WriteRefused('native mailbox requires a complete writeBatch')
        try:
            planned = mailbox.command_writes(self._app, values.pop('Kind'), values.pop('Sequence'), **values)
        except ValueError as refusal:
            raise WriteRefused(str(refusal)) from refusal
        comm.ConnectionSize = frame.CONNECTION_SIZE
        for target, payload in planned:
            reply = comm.Write(target, payload)
            if not _success(reply):
                log.error('stage=write-aborted detail=%s (%s)', target, getattr(reply, 'Status', 'unknown'))
                return False
        # Keep the one-writer transaction until the PLC has consumed and wiped
        # this frame. Another client must not overwrite arguments mid-dispatch.
        from fraktal_ab_press_execute import read_scalar
        expected = planned[-1][1] & 0xffffffff
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            ack = read_scalar(comm, mailbox.response_tag_name(self._app) + '.AckSequence')
            if ack is not None and (ack & 0xffffffff) == expected:
                return True
            time.sleep(.01)
        raise TimeoutError('native mailbox acknowledgement timed out; outcome is unknown')

    def __call__(self, writes, mailbox_path):
        return self._command(writes, mailbox_path)

    def set_command(self, writes, mailbox_path, session):
        return self._command(writes, mailbox_path, session)

    def _verify_login_profile(self, comm, writes):
        import fraktal_ab_access as access
        import fraktal_ab_mailbox as mailbox
        from fraktal_ab_press_execute import read_layout
        if self._app.access_users is None or not any(
                p.endswith('/Kind') and v == mailbox.LOGIN for p, _, v in writes):
            return
        # Read the dimension-aware contract, never a member-offset guess.
        # An old/wrong provider must be refused before any credential write.
        state = read_layout(comm, access.tag(self._app, 'State'), access.state_members(self._app))
        if (state is None or state['SchemaVersion'] != access.STATE_SCHEMA
                or state['LoginPrehashRounds'] != access.PIN_HASH_ROUNDS):
            raise WriteRefused('Controller login derivation profile does not match the gateway')

    def _command(self, writes, mailbox_path, session=None):
        from pylogix import PLC

        from fraktal_ab_s16_execute import _normalize_serial, _success, _value

        # Reject private/nested transaction fields supplied by a Web client.
        for path, vtype, value in writes:
            self.writes_for(self.tag_for(path), vtype, value)

        import fraktal_ab_mailbox as mailbox
        if writes == [(self._app.name + '/HmiRequest/Kind', 'int32', mailbox.NONE)]:
            # V3 cleanup is a validated no-op. No controller I/O is needed;
            # authentication and mailbox scope were checked by the gateway.
            return True

        with PLC() as comm:
            comm.IPAddress = self._target
            comm.ProcessorSlot = self._slot
            from fraktal_ab_mailbox_frame import CONNECTION_SIZE
            comm.ConnectionSize = CONNECTION_SIZE
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

            self._verify_login_profile(comm, writes)

            if session is not None and self._app.config_sets:
                from fraktal_ab_set_broker import process
                return process(_GuardedConnection(comm, self._expect_serial), self._app, self._set_store, session, writes, self._write_base)
            return self._write_base(_GuardedConnection(comm, self._expect_serial), writes)


class _GuardedConnection:
    """Exact identity immediately before every primitive native write."""

    def __init__(self, comm, serial):
        self._comm, self._serial = comm, serial

    def __getattr__(self, name):
        return getattr(self._comm, name)

    @property
    def ConnectionSize(self):
        return self._comm.ConnectionSize

    @ConnectionSize.setter
    def ConnectionSize(self, value):
        self._comm.ConnectionSize = value

    def Write(self, target, value):
        from fraktal_ab_s16_execute import _normalize_serial, _value
        device = _value(self._comm.GetDeviceProperties())
        if device is None or _normalize_serial(getattr(device, 'SerialNumber', 0)) != self._serial:
            raise WriteRefused('exact controller identity check failed before native write')
        return self._comm.Write(target, value)


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


async def _run_native_worker(call, *args):
    """Cancellation must not release a native lock while its thread still runs."""
    task = asyncio.create_task(asyncio.to_thread(call, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        except Exception:
            pass
        raise


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
                 clock: Callable[[], float] = time.monotonic, budget=None):
        self._read_fn = read_fn
        self.budget = budget if budget is not None else getattr(read_fn, 'budget', None)
        if self.budget is not None and self.budget.validate():
            raise ValueError('; '.join(self.budget.validate()))
        self._cache_ttl = self.budget.cache_ms / 1000 if self.budget else cache_ttl
        self._clock = clock
        self._lock = asyncio.Lock()
        self._doc: Optional[dict[str, Any]] = None
        self._doc_ts = 0.0
        self._sample_ts = 0.0
        self._paths: list[str] = []
        self._revision = 0
        self._healthy = False
        self.last_success: Optional[str] = None
        self.last_failure: Optional[str] = None
        # Why the controller's station was refused, when it was: said in
        # /healthz so "commands do nothing" has a stated cause.
        self.last_refusal: Optional[str] = None

    @property
    def paths(self) -> list[str]:
        return self._paths

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def healthy(self) -> bool:
        return self._healthy and (self.budget is None or
            (self._clock() - self._sample_ts) * 1000 < self.budget.fast_good_ms)

    def _aged(self, doc):
        if self.budget is None:
            return doc
        result = dict(doc)
        aged_at = self._clock()
        elapsed = max(0, (aged_at - self._doc_ts) * 1000)
        result['freshnessBudget'] = self.budget.wire()
        result['sampleAgeMs'] = max(0, (aged_at - self._sample_ts) * 1000)
        # Internal clock boundary for the snapshot RPC's processing allowance.
        # Never exposed as a timestamp or used to advance source freshness.
        result['_agedAt'] = aged_at
        metadata = {}
        for path, source in doc.get('dataValues', {}).items():
            value = dict(source)
            age = value.get('ageMs', 0) + elapsed
            slow = value.get('tier') == 'slow'
            good = self.budget.slow_good_ms if slow else self.budget.fast_good_ms
            expiry = self.budget.slow_expiry_ms if slow else self.budget.fast_expiry_ms
            severity = 0x80000000 if age >= expiry else 0x40000000 if age >= good else 0
            if severity > (value.get('status', 0x80000000) & 0xc0000000):
                value['status'] = severity
                value['qualityReason'] = 'read-expired' if age >= expiry else 'read-late'
            value['ageMs'] = age
            metadata[path] = value
        result['dataValues'] = metadata
        result['values'] = {p: v for p, v in doc.get('values', {}).items()
                            if (metadata.get(p, {}).get('status', 0x80000000) & 0xc0000000) == 0}
        return result

    def _accept(self, doc, started, acquired):
        # Ages start before I/O: a delayed acquisition cannot become fresh just
        # because it finally completed. UTC is receipt time, never source time.
        doc = dict(doc)
        ended = self._clock()
        metadata = dict(doc.get('dataValues', {}))
        for path, value in doc.get('values', {}).items():
            metadata[path] = {'value': value, 'status': 0,
                'serverTimestampUs': acquired, 'ageMs': max(0, (ended - started) * 1000), 'tier': 'fast',
                'type': ('Boolean' if isinstance(value, bool) else 'Integer' if isinstance(value, int)
                         else 'Double' if isinstance(value, float) else 'String' if isinstance(value, str) else 'Unknown'),
                **metadata.get(path, {})}
        doc['dataValues'] = metadata
        self._doc, self._doc_ts, self._sample_ts = doc, ended, started
        self._healthy = True
        self.last_success, self.last_refusal = _utcnow_iso(), None
        self._apply(doc)
        return self._aged(doc)

    async def document(self, *, force: bool = False) -> dict[str, Any]:
        async with self._lock:
            now = self._clock()
            if not force and self._doc is not None \
                    and (now - self._doc_ts) <= self._cache_ttl:
                return self._aged(self._doc)
            acquired = str(time.time_ns() // 1000)
            try:
                doc = await _run_native_worker(self._read_fn)
            except Exception as exc:
                self._doc = None  # a forced read failure cannot revive cached Good data
                self._healthy = False
                self.last_failure = _utcnow_iso()
                self.last_refusal = (str(exc) if type(exc).__name__ in (
                    "ProjectionRefused", "BuildMismatch") else None)
                raise
            return self._accept(doc, now, acquired)

    async def set_tiers(self, slow, excluded):
        async with self._lock:
            callback = getattr(self._read_fn, 'set_tiers', None)
            if callback is not None:
                callback(slow, excluded, self.paths)

    async def targeted(self, paths, *, reuse_good=False):
        async with self._lock:
            if reuse_good and self.budget is not None and self._doc is not None \
                    and self.healthy:
                doc = self._aged(self._doc)
                metadata = doc.get('dataValues', {})
                if all(p in doc.get('values', {}) and p in metadata and
                       (metadata[p].get('status', 0x80000000) & 0xc0000000) == 0 and
                       metadata[p].get('ageMs', float('inf')) <= self.budget.slow_period_ms
                       for p in paths):
                    # Source age is returned to the viewer. Reusing this record
                    # never advances the complete-sample timestamp or its health.
                    return doc
            callback = getattr(self._read_fn, 'targeted', None)
            if callback is not None:
                callback(paths)
                self._doc = None
        return await self.document()

    async def mailbox_document(self):
        """A fresh control read, serialized with the native snapshot reader."""
        callback = getattr(self._read_fn, 'mailbox', None)
        if callback is None:
            return await self.document()
        async with self._lock:
            started, acquired = self._clock(), str(time.time_ns() // 1000)
            try:
                doc = await _run_native_worker(callback)
            except Exception as exc:
                self._doc = None
                self._healthy = False
                self.last_failure = _utcnow_iso()
                self.last_refusal = (str(exc) if type(exc).__name__ in (
                    'ProjectionRefused', 'BuildMismatch') else None)
                raise
            # A cold/reconnected reader first validates a complete station.
            # A partial mailbox document never alters discovery or the cache.
            if 'schema' in doc:
                return self._accept(doc, started, acquired)
            # Control replies have their own acquisition age. They do not
            # advance complete-station health or replace its cached document.
            elapsed = max(0, (self._clock() - started) * 1000)
            severity = 0
            if self.budget is not None:
                severity = (0x80000000 if elapsed >= self.budget.fast_expiry_ms
                            else 0x40000000 if elapsed >= self.budget.fast_good_ms else 0)
            doc = dict(doc, dataValues={p: dict(value=v,
                status=0x80320000 if v is None else severity, ageMs=elapsed,
                serverTimestampUs=acquired, tier='fast')
                for p, v in doc.get('values', {}).items()})
            return doc

    def _apply(self, doc: dict[str, Any]) -> None:
        paths = sorted(doc.get("values", {}).keys())
        if paths != self._paths:
            self._paths = paths
            self._revision = (self._revision + 1) & 0x7FFFFFFF
            if self._revision == 0:
                self._revision = 1


class _ConnState:
    __slots__ = ("configured", "authenticated", "config_model", "sets", "excluded", "slow")

    def __init__(self) -> None:
        # Once the client has installed a read-tier profile it no longer needs
        # the path list echoed on every snapshot, so we stop resending it - the
        # same optimization the reference server makes.
        self.configured = False
        # Set once at connect from the WebSocket's Authorization header; a write
        # is refused unless this is true (Core §14: no anonymous write).
        self.authenticated = False
        # Core §3.8a: the model this connection's last QUERY_CONFIG asked
        # about, 0 = the running record. Per connection because a mailbox
        # answer belongs to whoever asked - two operators editing two models
        # must not see each other's page.
        self.config_model = 0
        from fraktal_ab_sets import Session
        self.sets = Session()
        self.excluded = frozenset()
        self.slow = frozenset()


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
        # Mutations are off unless a token is configured (read-only default), never
        # anonymous (Core §14), confined to HmiRequest mailboxes (permits_write),
        # and only actually reach the controller when write_fn is wired.
        self._write_token = write_token
        # One station mailbox is shared by all viewers and operators. Keep
        # argument staging, Sequence and bookkeeping in one transaction.
        self._mailbox_lock = asyncio.Lock()
        self._write_roots = write_roots
        self._allow_all_root_mailboxes = allow_all_root_mailboxes
        self._write_fn = write_fn
        self._mailbox_sequences: dict[str, int] = {}
        self._states = set()
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
            # Configured mutation policy, independent of controller readiness.
            # The inert QUERY_CONFIG exception does not enable commands.
            "writeAccess": {
                "enabled": (bool(self._write_token)
                            and self._write_fn is not None
                            and (bool(self._write_roots)
                                 or self._allow_all_root_mailboxes)),
                "roots": sorted(self._write_roots),
                "allRootMailboxes": (not self._write_roots
                                     and self._allow_all_root_mailboxes),
            },
        }
        if self.station.last_success is not None:
            body["lastControllerRead"] = self.station.last_success
        if self.station.last_failure is not None:
            body["lastControllerFailure"] = self.station.last_failure
        if self.station.last_refusal is not None:
            body["controllerRefusal"] = self.station.last_refusal
        code = (http.HTTPStatus.SERVICE_UNAVAILABLE
                if (is_ready and not ready) else http.HTTPStatus.OK)
        return connection.respond(code, json.dumps(body) + "\n")

    # --- WebSocket: the protocol ------------------------------------------

    async def handler(self, connection: Any) -> None:
        state = _ConnState()
        self._states.add(state)
        state.authenticated = self._authenticate(connection)
        peer = getattr(connection, "remote_address", None)
        log.info("stage=connected peer=%s authenticated=%s", peer,
                 state.authenticated)
        pending: set[asyncio.Task] = set()
        requests_cancelled = False

        def cancel_pending():
            nonlocal requests_cancelled
            # No requests are added after shutdown starts. Cancel only once:
            # a second cancellation could interrupt a native thread's drain.
            if not requests_cancelled:
                requests_cancelled = True
                for task in pending:
                    task.cancel()

        def completed(task):
            pending.discard(task)
            if not task.cancelled():
                error = task.exception()
                if error is not None:
                    log.info('stage=request-ended peer=%s error=%s',
                             peer, type(error).__name__)

        try:
            async for message in connection:
                # A set transaction can outlast a complete sample's Good window.
                # Its viewer must still receive current reads, just as other
                # viewers do. Reply IDs multiplex them; mailbox writes remain
                # serialized by _mailbox_lock, not by the receive loop.
                if len(pending) >= MAX_PENDING_REQUESTS:
                    cancel_pending()
                    await connection.close(code=1013,
                                           reason='Too many concurrent requests')
                    break
                task = asyncio.create_task(
                    self.dispatch(connection.send, state, message))
                pending.add(task)
                task.add_done_callback(completed)
        except Exception as exc:  # a closed socket is a normal end
            log.info("stage=disconnected peer=%s detail=%s", peer, exc)
        finally:
            # Discard queued work on disconnect. An already executing native
            # operation is drained by _run_native_worker, never replayed; its
            # lock remains held until the thread finishes.
            cancel_pending()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            self._states.discard(state)
            await self._apply_read_tiers()

    async def _apply_read_tiers(self):
        if not self._states:
            slow, excluded = set(), set()
        else:
            states = list(self._states)
            slow = set(states[0].slow | states[0].excluded)
            excluded = set(states[0].excluded)
            for state in states[1:]:
                slow.intersection_update(state.slow | state.excluded)
                excluded.intersection_update(state.excluded)
            slow.difference_update(excluded)
        await self.station.set_tiers(slow, excluded)

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
                await send(_ok(rid, await self._read_values(state, params)))
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

    @staticmethod
    def _values_for(state: _ConnState, doc: dict[str, Any]) -> dict[str, Any]:
        """The shared values, with this connection's configuration page.

        Every model's page is already computed; this only picks the one the
        connection last asked for. The path set is identical across models, so
        nothing about discovery changes - only the numbers do.
        """
        values = doc.get("values", {})
        page = (doc.get("configPages") or {}).get(state.config_model)
        merged = dict(values)
        if page:
            merged.update(page)
        merged.update(state.sets.values)
        return merged

    async def _snapshot(self, state: _ConnState) -> dict[str, Any]:
        started = self.station._clock()
        if state not in self._states:
            self._states.add(state)
            await self._apply_read_tiers()
        doc = await self.station.document()
        paths = self.station.paths
        result = dict(doc)
        aged_at = result.pop('_agedAt', None)
        if aged_at is not None:
            # The published ages already include this server-side wait/read.
            # Clients add only the remaining RPC time, avoiding double aging.
            result['responseProcessingMs'] = max(0, (aged_at - started) * 1000)
        result.pop("configPages", None)
        result["discoveryRevision"] = self.station.revision
        result["nodeCount"] = len(paths)
        result["truncated"] = bool(doc.get("truncated", False))
        result["paths"] = [] if state.configured else list(paths)
        result["values"] = {p: v for p, v in self._values_for(state, doc).items() if p not in state.excluded}
        result["dataValues"] = {p: dict(v, value=result['values'].get(p, v.get('value')))
                                for p, v in doc.get("dataValues", {}).items() if p not in state.excluded}
        if self.station.budget is not None:
            for p, v in result['values'].items():
                if p not in result['dataValues']:
                    result['dataValues'][p] = dict(value=v, status=0,
                        tier='fast', ageMs=result['sampleAgeMs'])
            # Connection-specific pages inherit the complete station's quality;
            # they cannot restore a value withdrawn by the shared read cache.
            result['values'] = {p: v for p, v in result['values'].items()
                if self.station.healthy and
                (result['dataValues'].get(p, {}).get('status', 0) & 0xc0000000) == 0}
        return result

    async def _discover_paths(self) -> dict[str, Any]:
        await self.station.document()
        paths = self.station.paths
        return {
            "revision": self.station.revision,
            "nodeCount": len(paths),
            "paths": list(paths),
        }

    async def _read_values(self, state: _ConnState,
                           params: dict[str, Any]) -> dict[str, Any]:
        with_metadata = params.get('includeDataValues', False)
        if not isinstance(with_metadata, bool):
            raise ValueError('includeDataValues must be Boolean.')
        if self.station.paths and params.get('revision') == self.station.revision:
            indices = validate_indices(params.get('indices'), len(self.station.paths),
                maximum=MAX_TARGET_READ_PATHS, require_non_empty=True)
            requested = [self.station.paths[i] for i in indices]
            control_paths = getattr(self.station._read_fn, 'mailbox_paths', ())
            if set(requested) <= set(control_paths):
                doc = await self.station.mailbox_document()
                if params.get('revision') != self.station.revision:
                    raise StaleRevision('Discovery revision is stale; discover paths again.')
                return self._target_read_result(state, doc, requested, with_metadata,
                                                control_reply=True)
        doc = await self.station.document()
        if params.get("revision") != self.station.revision:
            raise StaleRevision(
                "Discovery revision is stale; discover paths again.")
        paths = self.station.paths
        indices = validate_indices(
            params.get("indices"), len(paths),
            maximum=MAX_TARGET_READ_PATHS, require_non_empty=True)
        requested = [paths[i] for i in indices]
        if any(p in (state.slow | state.excluded) for p in requested):
            doc = await self.station.targeted(requested, reuse_good=with_metadata)
            if params.get('revision') != self.station.revision:
                raise StaleRevision('Discovery revision is stale; discover paths again.')
        return self._target_read_result(state, doc, requested, with_metadata)

    def _target_read_result(self, state, doc, requested, with_metadata,
                            control_reply=False):
        values = self._values_for(state, doc)
        result = {p: values.get(p) if self.station.budget is None or (
            (control_reply or self.station.healthy) and
            (doc.get('dataValues', {}).get(p, {}).get('status', 0x80000000) & 0xc0000000) == 0)
            else None for p in requested}
        if not with_metadata:
            return result
        metadata = {}
        for path, value in result.items():
            source = doc.get('dataValues', {}).get(path, {})
            metadata[path] = dict(source, value=value,
                status=source.get('status', 0x80000000) if value is not None else 0x80320000,
                ageMs=source.get('ageMs', 0))
        return {'protocol': 'fraktal.opcua.read-values.v1',
                'values': result, 'dataValues': metadata}

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
        self._states.add(state)
        state.configured = True
        state.excluded = frozenset(self.station.paths[i] for i in excluded)
        state.slow = frozenset(self.station.paths[i] for i in slow)
        await self._apply_read_tiers()
        return True

    def _guard_write(self, state: _ConnState) -> None:
        if not self._write_token:
            raise WriteRefused(READ_ONLY_REFUSED)
        if not state.authenticated:
            raise WriteRefused(ANON_WRITE_REFUSED)

    def seed_sequences(self, doc: dict[str, Any]) -> None:
        """Adopt the native committed input without regressing a reserved attempt.

        The reference server seeds the same way, and without it the first batch
        after a gateway restart carries no expectation at all: any sequence
        would be accepted, including one the controller has already consumed.
        A client that replayed a stale commit would then re-run a command the
        operator issued once. Seeding makes the guard mean something from the
        first write rather than only from the second.

        A modular forward native observation can advance this gateway's record.
        A lagging observation cannot release an interrupted/reserved attempt.

        Zero is an ordinary wrapped sequence, and may also be a lagging read
        before the first committed request. It cannot prove a download. The
        owner restarts the gateway after a download, as the deployment loop
        requires; never reset a replay guard from an ambiguous value.
        """
        for path, value in doc.get("values", {}).items():
            if not (path.endswith("/HmiRequest/Sequence")
                    and isinstance(value, int) and not isinstance(value, bool)):
                continue
            mailbox = path[: -len("/Sequence")]
            observed = value & 0xffffffff
            known = self._mailbox_sequences.setdefault(mailbox, observed)
            # A trusted native observation may advance the record (for example
            # the exclusive bench harness), but a lagging read cannot regress
            # a committed/reserved request. Use modular distance across wrap.
            if 0 < ((observed - known) & 0xffffffff) < 0x80000000:
                self._mailbox_sequences[mailbox] = observed

    @staticmethod
    async def _run_writer(call, *args):
        return await _run_native_worker(call, *args)

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
        async with self._mailbox_lock:
            return bool(await self._run_writer(self._write_fn, [(path, vtype, value)],
                                                None))

    async def _write_batch(self, state: _ConnState,
                           params: dict[str, Any]) -> bool:
        started = time.monotonic()
        async with self._mailbox_lock:
            acquired = time.monotonic()
            try:
                return await self._write_batch_locked(state, params)
            finally:
                log.info('stage=mailbox-complete elapsed-ms=%.1f queue-ms=%.1f',
                         (time.monotonic() - started) * 1000, (acquired - started) * 1000)

    async def _write_batch_locked(self, state: _ConnState,
                                  params: dict[str, Any]) -> bool:
        try:
            writes, mailbox, sequence = validate_batch(params)
        except ValueError:
            self._guard_write(state)
            raise
        # Some commands name their target with a string the controller cannot
        # read - a channel browse path, a model code. Resolving here, after
        # validation and before the scope check, keeps every injected write
        # inside the same mailbox the operator was already permitted to
        # command.
        import fraktal_ab_mailbox as mailbox_contract
        import fraktal_ab_projection as station_projection

        query = mailbox_contract.is_config_query(writes)
        if query:
            # D5: the page request is a read operation, including in a viewer
            # with no bearer or write roots. It reaches only this station's
            # canonical root mailbox; arguments cannot carry a mutation.
            if mailbox != f"{station_projection.APP.name}/HmiRequest":
                raise WriteRefused(WRITE_SCOPE_REFUSED)
        else:
            self._guard_write(state)
        for path, _vtype, _value in writes:
            if not query and not permits_write(path, self._write_roots,
                                  self._allow_all_root_mailboxes):
                raise WriteRefused(WRITE_SCOPE_REFUSED)
        # Core §3.8a: remember which model this connection is asking about, so
        # the page it reads next is that model's. Recorded only after the scope
        # and controller write succeeded - a refused request must not change what the connection
        # sees - and for EVERY query, so the client's ordinary manifest fetch
        # (model 0) puts it back on the running record.
        # Seed from the controller before judging the sequence, so the very
        # first commit is checked against what the machine has actually
        # answered rather than against nothing.
        if self.station.budget is not None and not self.station.healthy:
            await self.station.document(force=True)
        document = await self.station.mailbox_document()
        if self.station.budget is not None and not self.station.healthy:
            raise WriteRefused('complete station read is late or expired; refresh before commanding')
        self.seed_sequences(document)
        observed = document['values']
        writes = mailbox_contract.resolve_batch(
            station_projection.APP, writes,
            [document['values'].get(f'{station_projection.APP.name}/AvailableModels[{i}]/ModelCode', '')
             for i in range(1, document['values'].get(station_projection.APP.name + '/AvailableModelCount', 0) + 1)]
            if station_projection.APP.model_capacity else None)
        request = observed.get(mailbox + '/Sequence')
        ack = observed.get(mailbox.replace('/HmiRequest', '/HmiResponse') + '/AckSequence')
        if request is not None and ack is not None and request != ack:
            raise WriteRefused('previous native mailbox request is still awaiting acknowledgement')
        previous = self._mailbox_sequences.get(mailbox)
        if previous is not None and not 0 < ((sequence - previous) & 0xffffffff) < 0x80000000:
            raise WriteRefused(
                f"stale mailbox sequence: requires a fresh forward sequence "
                f"after {previous}, got {sequence}")
        if self._write_fn is None:
            raise WriteRefused(WRITE_NOT_CONNECTED)
        # Burn the sequence before I/O, including an interrupted payload or an
        # ambiguous commit. The HMI reserves identically. Recovery accepts only
        # a fresh next request; this attempt is never replayed automatically.
        self._mailbox_sequences[mailbox] = sequence
        self.station._doc = None
        from fraktal_ab_sets import SET_KINDS
        kind = next((v for p, _t, v in writes if p.endswith('/HmiRequest/Kind')), None)
        if kind != mailbox_contract.IMPORT_CONFIG_SET:
            state.sets.interrupt()
        if kind in SET_KINDS and hasattr(self._write_fn, 'set_command'):
            state.sets.committed_sequence = None
            try:
                accepted = bool(await self._run_fresh_writer(self._write_fn.set_command, writes, mailbox, state.sets))
            except Exception:
                # I/O after a committed set command may fail. Never replay an
                # ambiguous load or save under the same external Sequence.
                if state.sets.committed_sequence == sequence:
                    self._mailbox_sequences[mailbox] = sequence
                    self.station._doc = None
                state.sets.interrupt()
                raise
        else:
            try:
                accepted = bool(await self._run_fresh_writer(self._write_fn, writes, mailbox))
            finally:
                self.station._doc = None
        if accepted:
            self.station._doc = None  # next acknowledgement read sees this command
            self._mailbox_sequences[mailbox] = sequence
            state.config_model = mailbox_contract.requested_config_model(
                writes, state.config_model)
        return accepted

    async def _run_fresh_writer(self, call, *args):
        def deliver():
            # Re-check after waiting for the native worker, immediately before
            # delivery. Partial Ack reads never extend complete-station health.
            if self.station.budget is not None and not self.station.healthy:
                raise WriteRefused('complete station read expired before command delivery')
            return call(*args)
        return await self._run_writer(deliver)


class SerialMismatch(Exception):
    """The controller answering is not the one this gateway is pinned to."""


def explain_build_mismatch(controller: Any, loaded: str,
                           on_disk: Optional[str]) -> str:
    """What to DO about a content-hash mismatch, from which side moved.

    The gateway loads the declaration once, at start. A download after that is
    the common case - the controller now runs exactly what the repository
    declares, and only this process is behind - and an operator sees it as
    "commands do nothing". The other cases need a download instead.
    """
    head = f"the controller runs build {controller!r}; this gateway loaded {loaded!r}"
    if on_disk is None:
        return (f"{head}, and the repository's current declaration could not be "
                f"read to tell which side moved")
    if on_disk == controller:
        return (f"{head}, and the repository now declares {on_disk!r} too: the "
                f"download landed after this gateway started. Restart the gateway.")
    if on_disk == loaded:
        return (f"{head}, which is what the repository declares. The controller "
                f"is not running this repository's build: download the L5X "
                f"generated from it, or run the gateway from the commit that "
                f"produced the loaded build.")
    return (f"{head}, and the repository now declares {on_disk!r}, which is "
            f"neither. Regenerate, download, then restart the gateway.")


def declared_on_disk(timeout: float = 60.0) -> Optional[str]:
    """The content hash of the declaration as the files say NOW.

    A fresh interpreter, because this process imported its declaration at
    start - which is exactly the copy that may be stale. Returns None when the
    declaration cannot be evaluated; the caller says so rather than guessing.
    """
    import subprocess
    import sys

    code = ("import fraktal_ab_manifest as m, fraktal_ab_station as s;"
            "print(m.content_hash(s.application()))")
    try:
        done = subprocess.run([sys.executable, "-c", code],
                              cwd=os.path.dirname(os.path.abspath(__file__)),
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = done.stdout.strip().splitlines()
    return lines[-1].strip() if done.returncode == 0 and lines else None


class BuildMismatchExplainer:
    """Turn a BuildMismatch into a refusal that names its fix, logged once.

    The read loop meets the mismatch on every poll, so the on-disk hash is
    cached per controller hash for a minute rather than recomputed each time,
    and the error is logged when its text changes, not on every read.
    """

    def __init__(self, probe: Callable[[], Optional[str]] = declared_on_disk,
                 clock: Callable[[], float] = time.monotonic, ttl: float = 60.0):
        self._probe, self._clock, self._ttl = probe, clock, ttl
        self._cached: Optional[tuple[Any, float, Optional[str]]] = None
        self._logged: Optional[str] = None

    def __call__(self, refusal: Any) -> Exception:
        import fraktal_ab_projection as projection

        now = self._clock()
        cached = self._cached
        stale = (cached is None or cached[0] != refusal.controller_hash
                 or now - cached[1] > self._ttl)
        if stale:
            cached = (refusal.controller_hash, now, self._probe())
            self._cached = cached
        message = explain_build_mismatch(refusal.controller_hash,
                                         refusal.declared_hash, cached[2])
        if message != self._logged:
            log.error("stage=build-mismatch detail=%s", message)
            self._logged = message
        return projection.ProjectionRefused(message)


class _NativeReader:
    """A blocking read that reuses one pylogix connection and reconnects on drop.

    The identity is checked when the connection is opened, before any manifest is
    trusted; ``read_document`` then validates the manifest content hash on every
    read (fail-closed). A read on a stale reused socket reconnects and retries
    once transparently, so an idle period does not surface a spurious error to
    the HMI. A serial mismatch is a deterministic refusal and is never retried,
    and a freshly opened connection that still fails to read is a real fault, so
    it is not hammered.
    """
    def __init__(self, target, slot, expected_serial, access_level):
        import fraktal_ab_projection as projection
        self.target, self.slot, self.expected_serial = target, slot, expected_serial
        self.access_level = (projection.ACCESS_OPERATOR if access_level is None else access_level)
        self.plc = None
        self.budget = projection.APP.read_budget
        self.plan = projection.ReadPlan(budget=self.budget)
        self.set_tiers = self.plan.set_tiers
        self.targeted = self.plan.targeted
        self.explain = BuildMismatchExplainer()
        self.mailbox_paths = frozenset(f'{projection.APP.name}/{leaf}'
                                     for leaf in projection.MAILBOX_CONTROL_LEAVES)

    def _open(self) -> Any:
        import fraktal_ab_projection as projection
        from pylogix import PLC
        plc = PLC()
        plc.IPAddress = self.target
        plc.ProcessorSlot = self.slot
        if self.budget is not None:
            plc.ConnectionSize = self.budget.connection_bytes
        try:
            serial, ok = projection.verify_serial(plc, self.expected_serial)
        except Exception:
            plc.Close()
            raise
        if not ok:
            plc.Close()
            raise SerialMismatch(
                f"serial {serial} is not the expected controller; refusing")
        log.info("stage=identity-verified serial=%s target=%s", serial, self.target)
        return plc

    def _drop(self) -> None:
        plc = self.plc
        if plc is not None:
            try:
                plc.Close()
            except Exception:
                pass
            self.plc = None
        self.plan.manifest = None
        self.plan.groups.clear()

    def mailbox(self):
        return self._read(mailbox_only=True)

    def __call__(self):
        return self._read()

    def _read(self, mailbox_only=False) -> dict[str, Any]:
        import fraktal_ab_projection as projection
        last_exc: Optional[BaseException] = None
        for _ in range(2):
            opened_now = False
            try:
                plc = self.plc
                if plc is None:
                    plc = self._open()
                    self.plc = plc
                    opened_now = True
                if mailbox_only and self.plan.manifest is not None:
                    return projection.read_mailbox_document(plc, self.plan)
                return projection.read_document(plc, self.access_level, plan=self.plan)
            except SerialMismatch:
                self._drop()
                raise
            except projection.BuildMismatch as refusal:
                # Deterministic, like a serial mismatch: retrying cannot help,
                # and the connection itself is fine.
                raise self.explain(refusal) from refusal
            except Exception as exc:
                last_exc = exc
                self._drop()
                if opened_now:
                    break  # a fresh connection that failed is a real fault
        assert last_exc is not None
        raise last_exc


def build_reader(target: str, slot: int, expected_serial: str,
                 access_level: int | None = None) -> Callable[[], dict[str, Any]]:
    return _NativeReader(target, slot, expected_serial, access_level)


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
    parser.add_argument(
        "--access-level", default="operator",
        choices=("none", "operator", "technician", "engineer", "admin"),
        help="pre-login display ceiling, bounded by the controller's actual "
             "anonymous level (NONE). After LOGIN the PLC user's level wins. "
             "Legacy declarations without a controller provider retain their "
             "deployment-wide level. This option never grants PLC permissions.")
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
    # every mutation has already passed the Core §14 bearer gate and
    # permits_write. Without a token only complete, inert QUERY_CONFIG batches
    # can reach the writer; read-only remains the default.
    if write_token:
        log.warning("stage=write-gate-enabled source=%s detail=Core §14 write "
                    "gate is on (authenticated writes only); writes reach the "
                    "root command mailbox and nothing else",
                    WRITE_TOKEN_ENV if os.environ.get(WRITE_TOKEN_ENV) else "argv")

    import fraktal_ab_projection as projection

    access_level = projection.ACCESS_LEVELS[args.access_level]
    if access_level > projection.ACCESS_OPERATOR:
        # A raised level is a posture change, so it is a WARNING beside the
        # write-gate warnings rather than an INFO nobody reads. The default
        # says nothing, because the default changes nothing.
        log.warning("stage=access-level level=%s detail=pre-login display "
                    "ceiling only when the controller owns access; logged-in "
                    "levels and every command permission come from the PLC. "
                    "Legacy declarations apply this level to every viewer", args.access_level)
    station = Station(build_reader(args.target, args.slot, args.expect_serial,
                                   access_level))
    gateway = Gateway(
        station,
        allowed_origins=frozenset(_normalize_origin(o) for o in args.allow_origin),
        write_token=write_token,
        write_roots=frozenset(args.write_root),
        allow_all_root_mailboxes=bool(write_token) and not args.write_root,
        # D5 page queries use the same serialized, serial-guarded mailbox
        # writer in a viewer. Every mutation still needs the bearer and scope.
        write_fn=MailboxWriter(args.target, args.slot, args.expect_serial))
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

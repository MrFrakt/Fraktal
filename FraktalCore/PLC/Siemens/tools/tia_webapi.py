"""Fraktal/TIA Web API probe - the licence-free self-description transport spike
(Part IV §11.1a, spike S1/S7/S9).

The S7 CPU's Web API (JSON-RPC 2.0 over HTTPS, POST /api/jsonrpc) gives symbolic
read/write/browse of optimized data to an authenticated web-server user, with no
runtime licence. Exposure follows the same "Accessible from HMI/OPC UA/Web API"
member attribute Fraktal already sets, so private state is not reachable.

    python tia_webapi.py probe    [--host 192.168.0.10]          (no login needed)
    python tia_webapi.py browse   --var "\"SpikeUnit\""
    python tia_webapi.py tree     --root SpikeUnit [--max 2000]
    python tia_webapi.py snapshot --root SpikeUnit [--repeat 10]
    python tia_webapi.py read     --var "\"SpikeUnit\".Status.State"
    python tia_webapi.py mailbox  --root SpikeUnit --kind 3 --int 0

Login: --user (default "fraktal"), password from the environment variable
FRAKTAL_TIA_WEB_PASSWORD only (never on the command line, never logged).

TLS: the CPU presents a self-signed certificate. It is accepted only when its
SHA-256 fingerprint equals the pinned one (--pin-file, default
%LOCALAPPDATA%\\Fraktal\\TiaStations\\<host>.webapi.pin). The first contact needs
an explicit --trust-first, which records the fingerprint; every later mismatch
fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import pathlib
import socket
import ssl
import statistics
import sys
import time

DEFAULT_HOST = "192.168.0.10"


class WebApiError(RuntimeError):
    def __init__(self, method, error):
        self.code = error.get("code")
        super().__init__("%s -> %s %s" % (method, self.code, error.get("message")))


class WebApi:
    def __init__(self, host: str, pin_file: pathlib.Path, trust_first: bool, timeout: float = 10.0):
        self.host = host
        self.token = None
        self._id = 0
        self._timeout = timeout
        self._pin_file = pin_file
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE     # verified below by pinned fingerprint instead
        self._connect(trust_first)

    def _connect(self, trust_first=False):
        """Opens a TCP+TLS connection and verifies the pin on EVERY connection.
        The 1214C closes an idle keep-alive connection after 1-2 s (measured), so
        connections are disposable; the login token outlives them."""
        self.conn = http.client.HTTPSConnection(self.host, 443, timeout=self._timeout, context=self._ctx)
        self.conn.connect()
        der = self.conn.sock.getpeercert(binary_form=True)
        self.fingerprint = hashlib.sha256(der).hexdigest()
        pin_file = self._pin_file
        if pin_file.exists():
            pinned = pin_file.read_text(encoding="ascii").strip()
            if pinned != self.fingerprint:
                self.conn.close()
                raise ssl.SSLError("certificate fingerprint %s does not match pin %s (%s)"
                                   % (self.fingerprint, pinned, pin_file))
        elif trust_first:
            pin_file.parent.mkdir(parents=True, exist_ok=True)
            pin_file.write_text(self.fingerprint + "\n", encoding="ascii")
            print("pinned certificate sha256=%s -> %s" % (self.fingerprint, pin_file))
        else:
            self.conn.close()
            raise ssl.SSLError("no pin for %s; first contact needs --trust-first (sha256=%s)"
                               % (self.host, self.fingerprint))

    def _post(self, payload):
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Auth-Token"] = self.token
        try:
            self.conn.request("POST", "/api/jsonrpc", body=body, headers=headers)
            resp = self.conn.getresponse()
        except (ConnectionError, http.client.RemoteDisconnected, http.client.CannotSendRequest,
                http.client.BadStatusLine):
            # The server dropped an idle connection: reconnect (pin re-checked) and
            # send once more. Safe for reads; a mailbox write is idempotent because
            # the PLC acts only on a CHANGED Sequence, so a resent value is inert.
            self.conn.close()
            self._connect()
            self.conn.request("POST", "/api/jsonrpc", body=body, headers=headers)
            resp = self.conn.getresponse()
        data = resp.read()
        if resp.status != 200:
            raise RuntimeError("HTTP %d: %s" % (resp.status, data[:200]))
        return json.loads(data.decode("utf-8"))

    def call(self, method, params=None):
        self._id += 1
        req = {"jsonrpc": "2.0", "method": method, "id": self._id}
        if params is not None:
            req["params"] = params
        reply = self._post(req)
        if "error" in reply:
            raise WebApiError(method, reply["error"])
        return reply.get("result")

    def bulk(self, calls):
        """calls: list of (method, params). Returns list of (result, error) in order."""
        reqs = []
        for method, params in calls:
            self._id += 1
            reqs.append({"jsonrpc": "2.0", "method": method, "params": params, "id": self._id})
        replies = self._post(reqs)
        by_id = {r.get("id"): r for r in replies}
        return [(by_id[q["id"]].get("result"), by_id[q["id"]].get("error")) for q in reqs]

    def login(self, user):
        # A second Api.Login on a session that holds a valid token answers
        # 101 "Already Authenticated" (measured, 1214C V4.7), so log in once.
        if self.token:
            return
        password = os.environ.get("FRAKTAL_TIA_WEB_PASSWORD")
        if not password:
            raise SystemExit("set FRAKTAL_TIA_WEB_PASSWORD (the web-server user's password)")
        self.token = self.call("Api.Login", {"user": user, "password": password})["token"]


def var_path(segments):
    """Fraktal browse paths quote the DB; members are plain unless they need quotes."""
    out = '"%s"' % segments[0]
    for s in segments[1:]:
        out += "." + (s if s.replace("_", "").isalnum() and s.lower() != "name" else '"%s"' % s)
    return out


def walk(api, root, limit):
    """Breadth-first PlcProgram.Browse of one DB; returns leaves [(path, datatype)]."""
    leaves, queue, browsed = [], [[root]], 0
    while queue and len(leaves) < limit:
        node = queue.pop(0)
        children = api.call("PlcProgram.Browse", {"var": var_path(node), "mode": "children"})
        browsed += 1
        for c in children or []:
            seg = node + [c["name"]]
            if c.get("array_dimensions"):
                dims = c["array_dimensions"][0]
                for i in range(dims["start_index"], dims["start_index"] + dims["count"]):
                    item = seg[:-1] + ["%s[%d]" % (c["name"], i)]
                    if c.get("has_children"):
                        queue.append(item)
                    else:
                        leaves.append((item, c.get("datatype")))
            elif c.get("has_children"):
                queue.append(seg)
            else:
                leaves.append((seg, c.get("datatype")))
    return leaves, browsed


def leaf_var(segments):
    # array elements carry their index inside the segment: Rows[3]
    head = '"%s"' % segments[0]
    parts = []
    for s in segments[1:]:
        base, _, idx = s.partition("[")
        name = base if (base.replace("_", "").isalnum() and base.lower() != "name") else '"%s"' % base
        parts.append(name + ("[" + idx if idx else ""))
    return ".".join([head] + parts)


def cmd_probe(api, args):
    print("Api.Ping:", api.call("Api.Ping"))
    for m in ("Api.Version", "Api.GetQuantityStructures", "Api.GetAuthenticationMode"):
        try:
            print(m + ":", json.dumps(api.call(m)))
        except WebApiError as e:
            print(m + ": error", e.code)
    methods = api.call("Api.Browse")
    names = sorted(m["name"] if isinstance(m, dict) else str(m) for m in methods or [])
    print("Api.Browse: %d methods" % len(names))
    for n in names:
        print("  ", n)
    print("certificate sha256:", api.fingerprint)
    return 0


def cmd_browse(api, args):
    api.login(args.user)
    for c in api.call("PlcProgram.Browse", {"var": args.var, "mode": "children"}) or []:
        print(json.dumps(c))
    return 0


def cmd_tree(api, args):
    api.login(args.user)
    t0 = time.perf_counter()
    leaves, browsed = walk(api, args.root, args.max)
    dt = time.perf_counter() - t0
    for seg, dtype in leaves:
        print("%-60s %s" % (leaf_var(seg), dtype))
    print("leaves=%d browse_calls=%d discovery_ms=%.0f" % (len(leaves), browsed, dt * 1000))
    return 0


def cmd_read(api, args):
    api.login(args.user)
    print(json.dumps(api.call("PlcProgram.Read", {"var": args.var})))
    return 0


def cmd_snapshot(api, args):
    api.login(args.user)
    leaves, _ = walk(api, args.root, args.max)
    vars_ = [leaf_var(s) for s, _ in leaves]
    times, errors = [], {}
    for _ in range(args.repeat):
        t0 = time.perf_counter()
        values = {}
        for i in range(0, len(vars_), args.chunk):
            chunk = vars_[i:i + args.chunk]
            for v, (res, err) in zip(chunk, api.bulk([("PlcProgram.Read", {"var": v}) for v in chunk])):
                if err:
                    errors[v] = err.get("code")
                else:
                    values[v] = res
        times.append((time.perf_counter() - t0) * 1000)
    for v in vars_[:args.show]:
        print("%-60s %s" % (v, json.dumps(values.get(v))))
    print("leaves=%d chunk=%d snapshots=%d ms: median=%.0f max=%.0f min=%.0f errors=%d"
          % (len(vars_), args.chunk, len(times), statistics.median(times), max(times), min(times), len(errors)))
    for v, code in list(errors.items())[:10]:
        print("  error %s on %s" % (code, v))
    return 0 if not errors else 1


def cmd_mailbox(api, args):
    """Core §3.10(a″): arguments first, Sequence LAST in a separate request, then
    wait for the matching AckSequence. Never replays: a timeout is reported, not retried."""
    api.login(args.user)
    root = '"%s"' % args.root
    seq = api.call("PlcProgram.Read", {"var": root + ".HmiRequest.Sequence"})
    nxt = (int(seq) + 1) & 0xFFFFFFFF
    writes = [("PlcProgram.Write", {"var": root + ".HmiRequest.Kind", "value": args.kind}),
              ("PlcProgram.Write", {"var": root + ".HmiRequest.IntValue", "value": args.int})]
    for res, err in api.bulk(writes):
        if err:
            raise SystemExit("argument write failed: %s" % err)
    t0 = time.perf_counter()
    api.call("PlcProgram.Write", {"var": root + ".HmiRequest.Sequence", "value": nxt})
    while True:
        ack = api.call("PlcProgram.Read", {"var": root + ".HmiResponse.AckSequence"})
        if int(ack) == nxt:
            break
        if time.perf_counter() - t0 > args.timeout:
            print("no acknowledgement within %.1f s (sequence %d) - not replayed" % (args.timeout, nxt))
            return 2
        time.sleep(0.02)
    ms = (time.perf_counter() - t0) * 1000
    accepted = api.call("PlcProgram.Read", {"var": root + ".HmiResponse.Accepted"})
    diag = api.call("PlcProgram.Read", {"var": root + ".HmiResponse.Diagnostic"})
    print("kind=%d int=%d sequence=%d acknowledged in %.0f ms accepted=%s diagnostic=%r"
          % (args.kind, args.int, nxt, ms, accepted, diag))
    return 0 if accepted else 1


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--user", default="fraktal")
    p.add_argument("--pin-file")
    p.add_argument("--trust-first", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    b = sub.add_parser("browse"); b.add_argument("--var", required=True)
    t = sub.add_parser("tree"); t.add_argument("--root", required=True); t.add_argument("--max", type=int, default=2000)
    r = sub.add_parser("read"); r.add_argument("--var", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("--root", required=True)
    s.add_argument("--max", type=int, default=2000); s.add_argument("--repeat", type=int, default=5)
    s.add_argument("--chunk", type=int, default=50); s.add_argument("--show", type=int, default=12)
    m = sub.add_parser("mailbox"); m.add_argument("--root", required=True)
    m.add_argument("--kind", type=int, required=True); m.add_argument("--int", type=int, default=0)
    m.add_argument("--timeout", type=float, default=3.0)
    args = p.parse_args(argv)
    base = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "Fraktal" / "TiaStations"
    pin = pathlib.Path(args.pin_file) if args.pin_file else base / ("%s.webapi.pin" % args.host)
    api = WebApi(args.host, pin, args.trust_first)
    handlers = {"probe": cmd_probe, "browse": cmd_browse, "tree": cmd_tree, "read": cmd_read,
                "snapshot": cmd_snapshot, "mailbox": cmd_mailbox}
    return handlers[args.cmd](api, args)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ssl.SSLError, socket.error, WebApiError, RuntimeError) as e:
        print("error:", e)
        sys.exit(3)

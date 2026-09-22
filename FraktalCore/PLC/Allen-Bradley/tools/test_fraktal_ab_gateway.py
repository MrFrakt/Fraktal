#!/usr/bin/env python3
"""Unit tests for the AB HMI gateway's protocol bookkeeping.

No controller and no socket: the gateway's pure logic - origin acceptance,
index validation, revision discipline - and its request dispatch are driven
against a fake station that returns a fixed projection document. Every check has
a paired negative, because a probe that cannot fail is not evidence.
"""

import asyncio
import json
import unittest

import fraktal_ab_gateway as gw


def _doc(extra=None):
    values = {
        "Press/Status/Name": "Press",
        "Press/Status/ModuleType": 1,
        "Press/Status/DisplayNameKey": "project.module.press",
        "Press/Status/State": 0,
        "Press/Status/FaultActive": False,
        "Press/Status/Diagnostic/ReasonCode": 0,
        "Press/ModeActivePublished": 0,
        "Press/GoodCount": 0,
        "Press/NokCount": 0,
        "Press/CurrentStep/StepNo": 0,
        "Press/Decision/Default": 0,
        "Press/Door/Status/Name": "Press.Door",
        "Press/Door/Status/ModuleType": 3,
        "Press/Door/Status/State": 0,
        "Press/Door/Status/FaultActive": False,
        "Press/Door/Status/Diagnostic/ReasonCode": 0,
        "Press/Door/Status/DisplayNameKey": "project.module.door",
    }
    if extra:
        values.update(extra)
    return {
        "schema": "fraktal.ab.projection",
        "schemaVersion": 1,
        "values": values,
        "dataValues": {},
        "truncated": False,
        "nodeCount": len(values),
        "moduleCount": 2,
        "configRevision": 4338506,
        "contentHash": "42334AD69FD1A3AB",
        "absent": [{"path": "AlarmLog/*", "reason": "owed work"}],
    }


class _Sends:
    """Collects the JSON envelopes the dispatcher sends."""

    def __init__(self):
        self.sent = []

    async def __call__(self, message):
        self.sent.append(json.loads(message))

    @property
    def last(self):
        return self.sent[-1]


def _station(source=None):
    holder = {"doc": source() if source else _doc()}
    return gw.Station(lambda: holder["doc"]), holder


def _run(coro):
    return asyncio.run(coro)


class OriginTests(unittest.TestCase):
    def test_a_loopback_http_origin_is_accepted(self):
        self.assertTrue(gw.accepts_origin("http://127.0.0.1:8080"))
        self.assertTrue(gw.accepts_origin("https://localhost"))
        self.assertTrue(gw.accepts_origin("http://[::1]:9000"))

    def test_a_remote_or_malformed_origin_is_refused(self):
        self.assertFalse(gw.accepts_origin("http://192.168.100.50:8080"))
        self.assertFalse(gw.accepts_origin("http://example.com"))
        self.assertFalse(gw.accepts_origin(None))
        self.assertFalse(gw.accepts_origin("null"))
        self.assertFalse(gw.accepts_origin("ftp://127.0.0.1"))
        self.assertFalse(gw.accepts_origin("http://127.0.0.1/path"))

    def test_an_explicitly_allowed_origin_is_accepted(self):
        allowed = frozenset({"https://hmi.example"})
        self.assertTrue(gw.accepts_origin("https://hmi.example", allowed))
        # ...and still refused without the allow-list entry (paired).
        self.assertFalse(gw.accepts_origin("https://hmi.example"))


class IndexTests(unittest.TestCase):
    def test_valid_indices_pass(self):
        self.assertEqual(gw.validate_indices([0, 2, 5], 6), [0, 2, 5])

    def test_a_bad_index_list_is_rejected(self):
        with self.assertRaises(ValueError):
            gw.validate_indices("not-a-list", 6)
        with self.assertRaises(ValueError):
            gw.validate_indices([], 6, require_non_empty=True)
        with self.assertRaises(ValueError):
            gw.validate_indices([0, 1, 2], 6, maximum=2)
        with self.assertRaises(ValueError):
            gw.validate_indices([-1], 6)
        with self.assertRaises(ValueError):
            gw.validate_indices([6], 6)
        with self.assertRaises(ValueError):
            gw.validate_indices([True], 6)  # bool is not an index


class RevisionTests(unittest.TestCase):
    def test_the_revision_starts_at_zero_and_bumps_to_one(self):
        station, _ = _station()
        self.assertEqual(station.revision, 0)
        _run(station.document())
        self.assertEqual(station.revision, 1)
        self.assertGreater(len(station.paths), 0)

    def test_an_unchanged_station_holds_its_revision(self):
        station, _ = _station()
        _run(station.document())
        _run(station.document(force=True))
        self.assertEqual(station.revision, 1)

    def test_a_changed_path_set_bumps_the_revision(self):
        station, holder = _station()
        _run(station.document())
        holder["doc"] = _doc(extra={"Press/PressRam/Status/Name": "Press.PressRam"})
        _run(station.document(force=True))
        self.assertEqual(station.revision, 2)


class SnapshotTests(unittest.TestCase):
    def test_the_snapshot_carries_a_positive_revision_and_the_paths(self):
        station, _ = _station()
        g = gw.Gateway(station)
        state = gw._ConnState()
        result = _run(g._snapshot(state))
        self.assertGreater(result["discoveryRevision"], 0)
        self.assertEqual(result["nodeCount"], len(station.paths))
        self.assertFalse(result["truncated"])
        self.assertTrue(result["paths"])  # non-empty until tiers are configured
        self.assertIn("Press/Status/Name", result["values"])
        self.assertEqual(result["values"]["Press/Status/Name"], "Press")

    def test_a_configured_client_no_longer_gets_the_path_list(self):
        station, _ = _station()
        g = gw.Gateway(station)
        state = gw._ConnState()
        state.configured = True
        result = _run(g._snapshot(state))
        self.assertEqual(result["paths"], [])
        # ...but an unconfigured client still does (paired).
        self.assertTrue(_run(g._snapshot(gw._ConnState()))["paths"])


class DispatchTests(unittest.TestCase):
    def _gateway(self):
        station, holder = _station()
        return gw.Gateway(station), station, holder

    def _call(self, gateway, method, params=None, rid=1, protocol=gw.PROTOCOL):
        sends = _Sends()
        request = {"id": rid, "method": method,
                   "params": params if params is not None else {}}
        if protocol is not None:
            request["protocol"] = protocol
        _run(gateway.dispatch(sends, gw._ConnState(), json.dumps(request)))
        return sends.last

    def test_write_is_refused_fail_closed(self):
        gateway, _, _ = self._gateway()
        reply = self._call(gateway, "write",
                            {"path": "Press/Cmd", "valueType": "boolean", "value": True})
        self.assertFalse(reply["ok"])
        self.assertIn("read-only", reply["error"])
        self.assertIn("11.2.1", reply["error"])

    def test_write_batch_is_refused_fail_closed(self):
        gateway, _, _ = self._gateway()
        reply = self._call(gateway, "writeBatch", {"writes": []})
        self.assertFalse(reply["ok"])
        self.assertIn("read-only", reply["error"])

    def test_a_read_only_method_succeeds_where_a_write_does_not(self):
        # The paired positive: the same gateway that refuses writes serves reads.
        gateway, station, _ = self._gateway()
        reply = self._call(gateway, "snapshot")
        self.assertTrue(reply["ok"])
        self.assertIn("values", reply["result"])

    def test_discover_then_read_values_round_trips(self):
        gateway, station, _ = self._gateway()
        disc = self._call(gateway, "discoverPaths")
        self.assertTrue(disc["ok"])
        revision = disc["result"]["revision"]
        paths = disc["result"]["paths"]
        name_index = paths.index("Press/Status/Name")
        reply = self._call(gateway, "readValues",
                           {"revision": revision, "indices": [name_index]})
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["result"]["Press/Status/Name"], "Press")

    def test_a_stale_revision_is_refused(self):
        gateway, station, _ = self._gateway()
        self._call(gateway, "discoverPaths")
        reply = self._call(gateway, "readValues",
                           {"revision": 999, "indices": [0]})
        self.assertFalse(reply["ok"])
        self.assertIn("stale", reply["error"].lower())

    def test_empty_indices_are_refused(self):
        gateway, station, _ = self._gateway()
        disc = self._call(gateway, "discoverPaths")
        reply = self._call(gateway, "readValues",
                           {"revision": disc["result"]["revision"], "indices": []})
        self.assertFalse(reply["ok"])

    def test_set_read_tiers_accepts_a_valid_profile(self):
        gateway, station, _ = self._gateway()
        disc = self._call(gateway, "discoverPaths")
        rev = disc["result"]["revision"]
        reply = self._call(gateway, "setReadTiers",
                           {"revision": rev, "slow": [0], "excluded": [1],
                            "refreshSlow": False})
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["result"], True)
        # A path that is both slow and excluded is refused (paired).
        bad = self._call(gateway, "setReadTiers",
                         {"revision": rev, "slow": [0], "excluded": [0]})
        self.assertFalse(bad["ok"])

    def test_an_unknown_method_is_refused(self):
        gateway, _, _ = self._gateway()
        reply = self._call(gateway, "downloadFirmware")
        self.assertFalse(reply["ok"])
        self.assertIn("Unsupported gateway method", reply["error"])

    def test_a_foreign_protocol_is_refused(self):
        gateway, _, _ = self._gateway()
        reply = self._call(gateway, "snapshot", protocol="some.other.v9")
        self.assertFalse(reply["ok"])
        self.assertIn("protocol", reply["error"].lower())

    def test_a_malformed_request_is_refused(self):
        gateway, _, _ = self._gateway()
        sends = _Sends()
        _run(gateway.dispatch(sends, gw._ConnState(), "this is not json"))
        self.assertFalse(sends.last["ok"])
        self.assertIsNone(sends.last["id"])

    def test_a_bad_id_is_refused(self):
        gateway, _, _ = self._gateway()
        sends = _Sends()
        _run(gateway.dispatch(sends, gw._ConnState(),
                              json.dumps({"id": -1, "method": "snapshot",
                                          "params": {}, "protocol": gw.PROTOCOL})))
        self.assertFalse(sends.last["ok"])

    def test_non_object_params_are_refused(self):
        gateway, _, _ = self._gateway()
        sends = _Sends()
        _run(gateway.dispatch(sends, gw._ConnState(),
                              json.dumps({"id": 1, "method": "snapshot",
                                          "params": [], "protocol": gw.PROTOCOL})))
        self.assertFalse(sends.last["ok"])


class HealthTests(unittest.TestCase):
    class _FakeConn:
        def __init__(self):
            self.status = None
            self.body = None

        def respond(self, status, text):
            self.status = status
            self.body = text
            return ("response", status, text)

    def test_readiness_is_unavailable_before_the_first_read(self):
        station, _ = _station()
        g = gw.Gateway(station)
        conn = self._FakeConn()
        g._health(conn, "/readyz")
        self.assertEqual(int(conn.status), 503)
        body = json.loads(conn.body)
        self.assertFalse(body["plcReady"])

    def test_readiness_is_ok_after_a_successful_read(self):
        station, _ = _station()
        g = gw.Gateway(station)
        _run(station.document())  # a successful read makes the station ready
        conn = self._FakeConn()
        g._health(conn, "/readyz")
        self.assertEqual(int(conn.status), 200)
        self.assertTrue(json.loads(conn.body)["plcReady"])

    def test_liveness_is_ok_even_before_a_read(self):
        station, _ = _station()
        g = gw.Gateway(station)
        conn = self._FakeConn()
        g._health(conn, "/livez")
        self.assertEqual(int(conn.status), 200)


class _Writes:
    """Captures what the write path would send to the controller."""

    def __init__(self, accept=True):
        self.calls = []
        self._accept = accept

    def __call__(self, writes, mailbox):
        self.calls.append((list(writes), mailbox))
        return self._accept


class _AuthConn:
    def __init__(self, authorization=None):
        headers = {} if authorization is None else {"Authorization": authorization}
        self.request = type("Req", (), {"headers": headers})()


def _authed():
    state = gw._ConnState()
    state.authenticated = True
    return state


class WriteValidationTests(unittest.TestCase):
    def test_only_hmirequest_mailboxes_are_writable(self):
        self.assertTrue(gw.permits_write(
            "Press/HmiRequest/IntValue", allow_all_root_mailboxes=True))
        self.assertTrue(gw.permits_write(
            "Press/HmiRequest/IntValue", frozenset({"Press"})))
        # paired negatives
        self.assertFalse(gw.permits_write(
            "Press/Status/State", allow_all_root_mailboxes=True))
        self.assertFalse(gw.permits_write(
            "HmiRequest/IntValue", allow_all_root_mailboxes=True))  # first segment
        self.assertFalse(gw.permits_write(
            "Press/HmiRequest", allow_all_root_mailboxes=True))  # last segment
        self.assertFalse(gw.permits_write(
            "Press/../HmiRequest/IntValue", allow_all_root_mailboxes=True))
        self.assertFalse(gw.permits_write(
            "Press/HmiRequest/IntValue", frozenset({"Other"})))
        self.assertFalse(gw.permits_write("Press/HmiRequest/IntValue"))  # off by default

    def test_write_value_must_match_its_type(self):
        self.assertEqual(
            gw.validate_write(
                {"path": "a/HmiRequest/x", "valueType": "int32", "value": 5}),
            ("a/HmiRequest/x", "int32", 5))
        self.assertEqual(
            gw.validate_write(
                {"path": "p", "valueType": "doubleValue", "value": 2})[2], 2.0)
        for bad in (
            {"path": "", "valueType": "int32", "value": 1},
            {"path": "p", "valueType": "nope", "value": 1},
            {"path": "p", "valueType": "boolean", "value": 1},   # 1 is not a bool
            {"path": "p", "valueType": "int32", "value": True},  # bool is not int32
            {"path": "p", "valueType": "uint32", "value": -1},
            {"path": "p", "valueType": "int32", "value": 0x80000000},
            {"path": "p", "valueType": "string", "value": 123},
        ):
            with self.assertRaises(gw.WriteRefused):
                gw.validate_write(bad)

    def test_batch_requires_a_sequence_commit_on_one_mailbox(self):
        writes, mailbox, seq = gw.validate_batch({"writes": [
            {"path": "Press/HmiRequest/IntValue", "valueType": "int32", "value": 1},
            {"path": "Press/HmiRequest/Sequence", "valueType": "uint32", "value": 7},
        ]})
        self.assertEqual((mailbox, seq), ("Press/HmiRequest", 7))
        # paired negatives
        with self.assertRaises(gw.WriteRefused):
            gw.validate_batch({"writes": []})
        with self.assertRaises(gw.WriteRefused):  # no Sequence commit last
            gw.validate_batch({"writes": [
                {"path": "Press/HmiRequest/IntValue", "valueType": "int32",
                 "value": 1}]})
        with self.assertRaises(gw.WriteRefused):  # two mailboxes
            gw.validate_batch({"writes": [
                {"path": "A/HmiRequest/IntValue", "valueType": "int32", "value": 1},
                {"path": "Press/HmiRequest/Sequence", "valueType": "uint32",
                 "value": 1}]})


class WritePostureTests(unittest.TestCase):
    def _gw(self, **kw):
        station, _ = _station()
        return gw.Gateway(station, write_token="s3cret",
                          allow_all_root_mailboxes=True, **kw)

    def test_read_only_gateway_refuses_every_write(self):
        station, _ = _station()
        g = gw.Gateway(station)  # no write token
        with self.assertRaises(gw.WriteRefused) as raised:
            _run(g._write(_authed(), {"path": "Press/HmiRequest/IntValue",
                                      "valueType": "int32", "value": 1}))
        self.assertIn("read-only", str(raised.exception))
        self.assertIn("11.2.1", str(raised.exception))

    def test_anonymous_write_is_refused_when_the_gate_is_on(self):
        writes = _Writes()
        g = self._gw(write_fn=writes)
        with self.assertRaises(gw.WriteRefused) as raised:
            _run(g._write(gw._ConnState(), {"path": "Press/HmiRequest/IntValue",
                                            "valueType": "int32", "value": 1}))
        self.assertIn("anonymous", str(raised.exception).lower())
        self.assertEqual(writes.calls, [], "must not reach the controller")

    def test_authenticated_in_scope_write_forwards_to_the_controller(self):
        writes = _Writes()
        g = self._gw(write_fn=writes)
        self.assertTrue(_run(g._write(_authed(), {
            "path": "Press/HmiRequest/IntValue", "valueType": "int32", "value": 3})))
        self.assertEqual(writes.calls[0][0],
                         [("Press/HmiRequest/IntValue", "int32", 3)])

    def test_an_off_scope_write_is_refused(self):
        writes = _Writes()
        g = self._gw(write_fn=writes)
        with self.assertRaises(gw.WriteRefused) as raised:
            _run(g._write(_authed(), {"path": "Press/Status/State",
                                      "valueType": "int32", "value": 1}))
        self.assertIn("scope", str(raised.exception).lower())
        self.assertEqual(writes.calls, [])

    def test_write_is_not_connected_without_a_write_path(self):
        g = self._gw(write_fn=None)  # the current controller state
        with self.assertRaises(gw.WriteRefused) as raised:
            _run(g._write(_authed(), {"path": "Press/HmiRequest/IntValue",
                                      "valueType": "int32", "value": 1}))
        self.assertIn("not connected", str(raised.exception).lower())

    def test_batch_commit_enforces_a_monotonic_sequence(self):
        writes = _Writes()
        g = self._gw(write_fn=writes)

        def batch(seq):
            return {"writes": [
                {"path": "Press/HmiRequest/IntValue", "valueType": "int32",
                 "value": 1},
                {"path": "Press/HmiRequest/Sequence", "valueType": "uint32",
                 "value": seq}]}

        self.assertTrue(_run(g._write_batch(_authed(), batch(5))))
        with self.assertRaises(gw.WriteRefused) as raised:  # next must be 6
            _run(g._write_batch(_authed(), batch(9)))
        self.assertIn("sequence", str(raised.exception).lower())
        self.assertTrue(_run(g._write_batch(_authed(), batch(6))))

    def test_dispatch_wraps_an_anonymous_write_as_ok_false(self):
        g = self._gw(write_fn=_Writes())
        sends = _Sends()
        _run(g.dispatch(sends, gw._ConnState(), json.dumps({
            "protocol": gw.PROTOCOL, "id": 1, "method": "write",
            "params": {"path": "Press/HmiRequest/IntValue",
                       "valueType": "int32", "value": 1}})))
        self.assertFalse(sends.last["ok"])
        self.assertIn("anonymous", sends.last["error"].lower())

    def test_authenticate_matches_only_the_configured_bearer(self):
        station, _ = _station()
        g = gw.Gateway(station, write_token="s3cret")
        self.assertTrue(g._authenticate(_AuthConn("Bearer s3cret")))
        self.assertFalse(g._authenticate(_AuthConn("Bearer wrong")))
        self.assertFalse(g._authenticate(_AuthConn(None)))
        # a gateway with no token never authenticates, even with a header
        self.assertFalse(gw.Gateway(station)._authenticate(_AuthConn("Bearer s3cret")))


if __name__ == "__main__":
    unittest.main()

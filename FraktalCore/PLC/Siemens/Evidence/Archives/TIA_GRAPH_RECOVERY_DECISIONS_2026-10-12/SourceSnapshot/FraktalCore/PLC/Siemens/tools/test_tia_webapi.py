"""A dropped write response must not cause another command on a restarted CPU."""
import http.client
import unittest
from unittest.mock import Mock

from tia_webapi import WebApi


class TransportPolicy(unittest.TestCase):
    def client(self):
        api = WebApi.__new__(WebApi)
        api.token = None
        api.conn = Mock()
        api.conn.sock = object()
        api._connect = Mock()
        return api

    def test_lost_write_or_login_response_is_never_replayed(self):
        for method in ("PlcProgram.Write", "Api.Login", "Api.ChangePassword"):
            api = self.client()
            api.conn.getresponse.side_effect = http.client.RemoteDisconnected("lost reply")
            with self.assertRaisesRegex(RuntimeError, "outcome unknown; not replayed"):
                api._post({"method": method, "id": 1})
            api.conn.request.assert_called_once()
            api._connect.assert_not_called()

    def test_mixed_batch_is_not_replayed(self):
        api = self.client()
        api.conn.request.side_effect = ConnectionResetError("reset")
        with self.assertRaisesRegex(RuntimeError, "not replayed"):
            api._post([{"method": "PlcProgram.Read"}, {"method": "PlcProgram.Write"}])
        api._connect.assert_not_called()

    def test_read_retry_reconnects_through_pin_check(self):
        api = self.client()
        response = Mock(status=200)
        response.read.return_value = b'{"result":99}'
        api.conn.getresponse.side_effect = [http.client.RemoteDisconnected("idle"), response]
        self.assertEqual(api._post({"method": "PlcProgram.Read"}), {"result": 99})
        api._connect.assert_called_once_with()
        self.assertEqual(api.conn.request.call_count, 2)

    def test_server_closed_socket_checks_pin_before_sending(self):
        api = self.client()
        api.conn.sock = None
        api._connect.side_effect = RuntimeError("pin mismatch")
        with self.assertRaisesRegex(RuntimeError, "pin mismatch"):
            api._post({"method": "PlcProgram.Read"})
        api.conn.request.assert_not_called()

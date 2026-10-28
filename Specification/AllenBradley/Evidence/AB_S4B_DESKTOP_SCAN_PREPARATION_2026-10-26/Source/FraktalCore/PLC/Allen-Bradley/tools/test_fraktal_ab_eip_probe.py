import importlib.util
import socket
import struct
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("fraktal_ab_eip_probe.py")
SPEC = importlib.util.spec_from_file_location("fraktal_ab_eip_probe", MODULE_PATH)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class EipProbeParserTests(unittest.TestCase):
    def test_identity_parser(self):
        name = b"1769-L24ER-QB1B"
        item = (
            struct.pack("<H", 1)
            + struct.pack(">HH", 2, 44818)
            + socket.inet_aton("192.168.100.89")
            + bytes(8)
            + struct.pack("<HHHBBHI", 1, 14, 149, 33, 14, 0x0060, 0x7036B510)
            + bytes((len(name),)) + name + bytes((3,))
        )
        payload = struct.pack("<HHH", 1, 0x000C, len(item)) + item
        identity = PROBE._parse_identity(payload)
        self.assertEqual(identity["socket_address"], "192.168.100.89")
        self.assertEqual(identity["serial_number"], "7036B510")
        self.assertEqual(identity["revision"], "33.014")
        self.assertEqual(identity["product_name"], "1769-L24ER-QB1B")

    def test_interface_configuration_network_order(self):
        data = b"".join(socket.inet_aton(value) for value in (
            "192.168.100.89", "255.255.255.0", "0.0.0.0", "0.0.0.0", "0.0.0.0"
        )) + struct.pack("<H", 0)
        result = PROBE._ipv4_fields(data, "192.168.100.89")
        self.assertEqual(result["address"], "192.168.100.89")
        self.assertEqual(result["network_mask"], "255.255.255.0")
        self.assertEqual(result["byte_order"], "network")

    def test_interface_configuration_reversed_fields(self):
        data = b"".join(socket.inet_aton(value)[::-1] for value in (
            "192.168.100.89", "255.255.255.0", "192.168.100.1", "0.0.0.0", "0.0.0.0"
        )) + struct.pack("<H", 0)
        result = PROBE._ipv4_fields(data, "192.168.100.89")
        self.assertEqual(result["address"], "192.168.100.89")
        self.assertEqual(result["gateway"], "192.168.100.1")
        self.assertEqual(result["byte_order"], "reversed-per-field")

    def test_time_sync_attribute_path_is_fixed(self):
        sent = []

        class FakeSocket:
            def settimeout(self, _timeout):
                pass

            def sendall(self, payload):
                sent.append(payload)

        original_register = PROBE._register_session
        original_attribute = PROBE._cip_attribute
        try:
            PROBE._register_session = lambda _sock: 7

            def attribute(_sock, session, attribute, *, class_id, instance_id):
                self.assertEqual(session, 7)
                self.assertEqual(class_id, PROBE.CIP_TIME_SYNC_CLASS)
                self.assertEqual(instance_id, PROBE.CIP_TIME_SYNC_INSTANCE)
                return struct.pack("<i", 1 if attribute == 1 else 0)

            PROBE._cip_attribute = attribute
            from unittest.mock import patch
            with patch.object(PROBE.socket, "create_connection") as connect:
                connect.return_value.__enter__.return_value = FakeSocket()
                result = PROBE.read_time_sync("192.0.2.1", 44818, 1.0)
        finally:
            PROBE._register_session = original_register
            PROBE._cip_attribute = original_attribute

        self.assertEqual(result, {
            "ptp_enabled": True,
            "ptp_enable_size": 4,
            "is_synchronized": False,
            "is_synchronized_size": 4,
        })
        self.assertEqual(len(sent), 1)


if __name__ == "__main__":
    unittest.main()

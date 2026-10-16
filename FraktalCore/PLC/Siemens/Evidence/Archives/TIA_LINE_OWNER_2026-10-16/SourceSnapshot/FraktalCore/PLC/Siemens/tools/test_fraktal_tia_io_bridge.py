"""I/O bridge wire admission, raw mapping and replay boundaries."""
import binascii
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import fraktal_tia_io_bridge as bridge


class IoBridgeTests(unittest.TestCase):
    def test_wire_layout_has_network_order_and_independent_ccitt_checksum(self):
        frame = bridge.Frame(1, 0x01020304, 0x11223344, 17, 19, 0x1234, True)
        raw = frame.encode()
        self.assertEqual(len(raw), 32)
        self.assertEqual(raw[:16].hex(), '4652494f010100000102030411223344')
        self.assertEqual(raw[16:30].hex(), '0000001100000013000012340100')
        self.assertEqual(int.from_bytes(raw[30:], 'big'), binascii.crc_hqx(raw[:30], 0xffff))
        self.assertEqual(bridge.Frame.decode(raw, 1), frame)

    def test_truncated_coalesced_and_corrupt_tcp_frames_are_refused(self):
        raw = bridge.Frame(2, 1, 1).encode()
        for wrong in (raw[:-1], raw + raw, raw[:10] + bytes([raw[10] ^ 1]) + raw[11:]):
            with self.assertRaises(ValueError): bridge.Frame.decode(wrong, 2)

    def test_valid_crc_does_not_admit_wrong_role_reserved_bits_or_zero_identity(self):
        raw = bridge.Frame(2, 1, 1).encode()
        for offset, value in ((4, 2), (5, 1), (6, 1), (7, 1), (28, 2), (29, 1), (11, 0), (15, 0)):
            changed = bytearray(raw[:30]); changed[offset] = value
            changed += binascii.crc_hqx(changed, 0xffff).to_bytes(2, 'big')
            with self.subTest(offset=offset), self.assertRaises(ValueError): bridge.Frame.decode(changed, 2)

    def test_no_control_on_or_undefined_input_bits_cross_the_wire(self):
        for frame in (bridge.Frame(2, 1, 1, signals=0x100), bridge.Frame(1, 1, 1, signals=0x4000),
                      bridge.Frame(1, 0, 1), bridge.Frame(1, 1, 0)):
            with self.assertRaises(ValueError): frame.encode()

    def test_map_fits_confirmed_onboard_capacity_and_keeps_control_on_separate(self):
        mapping = bridge.read_map()
        self.assertEqual(len(mapping['inputs']), 14)
        self.assertEqual(len(mapping['outputs']) + len(mapping['inhibited_outputs']), 10)
        self.assertEqual({r['address'] for r in mapping['inhibited_outputs']}, {'%Q1.0', '%Q1.1'})
        for output in mapping['outputs']:
            if 'opposite' in output:
                self.assertEqual(mapping['outputs'][output['opposite']]['opposite'], output['bit'])

    def test_invalid_duplicate_mapping_and_timing_fail_before_generation(self):
        for case in ('address', 'tag', 'bit', 'peer', 'period'):
            mapping = copy.deepcopy(bridge.read_map())
            if case in ('address', 'tag', 'bit'): mapping['inputs'][1][case] = mapping['inputs'][0][case]
            elif case == 'peer': mapping['physical_address'] = mapping['simulator_bench_address']
            else: mapping['period_ms'] = 1000
            with patch.object(bridge.json, 'loads', return_value=mapping):
                with self.subTest(case=case), self.assertRaises(ValueError): bridge.read_map()

    def test_generation_is_deterministic_and_will_not_overwrite_a_project(self):
        self.assertEqual(bridge.build(), bridge.build())
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'sources'
            first = bridge.generate(out)
            self.assertTrue(first['physical'])
            with self.assertRaises(FileExistsError): bridge.generate(out)

    def test_onboard_address_limits_are_enforced(self):
        for kind, address in (('inputs', '%I1.6'), ('inputs', '%I2.0'), ('outputs', '%Q1.2')):
            mapping = copy.deepcopy(bridge.read_map()); mapping[kind][0]['address'] = address
            with patch.object(bridge.json, 'loads', return_value=mapping):
                with self.subTest(address=address), self.assertRaises(ValueError): bridge.read_map()

    def test_forging_manifest_hash_cannot_bypass_source_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'sources'; bridge.generate(out)
            self.assertEqual(bridge.verify(out)['replayed_sources'], 5)
            source = out / '10_PressIoBridge.scl'
            source.write_bytes(source.read_bytes().replace(b'OUTPUT_MAPPING_CONFIRMED : Bool := FALSE;', b'OUTPUT_MAPPING_CONFIRMED : Bool := TRUE;'))
            manifest = bridge.json.loads((out / 'bridge_manifest.json').read_bytes())
            manifest['generated'][source.name] = bridge.hashlib.sha256(source.read_bytes()).hexdigest()
            (out / 'bridge_manifest.json').write_bytes(bridge.json.dumps(manifest).encode('ascii'))
            with self.assertRaises(ValueError): bridge.verify(out)

    def test_prepared_physical_plan_has_explicit_groups_and_no_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); out = directory / 'sources'; bridge.generate(out)
            project = directory / 'Copied.ap20'; project.write_bytes(b'fixture')
            plan = bridge.prepare_plan(out, project, directory / 'native').read_text(encoding='ascii')
            self.assertIn('Framework/IoBridge', plan)
            self.assertIn('Examples/PressIoBridge/00_System', plan)
            self.assertNotIn('download', plan.casefold())
            self.assertEqual(plan.count('compile --plc PLC_1'), 2)

    def test_client_io_image_cannot_be_an_external_command_path(self):
        import tia_lint
        source = bridge.build(False)['38_PressDemoHardwareDriver.scl']
        image = next(b for b in tia_lint.parse_blocks(source) if b.name == 'GDB_PressDemoIO')
        self.assertTrue(image.decls)
        for member in image.decls:
            for flag in ('ExternalAccessible', 'ExternalVisible', 'ExternalWritable'):
                self.assertIn(flag + " := 'False'", member.attrs)


if __name__ == '__main__':
    unittest.main()

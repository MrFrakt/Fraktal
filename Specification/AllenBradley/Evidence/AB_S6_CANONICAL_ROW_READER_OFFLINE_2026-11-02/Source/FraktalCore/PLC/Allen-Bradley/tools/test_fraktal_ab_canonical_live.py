"""Native S5 replay and hostile transport/proof cases for S6 row acquisition."""
from copy import deepcopy
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_live as live
import fraktal_ab_canonical_reader as reader


CAPTURE = Path(__file__).resolve().parents[4] / (
    'Specification/AllenBradley/Evidence/AB_S5_GATEWAY_QUALIFICATION_2026-10-31/'
    'Runtime/generic_capture.json.gz')


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += round(seconds * 1_000_000_000)


class Replay:
    def __init__(self, capture):
        self.records = {r['tag']: bytes.fromhex(r['rawHex']) for r in capture['records']}
        self.calls = []
        self.overrides = {}

    def raw(self, loc):
        self.calls.append(loc.path)
        if loc.path in self.overrides:
            return self.overrides[loc.path]
        data = self.records[loc.source]
        if loc.row['atomic'] == 0xC1 and not loc.row['struct']:
            return bytes([bool(data[loc.offset + loc.bit // 8] >> (loc.bit % 8) & 1)])
        return data[loc.offset:loc.offset + loc.width]


class Rows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = reader.load_json(CAPTURE)
        cls.expected = reader.snapshot(deepcopy(cls.capture))

    def setUp(self):
        self.clock = Clock()
        self.replay = Replay(self.capture)
        self.counter_calls = []

        def counters(symbol):
            self.counter_calls.append(symbol)
            return 0 if len(self.counter_calls) == 1 else 2
        self.subject = live.CanonicalRowReader(self.capture, self.replay.raw, counters,
                                              clock_ns=self.clock, sleep=self.clock.sleep)

    def test_every_sealed_native_leaf_resolves_and_decodes_exactly(self):
        self.assertEqual(len(self.expected['values']), 5264)
        for path, expected in self.expected['values'].items():
            with self.subTest(path=path):
                location = self.subject.location(path)
                value, kind = self.subject._decode(location, self.replay.raw(location))
                self.assertEqual(type(value), type(expected))
                self.assertEqual(value, expected)
                self.assertEqual(kind, self.expected['types'][path])

    def test_live_values_come_from_io_not_the_bootstrap_capture(self):
        path = 'Press/Status/FaultActive'
        self.replay.overrides[path] = bytes([not self.expected['values'][path]])
        result = self.subject.read_row([path])
        self.assertEqual(result['values'], {path: not self.expected['values'][path]})
        self.assertEqual(result['protocol'], 1)
        self.assertEqual(self.replay.calls, [path])

    def test_every_occupied_leaf_passes_the_complete_row_and_count_proof(self):
        for path, value in self.expected['values'].items():
            self.counter_calls.clear()
            with self.subTest(path=path):
                result = self.subject.read_row([path])
                self.assertEqual(result['values'], {path: value})
                self.assertEqual(result['types'], {path: self.expected['types'][path]})

    def test_owner_header_is_one_row_and_requires_independent_progress(self):
        paths = ['Press/Status/Name', 'Press/Status/State']
        result = self.subject.read_row(paths)
        self.assertEqual(result['protocol'], 2)
        self.assertEqual(result['values'], {p: self.expected['values'][p] for p in paths})
        self.assertNotEqual(self.counter_calls[0], self.counter_calls[1])

    def test_mixed_owners_and_unknown_paths_refuse_before_io(self):
        for paths in (['Press/Status/Name', 'Press/Status/FaultActive'],
                      ['Press/HmiRequest/Secret'], ['Press/Missing'], []):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                self.subject.read_row(paths)
        self.assertEqual(self.counter_calls, [])
        self.assertEqual(self.replay.calls, [])

    def test_torn_attempt_does_not_leak_its_values(self):
        counters = iter([0, 2, 4, 4, 4])
        self.subject._counter = lambda unused: next(counters)
        calls = []
        def raw(loc):
            calls.append(loc.path)
            return bytes([len(calls) == 1])
        self.subject._raw = raw
        result = self.subject.read_row(['Press/Status/FaultActive'])
        self.assertEqual(result['attempts'], 2)
        self.assertFalse(result['values']['Press/Status/FaultActive'])

    def test_frozen_scan_or_owner_progress_never_returns_values(self):
        for path in ('Press/Status/FaultActive', 'Press/Status/Name'):
            self.subject._counter = lambda unused: 2
            with self.subTest(path=path), self.assertRaises(live.CoherenceUnavailable) as failure:
                self.subject.read_row([path])
            self.assertEqual(failure.exception.attempts, 20)
            self.assertFalse(hasattr(failure.exception, 'values'))

    def test_odd_revisions_recover_but_invalid_counters_refuse(self):
        counters = iter([0, 1, 2, 2])
        self.subject._counter = lambda unused: next(counters)
        self.assertEqual(self.subject.read_row(['Press/Status/FaultActive'])['attempts'], 2)
        for value in (-1, 1 << 31, True, None):
            self.subject._counter = lambda unused, value=value: value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'counter'):
                self.subject.read_row(['Press/Status/FaultActive'])

    def test_odd_initial_progress_can_recover_without_accepting_a_frozen_scan(self):
        counters = iter([1, 2, 2, 2, 4, 4])
        self.subject._counter = lambda unused: next(counters)
        self.assertEqual(self.subject.read_row(['Press/Status/FaultActive'])['attempts'], 2)

    def test_forward_progress_across_wrap_is_allowed_but_backward_is_not(self):
        counters = iter([2147483646, 2, 2])
        self.subject._counter = lambda unused: next(counters)
        self.assertEqual(self.subject.read_row(['Press/Status/FaultActive'])['revision'], 2)
        self.assertFalse(live._later(2, 4))
        self.assertFalse(live._later(2, 2))

    def test_protocol_one_strict_scan_window_is_not_increased(self):
        original = self.subject._raw
        def slow(loc):
            self.clock.now += 10_000_000
            return original(loc)
        self.subject._raw = slow
        with self.assertRaises(live.CoherenceUnavailable):
            self.subject.read_row(['Press/Status/FaultActive'])

    def test_protocol_two_can_span_scans_within_its_published_window(self):
        original = self.subject._raw
        def slow(loc):
            self.clock.now += 20_000_000
            return original(loc)
        self.subject._raw = slow
        result = self.subject.read_row(['Press/Status/Name'])
        self.assertEqual(result['proofWindowNs'], 20_000_000)

    def test_deadline_stops_further_io_and_returns_no_values(self):
        def stalled(loc):
            self.clock.now += 1_000_000_000
            return self.replay.raw(loc)
        self.subject._raw = stalled
        with self.assertRaises(live.CoherenceUnavailable):
            self.subject.read_row(['Press/Status/FaultActive', 'Press/Status/Diagnostic/TimeSynchronized'])
        self.assertEqual(len(self.replay.calls), 1)

    def test_decode_time_is_included_in_total_acquisition_age(self):
        original = self.subject._decode
        def slow(*args):
            self.clock.now += 1_000_000_000
            return original(*args)
        self.subject._decode = slow
        with self.assertRaisesRegex(live.CoherenceUnavailable, 'deadline'):
            self.subject.read_row(['Press/Status/FaultActive'])

    def test_array_counts_are_read_inside_the_same_proof(self):
        # Pick a real occupied native row; descriptors supply its sibling count.
        path = next(p for p in self.expected['values']
                    if self.subject.location(p).requirements)
        location = self.subject.location(path)
        count, ordinal, capacity = location.requirements[-1]
        result = self.subject.read_row([path])
        self.assertEqual(result['values'][path], self.expected['values'][path])
        self.assertIn(count, self.replay.calls)
        self.replay.overrides[count] = struct.pack('<i', ordinal)
        self.counter_calls.clear()
        with self.assertRaisesRegex(ValueError, 'not occupied'):
            self.subject.read_row([path])
        self.replay.overrides[count] = struct.pack('<i', capacity + 1)
        self.counter_calls.clear()
        with self.assertRaisesRegex(ValueError, 'capacity'):
            self.subject.read_row([path])

    def test_array_indices_and_string_implementation_members_are_not_guessed(self):
        for path in ('Press/ActiveSteps[-1]/StepNo', 'Press/Status/Name/LEN',
                     'Press/ActiveSteps[100000]/StepNo',
                     'Press/SupportedModesPublished[00]', 'Press/SupportedModesPublished[-0]'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.subject.read_row([path])
        self.assertEqual(self.replay.calls, [])

    def test_bad_scalar_bytes_and_nonfinite_replies_refuse(self):
        self.replay.overrides['Press/Status/FaultActive'] = b''
        with self.assertRaisesRegex(ValueError, 'length'):
            self.subject.read_row(['Press/Status/FaultActive'])
        path = next(p for p, kind in self.expected['types'].items() if kind == 'Float')
        loc = self.subject.location(path)
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            self.subject._decode(loc, struct.pack('<f', float('nan')))

    def test_malformed_manifest_never_opens_a_row_reader(self):
        capture = deepcopy(self.capture)
        capture['manifest']['valid'] = False
        with self.assertRaises(ValueError):
            live.CanonicalRowReader(capture, self.replay.raw, lambda unused: 2)

    def test_import_graph_contains_no_station_or_legacy_projection(self):
        program = ('import sys; import fraktal_ab_canonical_live; '
                   'assert not set(sys.modules) & {"fraktal_ab_station", "fraktal_ab_generate", '
                   '"fraktal_ab_projection", "fraktal_ab_gateway", "fraktal_ab_declaration"}')
        result = subprocess.run([sys.executable, '-c', program], cwd=Path(__file__).parent,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class Discovery(unittest.TestCase):
    def comm(self, serial='0x601fc87b', tags=()):
        return NS(GetDeviceProperties=lambda: NS(Status='Success', Value=NS(SerialNumber=serial)),
                  GetTagList=lambda **unused: NS(Status='Success', Value=list(tags)), UDT={})

    def test_only_absent_manifest_allows_legacy_selection(self):
        self.assertIsNone(reader.open_row_reader(self.comm(), expect_serial='601FC87B'))

    def test_wrong_serial_stops_before_symbol_discovery(self):
        comm = self.comm(serial='0x12345678')
        comm.GetTagList = lambda **unused: self.fail('discovery reached after wrong serial')
        with self.assertRaisesRegex(ValueError, 'serial'):
            reader.open_row_reader(comm, expect_serial='601FC87B')

    def test_ambiguous_header_never_falls_back(self):
        from fraktal_ab_canonical_manifest import TYPE_HEADER
        template = NS(Name='Header', Fields=[NS(TagName=n, DataType=None, Bytes=struct.pack('<HHI', 0, 0xC4, i*4))
                              for i, n in enumerate(sorted(TYPE_HEADER))])
        comm = self.comm(tags=[NS(TagName='Header', Struct=True, Array=0, DataTypeValue=42)] * 2)
        comm.UDT = {42: template}
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            reader.open_row_reader(comm, expect_serial='601FC87B')

    def test_present_invalid_manifest_never_falls_back(self):
        from fraktal_ab_canonical_manifest import TYPE_HEADER
        template = NS(Name='Header', Fields=[
            NS(TagName=n, DataType=None, Bytes=struct.pack('<HHI', 0, 0xC4, i*4))
            for i, n in enumerate(sorted(TYPE_HEADER))])
        comm = self.comm(tags=[NS(TagName='Header', Struct=True, Array=0, DataTypeValue=42)])
        comm.UDT = {42: template}
        with patch.object(live, 'read_document', side_effect=ValueError('invalid canonical manifest')):
            with self.assertRaisesRegex(ValueError, 'invalid canonical'):
                reader.open_row_reader(comm, expect_serial='601FC87B')


class Wire(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = reader.load_json(CAPTURE)

    def setUp(self):
        self.replay = Replay(self.capture)
        self.layout = live.CanonicalRowReader(self.capture, self.replay.raw, lambda unused: 2)
        objects, unused = reader.template_objects(self.capture['templates'])
        from fraktal_ab_canonical_manifest import TYPE_HEADER
        header = next(h for h, t in objects.items()
                      if TYPE_HEADER <= {r['name'] for r in reader.member_table(t)})
        self.comm = NS(UDT=objects,
                       GetDeviceProperties=lambda: NS(Status='Success', Value=NS(SerialNumber='0x601FC87B')),
                       GetTagList=lambda **unused: NS(Status='Success', Value=[
                           NS(TagName='Header', Struct=True, Array=0, DataTypeValue=header)]),
                       _build_ioi=lambda symbol, kind: symbol,
                       _add_read_service=lambda ioi, count: ioi)
        self.locations, self.messages, self.counter_calls = {}, [], []
        self.packet_change = lambda packet: packet
        self.status = 0
        def send(symbol):
            self.messages.append(symbol)
            loc = self.locations[symbol]
            if loc.row['struct']:
                wire_type = struct.pack('<HH', 0x02A0, loc.row['handle'])
            else:
                wire_type = struct.pack('<H', loc.row['atomic'])
            packet = bytes(46) + bytes([0xCC, 0, 0, 0]) + wire_type + self.replay.raw(loc)
            return self.status, self.packet_change(packet)
        self.comm.conn = NS(send=send)
        def read(symbol):
            self.counter_calls.append(symbol)
            return NS(Status='Success', Value=0 if len(self.counter_calls) == 1 else 2)
        self.comm.Read = read
        with patch.object(live, 'read_document', return_value=(None, self.capture)), \
                patch.object(live, 'template_structure_handle', side_effect=lambda comm, h: h):
            self.subject = reader.open_row_reader(self.comm, expect_serial='601FC87B')

    def use(self, path):
        loc = self.layout.location(path)
        self.locations[loc.symbol] = loc
        return loc

    def test_connected_scalar_and_string_replies_match_native_bytes(self):
        for path in ('Press/Status/Name', 'Press/Status/State', 'Press/Status/FaultActive'):
            loc = self.use(path)
            actual = self.subject._decode(loc, self.subject._raw(loc))
            expected = self.layout._decode(loc, self.replay.raw(loc))
            self.assertEqual(actual, expected)
        self.assertEqual(len(self.messages), 3)

    def test_wrong_service_status_type_and_lengths_are_refused(self):
        loc = self.use('Press/Status/FaultActive')
        changes = [lambda p: p[:46], lambda p: p[:46] + b'\xcd' + p[47:],
                   lambda p: p[:48] + b'\x01' + p[49:],
                   lambda p: p[:50] + b'\xc4\x00' + p[52:],
                   lambda p: p[:-1], lambda p: p + b'\x00']
        for change in changes:
            self.packet_change = change
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.subject._raw(loc)
        self.status = 6
        with self.assertRaisesRegex(ValueError, 'read failed'):
            self.subject._raw(loc)

    def test_wrong_string_handle_is_refused_before_decoding(self):
        loc = self.use('Press/Status/Name')
        self.packet_change = lambda p: p[:52] + b'\x00\x00' + p[54:]
        with self.assertRaisesRegex(ValueError, 'type mismatch'):
            self.subject._raw(loc)

    def test_symbolic_bool_read_does_not_reuse_the_packed_record_bit_number(self):
        loc = self.use('Press/Status/FaultActive')
        self.replay.overrides[loc.path] = b'\xff'
        result = self.subject.read_row([loc.path])
        self.assertTrue(result['values'][loc.path])


if __name__ == '__main__':
    unittest.main()

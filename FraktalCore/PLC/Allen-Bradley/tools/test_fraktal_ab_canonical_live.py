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
        self.subject = live.CanonicalRowReader(self.capture, live.LeafBody(self.replay.raw), counters,
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
        self.subject._body = live.LeafBody(raw)
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
        def slow(loc):
            self.clock.now += 10_000_000
            return self.replay.raw(loc)
        self.subject._body = live.LeafBody(slow)
        with self.assertRaises(live.CoherenceUnavailable):
            self.subject.read_row(['Press/Status/FaultActive'])

    def test_protocol_two_can_span_scans_within_its_published_window(self):
        def slow(loc):
            self.clock.now += 20_000_000
            return self.replay.raw(loc)
        self.subject._body = live.LeafBody(slow)
        result = self.subject.read_row(['Press/Status/Name'])
        self.assertEqual(result['proofWindowNs'], 20_000_000)

    def test_deadline_stops_further_io_and_returns_no_values(self):
        def stalled(loc):
            self.clock.now += 1_000_000_000
            return self.replay.raw(loc)
        self.subject._body = live.LeafBody(stalled)
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

    def test_body_is_planned_once_before_any_proof_and_outside_its_window(self):
        events, body = [], live.LeafBody(self.replay.raw)
        def plan(locations):
            events.append('plan')
            self.clock.now += 50_000_000  # far beyond the 10 ms protocol-1 window
            return live.LeafBody.plan(body, locations)
        body.plan = plan
        self.subject._body = body
        counters = iter([0, 2, 4, 4, 4])  # first attempt torn, second coherent
        self.subject._counter = lambda unused: events.append('counter') or next(counters)
        result = self.subject.read_row(['Press/Status/FaultActive'])
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(events[:2], ['plan', 'counter'])
        self.assertEqual(events.count('plan'), 1)
        self.assertLess(result['proofWindowNs'], 10_000_000)

    def test_plan_that_drops_or_repeats_a_leaf_refuses_before_io(self):
        paths = ['Press/Status/Name', 'Press/Status/State']
        for change in (lambda packets: packets[:1], lambda packets: packets + packets[:1]):
            body = live.LeafBody(self.replay.raw)
            body.plan = lambda locations, change=change: change(live.LeafBody.plan(body, locations))
            self.subject._body = body
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'cover'):
                self.subject.read_row(paths)
        self.assertEqual((self.counter_calls, self.replay.calls), ([], []))

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
            live.CanonicalRowReader(capture, live.LeafBody(self.replay.raw), lambda unused: 2)

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


class Controller:
    """Answers connected Read Tag requests, plain or MSP, from sealed native bytes.

    It accepts only read services, and holds every request and reply to the
    connection size, sequence count included.
    """
    def __init__(self, replay, capacity):
        from pylogix import PLC
        self.encoder, self.replay, self.capacity = PLC(), replay, capacity
        # Only the encoders are used; pylogix creates its sockets eagerly.
        self.encoder.conn.Socket.close()
        self.encoder.conn.msg_socket.close()
        self.symbols, self.requests = {}, []
        self.item_change, self.frame_change, self.status = {}, (lambda frame: frame), 0
        self.on_send = lambda: None

    def register(self, location):
        self.symbols[self.encoder._build_ioi(location.symbol, 0xC4)] = location

    def _location(self, service):
        words = service[1]
        if service[0] != 0x4C or service[2 + 2 * words:] != b'\x01\x00':
            raise AssertionError('controller fake received a non-read service')
        return self.symbols[bytes(service[2:2 + 2 * words])]

    def _item(self, location):
        row = location.row
        wire = struct.pack('<HH', 0x02A0, row['handle']) if row['struct'] \
            else struct.pack('<H', row['atomic'])
        item = b'\xcc\x00\x00\x00' + wire + self.replay.raw(location)
        return self.item_change.get(location.path, lambda unused: unused)(item)

    def send(self, request):
        self.on_send()
        if 2 + len(request) > self.capacity:
            raise AssertionError('request exceeds the connection size')
        if request[:6] == live.MSP_HEADER:
            count = struct.unpack_from('<H', request, 6)[0]
            body = request[6:]
            offsets = list(struct.unpack_from('<%dH' % count, body, 2)) + [len(body)]
            locations = [self._location(body[a:b]) for a, b in zip(offsets, offsets[1:])]
            items = [self._item(location) for location in locations]
            at, starts = 2 + 2 * count, []
            for item in items:
                starts.append(at)
                at += len(item)
            payload = b'\x8a\x00\x00\x00' + struct.pack('<%dH' % (1 + count), count, *starts) \
                + b''.join(items)
        else:
            locations = [self._location(request)]
            payload = self._item(locations[0])
        if 2 + len(payload) > self.capacity:
            raise AssertionError('reply exceeds the connection size')
        self.requests.append(tuple(location.path for location in locations))
        return self.status, self.frame_change(bytes(46) + payload)


class Wire(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = reader.load_json(CAPTURE)
        cls.expected = reader.snapshot(deepcopy(cls.capture))
        cls.layout = live.CanonicalRowReader(cls.capture, live.LeafBody(None), lambda unused: 2)
        cls.objects, unused = reader.template_objects(cls.capture['templates'])

    def setUp(self):
        self.open(4002)

    def open(self, capacity):
        from fraktal_ab_canonical_manifest import TYPE_HEADER
        header = next(h for h, t in self.objects.items()
                      if TYPE_HEADER <= {r['name'] for r in reader.member_table(t)})
        self.replay = Replay(self.capture)
        self.controller = Controller(self.replay, min(capacity, 4002))
        for path in self.expected['values']:
            self.controller.register(self.layout.location(path))
        self.comm = NS(UDT=self.objects, ConnectionSize=capacity, conn=self.controller,
                       GetDeviceProperties=lambda: NS(Status='Success', Value=NS(SerialNumber='0x601FC87B')),
                       GetTagList=lambda **unused: NS(Status='Success', Value=[
                           NS(TagName='Header', Struct=True, Array=0, DataTypeValue=header)]),
                       _build_ioi=self.controller.encoder._build_ioi,
                       _add_read_service=self.controller.encoder._add_read_service)
        self.counter_calls, self.clock = [], Clock()
        def read(symbol):
            self.counter_calls.append(symbol)
            return NS(Status='Success', Value=0 if len(self.counter_calls) == 1 else 2)
        self.comm.Read = read
        with patch.object(live, 'read_document', return_value=(None, self.capture)), \
                patch.object(live, 'template_structure_handle', side_effect=lambda comm, h: h):
            self.subject = reader.open_row_reader(self.comm, expect_serial='601FC87B')
        self.subject._clock, self.subject._sleep = self.clock, self.clock.sleep

    def read(self, location):
        body = self.subject._body
        packet, = body.plan((location,))
        return body.parse(packet, body.send(packet))[0]

    def row(self, paths):
        self.counter_calls.clear()
        return self.subject.read_row(paths)

    def owners(self):
        rows = {}
        for path in self.expected['values']:
            rows.setdefault(self.layout._binding(path), []).append(path)
        return rows.values()

    def test_lone_scalar_and_string_replies_keep_the_plain_request(self):
        for path in ('Press/Status/Name', 'Press/Status/State', 'Press/Status/FaultActive'):
            loc = self.layout.location(path)
            self.assertEqual(self.subject._decode(loc, self.read(loc)),
                             self.layout._decode(loc, self.replay.raw(loc)))
        self.assertEqual(self.controller.requests, [('Press/Status/Name',), ('Press/Status/State',),
                                                    ('Press/Status/FaultActive',)])

    def test_every_sealed_leaf_replays_exactly_through_bounded_packets(self):
        for capacity in (4002, 500):
            self.open(capacity)
            for paths in self.owners():
                with self.subTest(capacity=capacity, owner=paths[0]):
                    before = len(self.controller.requests)
                    result = self.row(paths)
                    self.assertEqual(result['values'], {p: self.expected['values'][p] for p in paths})
                    self.assertEqual(result['types'], {p: self.expected['types'][p] for p in paths})
                    sent = self.controller.requests[before:]
                    self.assertEqual(result['packets'], len(sent))
                    # The fake names a shared packed word by one leaf, so
                    # compare read totals with logical leaves, counts once each.
                    read = [p for request in sent for p in request]
                    counts = {c for p in paths for c, *unused in self.layout.location(p).requirements}
                    self.assertEqual(len(read), len(set(paths) | counts))
                    self.assertTrue(all(read.count(c) == 1 for c in counts))
                    self.assertLessEqual(max(map(len, sent)), 64)
                    if len(paths) > 64:
                        self.assertLess(len(sent), len(paths) / 2)

    def test_connection_budget_caps_reads_and_bytes(self):
        flags = [p for p, kind in self.expected['types'].items() if kind == 'Boolean'
                 and self.layout._binding(p)[0] == 'FRK_Press_CanonicalGeneration'][:200]
        result = self.row(flags)
        # 64 is Dart's cipMaximumBatchReads; these short flags fit the bytes.
        self.assertEqual(max(map(len, self.controller.requests)), 64)
        self.assertEqual(result['packets'], 4)
        for capacity in (499, None, '4000'):
            self.comm.ConnectionSize = capacity
            self.controller.requests.clear()
            with self.subTest(capacity=capacity), self.assertRaisesRegex(ValueError, 'connection size'):
                self.row(flags)
            self.assertEqual((self.controller.requests, self.counter_calls), ([], []))

    def test_a_leaf_that_cannot_fit_alone_refuses_at_planning(self):
        loc = self.layout.location('Press/Status/Name')
        sizes = dict(self.subject._body._sizes)
        sizes[loc.row['handle']] = 495  # 6 + 4 + 495 exceeds a 500-byte connection
        self.comm.ConnectionSize = 500
        body = live.PacketBody(self.comm, sizes, self.subject._body._handles)
        with self.assertRaisesRegex(ValueError, 'connection budget'):
            body.plan((loc,))

    def test_wrong_service_status_type_and_lengths_are_refused(self):
        loc = self.layout.location('Press/Status/FaultActive')
        changes = [lambda p: p[:46], lambda p: p[:46] + b'\xcd' + p[47:],
                   lambda p: p[:48] + b'\x01' + p[49:],
                   lambda p: p[:50] + b'\xc4\x00' + p[52:],
                   lambda p: p[:-1], lambda p: p + b'\x00']
        for change in changes:
            self.controller.frame_change = change
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.read(loc)
        self.controller.frame_change, self.controller.status = (lambda p: p), 6
        with self.assertRaisesRegex(ValueError, 'read failed'):
            self.read(loc)

    def test_wrong_string_handle_is_refused_before_decoding(self):
        loc = self.layout.location('Press/Status/Name')
        self.controller.frame_change = lambda p: p[:52] + b'\x00\x00' + p[54:]
        with self.assertRaisesRegex(ValueError, 'type mismatch'):
            self.read(loc)

    def test_multi_service_reply_defects_are_refused(self):
        paths = ['Press/Status/Name', 'Press/Status/State', 'Press/Status/ConfigRev']
        frame_changes = [
            lambda f: f[:48] + b'\x1e' + f[49:],                      # partial failure
            lambda f: f[:50] + b'\x02\x00' + f[52:],                   # count differs
            lambda f: f[:52] + b'\x07\x00' + f[54:],                   # first offset
            lambda f: f[:54] + f[52:54] + f[56:],                      # repeated offset
            lambda f: f[:-1], lambda f: f + b'\x00', lambda f: f[:51]]
        item_changes = [
            ('Press/Status/State', lambda i: i[:2] + b'\x05' + i[3:]),  # embedded status
            ('Press/Status/State', lambda i: i[:4] + b'\xc3\x00' + i[6:]),
            ('Press/Status/Name', lambda i: i[:6] + b'\x00\x00' + i[8:])]
        for change in frame_changes:
            self.controller.frame_change = change
            with self.subTest(frame=change), self.assertRaises(ValueError):
                self.row(paths)
        self.controller.frame_change = lambda f: f
        for path, change in item_changes:
            self.controller.item_change = {path: change}
            with self.subTest(item=path), self.assertRaises(ValueError):
                self.row(paths)
        self.controller.item_change = {}
        self.assertEqual(set(self.row(paths)['values']), set(paths))

    def test_malformed_reply_refuses_even_from_a_torn_attempt(self):
        # Owner progress, revision before/after (torn), progress: a retry would follow.
        counters = iter([0, 2, 4, 2])
        self.subject._counter = lambda unused: next(counters)
        self.controller.frame_change = lambda f: f[:-1]
        with self.assertRaisesRegex(ValueError, 'length') as failure:
            self.subject.read_row(['Press/Status/Name', 'Press/Status/State'])
        self.assertNotIsInstance(failure.exception, live.CoherenceUnavailable)
        self.assertEqual(len(self.controller.requests), 1)

    def test_deadline_stops_further_packets(self):
        self.open(500)
        paths = [p for p in self.expected['values']
                 if self.layout._binding(p)[0] == 'FRK_Press_ConfigViewRevision'][:40]
        self.controller.on_send = lambda: setattr(self.clock, 'now', self.clock.now + 1_000_000_000)
        with self.assertRaises(live.CoherenceUnavailable):
            self.row(paths)
        self.assertEqual(len(self.controller.requests), 1)

    def test_symbolic_bool_read_does_not_reuse_the_packed_record_bit_number(self):
        loc = self.layout.location('Press/Status/FaultActive')
        self.replay.overrides[loc.path] = b'\xff'
        result = self.row([loc.path])
        self.assertTrue(result['values'][loc.path])


if __name__ == '__main__':
    unittest.main()

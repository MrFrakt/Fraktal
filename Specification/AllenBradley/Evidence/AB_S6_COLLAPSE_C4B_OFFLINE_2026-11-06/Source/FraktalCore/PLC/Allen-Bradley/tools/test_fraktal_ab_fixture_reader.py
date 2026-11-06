"""O10 co-reading: native fixture bytes and canonical leaves share one proof."""
from copy import deepcopy
import struct
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_live as live
from test_fraktal_ab_canonical_live import CAPTURE, Clock, Replay

SYMBOL = 'FRK_Press_FixtureObservation'
HANDLE = 2047


def fixture_capture():
    capture = reader.load_json(CAPTURE)
    assert HANDLE not in {t['handle'] for t in capture['templates']}
    fields = []
    for name, count, offset in (('Unit_Running', 0, 0), ('Door_DoneCount', 0, 4),
                                ('Chart_Visited', 32, 8)):
        code = 0x20c4 if count else 0xc4
        fields.append(dict(name=name, info=count, code=code, offset=offset, atomic=0xc4,
                           struct=False, handle=0xc4, array=int(bool(count)), typeName='DINT'))
    capture['templates'].append(dict(handle=HANDLE, name='FRK_T_PressFixtureObservationV1',
                                     byteSize=136, members=fields))
    capture['symbols'].append(dict(name=SYMBOL, handle=HANDLE, arrayRank=0))
    return capture


class FixtureReads(unittest.TestCase):
    def setUp(self):
        self.capture = fixture_capture()
        self.clock = Clock()
        self.replay = Replay(self.capture)
        self.raw = struct.pack('<34i', 1, -17, *range(32))
        self.calls, self.counter_calls = [], []
        def raw(location):
            self.calls.append(location.path)
            return self.raw if location.symbol == SYMBOL else self.replay.raw(location)
        def counter(symbol):
            self.counter_calls.append(symbol)
            return 0 if len(self.counter_calls) == 1 else 2
        self.subject = live.CanonicalRowReader(self.capture, live.LeafBody(raw), counter,
                                              clock_ns=self.clock, sleep=self.clock.sleep)

    def test_private_fields_are_decoded_from_their_template_and_never_canonical(self):
        path = 'Press/CurrentStep/StepNo'
        result = self.subject.read_row([path], private=[SYMBOL])
        self.assertEqual(result['private'], {SYMBOL: dict(Unit_Running=1, Door_DoneCount=-17,
                                                          Chart_Visited=list(range(32)))})
        self.assertEqual(set(result['values']), {path})
        self.assertIn('#' + SYMBOL, self.calls)
        self.assertNotIn(SYMBOL, result['values'])
        self.assertEqual(result['protocol'], 1)

    def test_private_fixture_forces_scan_proof_for_a_header_owner_field(self):
        result = self.subject.read_row(['Press/PartSlide/Status/State'], private=[SYMBOL])
        self.assertEqual(result['protocol'], 1)
        self.assertEqual(set(self.counter_calls), {'FRK_Press_CanonicalGeneration'})

    def test_private_fields_do_not_gain_the_one_second_owner_window(self):
        original = self.subject._body._raw
        def slow(location):
            self.clock.now += 10_000_000
            return original(location)
        self.subject._body._raw = slow
        with self.assertRaises(live.CoherenceUnavailable):
            self.subject.read_row(['Press/Status/State'], private=[SYMBOL])

    def test_torn_fixture_does_not_leak_into_the_accepted_result(self):
        sequence = iter((0, 2, 4, 4, 4))
        self.subject._counter = lambda unused: next(sequence)
        original = self.subject._body._raw
        def changed(location):
            if location.symbol == SYMBOL:
                self.raw = struct.pack('<34i', 2 if self.calls else 99, 3, *range(32))
            return original(location)
        self.subject._body._raw = changed
        result = self.subject.read_row(['Press/CurrentStep/StepNo'], private=[SYMBOL])
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(result['private'][SYMBOL]['Unit_Running'], 2)

    def test_frozen_progress_never_publishes_private_values(self):
        self.subject._counter = lambda unused: 2
        with self.assertRaises(live.CoherenceUnavailable) as failure:
            self.subject.read_row(['Press/CurrentStep/StepNo'], private=[SYMBOL])
        self.assertFalse(hasattr(failure.exception, 'private'))

    def test_missing_public_command_and_arbitrary_structures_refuse_before_io(self):
        for symbol in ('Press', 'FRK_Press_ConfigRead', 'missing', 'Bad.Name',
                       self.capture['manifest']['commandBindings'][0]['PayloadSymbol']):
            with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                self.subject.read_row(['Press/CurrentStep/StepNo'], private=[symbol])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.counter_calls, [])

    def test_duplicate_private_selection_refuses_before_io(self):
        with self.assertRaises(ValueError):
            self.subject.read_row(['Press/CurrentStep/StepNo'], private=[SYMBOL, SYMBOL])
        self.assertEqual(self.counter_calls, [])

    def test_wrong_fixture_version_or_extent_refuses_before_io(self):
        for change in ('version', 'extent', 'overlap'):
            capture = deepcopy(self.capture)
            template = capture['templates'][-1]
            if change == 'version':
                template['name'] += 'Changed'
            elif change == 'extent':
                template['byteSize'] -= 4
            else:
                template['members'][1]['offset'] = 0
            subject = live.CanonicalRowReader(capture, self.subject._body, self.subject._counter)
            with self.subTest(change=change), self.assertRaises(ValueError):
                subject.read_row(['Press/CurrentStep/StepNo'], private=[SYMBOL])
        self.assertEqual(self.calls, [])

    def test_truncated_private_body_is_refused(self):
        self.raw = self.raw[:-4]
        with self.assertRaisesRegex(ValueError, 'length'):
            self.subject.read_row(['Press/CurrentStep/StepNo'], private=[SYMBOL])

    def test_packet_planning_fetches_the_fixture_handle_before_any_counter(self):
        location = self.subject._private(SYMBOL)
        comm = NS(ConnectionSize=500, _build_ioi=lambda symbol, kind: b'\x91\x02XX',
                  _add_read_service=lambda ioi, count: b'\x4c\x02' + ioi + b'\x01\x00')
        body = live.PacketBody(comm, self.subject._sizes, {})
        with patch.object(live, 'template_structure_handle', return_value=0x4321) as lookup:
            packets = body.plan(iter([location]))
            body.plan([location])
        self.assertEqual(len(packets), 1)
        lookup.assert_called_once_with(comm, HANDLE)
        self.assertEqual(self.counter_calls, [])
        frame = bytes(46) + struct.pack('<BBBBHH', 0xcc, 0, 0, 0, 0x02a0, 0x4321) + self.raw
        self.assertEqual(body.parse(packets[0], frame), (self.raw,))

    def test_private_field_members_are_not_available_as_canonical_paths(self):
        with self.assertRaises(ValueError):
            self.subject.location(SYMBOL + '/Unit_Running')


if __name__ == '__main__':
    unittest.main()

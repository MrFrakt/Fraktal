"""Part/genealogy acquisition: native replay, strict bounds and unchanged guards.

Replay counters are apparatus seams. The controller bytes are from the sealed
S6 host session; these tests do not claim native coherence on a new image.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import json
import struct
import unittest
from unittest.mock import Mock, patch

import fraktal_ab_canonical_live as live
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_publication as publication
import fraktal_ab_fixture_reads as views
import fraktal_ab_fixture_observation as observation
import fraktal_ab_genealogy_s6_collapse_demo as profile
import fraktal_ab_part_execute as fixture
import fraktal_ab_st_model as st
from test_fraktal_ab_canonical_live import Clock, Replay

ROOT = Path(__file__).resolve().parents[4]
SESSION = ROOT/'Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04/Session'
APP = profile.application()


class CanonicalPart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = reader.load_json(SESSION/'capture_canonical.json.gz')
        cls.expected = reader.snapshot(deepcopy(cls.capture))['values']
        cls.batch = json.loads((SESSION/'capture_legacy.json').read_bytes())

    def setUp(self):
        self.clock, self.replay, self.counters = Clock(), Replay(self.capture), []
        def counter(_):
            self.counters.append(1)
            return 0 if len(self.counters) == 1 else 2
        row_reader = live.CanonicalRowReader(self.capture, live.LeafBody(self.replay.raw), counter,
                                            clock_ns=self.clock, sleep=self.clock.sleep)
        read_row = row_reader.read_row
        def fresh(*args, **kwargs):
            self.counters.clear()
            return read_row(*args, **kwargs)
        row_reader.read_row = fresh
        self.session = views.FixtureReads(APP, row_reader)
        self.bound = patch.object(views, '_session', return_value=self.session)
        self.bound.start()
        self.addCleanup(self.bound.stop)

    def test_part_result_is_the_native_canonical_tree_including_timestamp(self):
        actual = views.part_values(object(), app=APP)
        expected = {path[len(APP.name)+1:]: value for path, value in self.expected.items()
                    if path.startswith(APP.name+'/Part/')}
        self.assertEqual(actual, expected)
        self.assertIs(type(actual['Part/Result/Stamp']), type(expected['Part/Result/Stamp']))

    def test_identity_wait_reads_only_its_two_leaves(self):
        self.assertEqual(views.part_identity(object(), app=APP),
                         dict(Present=self.expected['Press/Part/Present'], Uid=self.expected['Press/Part/Uid']))
        self.assertEqual(set(self.replay.calls), {'Press/Part/Present', 'Press/Part/Uid'})

    def test_manifest_pin_is_a_fresh_read_over_native_templates(self):
        subject = self.session.reader
        observed, digest = [], ['A'*64]
        def raw(location):
            name = location.path.rsplit('/', 1)[1]
            observed.append(name)
            if name == 'ContentHash':
                data = digest[0].encode()
                return struct.pack('<i', len(data)) + data + bytes(location.width - 4 - len(data))
            return bytes([int(name == 'Valid')])
        subject._body = live.LeafBody(raw)
        self.assertEqual(subject.manifest_identity(), dict(Valid=1, Truncated=0, ContentHash=digest[0]))
        digest[0] = 'B'*64
        self.assertEqual(subject.manifest_identity()['ContentHash'], digest[0])
        self.assertEqual(observed, ['Valid', 'Truncated', 'ContentHash'] * 2)

    def test_manifest_pin_refuses_missing_and_ambiguous_headers(self):
        from fraktal_ab_canonical_manifest import manifest_candidates
        subject = self.session.reader
        headers = manifest_candidates(list(subject._symbols.values()), self.capture['templates'])
        self.assertEqual(len(headers), 1)
        symbol = subject._symbols.pop(headers[0]['name'])
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            subject.manifest_identity()
        subject._symbols[symbol['name']] = symbol
        subject._symbols['OtherHeader'] = dict(symbol, name='OtherHeader')
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            subject.manifest_identity()

    def test_host_batch_equals_the_two_native_bracketing_batches(self):
        actual = views.host_events(object(), app=APP)
        self.assertEqual(actual, self.batch['first'])
        self.assertEqual(actual, self.batch['second'])

    def test_unoccupied_host_rows_are_not_acquired(self):
        original = views.values
        def partial(comm, paths, **kw):
            # A nonwrapped two-event counterexample over the sealed native
            # slot bodies. This occupancy mutation is apparatus, not evidence
            # of a native two-event ring.
            result = original(comm, paths, **kw)
            for name, value in dict(Head=2, Count=2, NewestSequence=2, Wrapped=False,
                                    DataRevision=4, RingHead=2).items():
                result['Press/HostEvents/' + name] = value
            for slot in (1, 2):
                path = f'Press/HostEvents/Ring[{slot}]/Sequence'
                if path in result:
                    result[path] = slot
            return result
        with patch.object(views, 'values', side_effect=partial):
            actual = views.host_events(object(), app=APP)
        meta = actual['metadata']
        occupied = {(meta['Head']-meta['Count']+i)%meta['Capacity']+1 for i in range(meta['Count'])}
        for path in self.replay.calls:
            if '/HostEvents/Ring[' in path:
                slot = int(path.split('/Ring[', 1)[1].split(']', 1)[0])
                self.assertIn(slot, occupied)

    def test_malformed_record_is_refused_instead_of_dropped(self):
        # Corrupt one occupied record in the decoded seam; no row can be
        # dropped to manufacture a valid sequence interval.
        original = views.values
        def corrupt(comm, paths, **kw):
            result = original(comm, paths, **kw)
            for path in result:
                if '/HostEvents/Ring[' in path and path.endswith('/Kind'):
                    result[path] = 99
                    break
            return result
        with patch.object(views, 'values', side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, 'semantics'):
                views.host_events(object(), app=APP)

    def test_changed_planning_headers_exhaust_the_original_three_attempts(self):
        original, calls = views.values, []
        def changed(comm, paths, **kw):
            result = original(comm, paths, **kw)
            calls.append(1)
            if len(calls) % 2 == 0:
                result['Press/HostEvents/DataRevision'] += 2
            return result
        with patch.object(views, 'values', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'every bounded'):
                views.host_events(object(), app=APP)
        self.assertEqual(len(calls), 6)

    def test_no_extended_host_attempt_budget_is_accepted(self):
        for count in (0, 4, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                views.host_events(object(), app=APP, attempts=count)


class CanonicalImageGuard(unittest.TestCase):
    def test_every_primitive_write_rechecks_native_identity_and_manifest_hash(self):
        identity = NS(SerialNumber='0x601FC87B', ProductName='Emulate 5580 Controller', Revision='38.11')
        row_reader = Mock()
        row_reader.manifest_identity.return_value = dict(Valid=True, Truncated=False, ContentHash='A'*64)
        state = NS(_fraktal_fixture_reads=NS(reader=row_reader))
        native = Mock(IPAddress='127.0.0.1', ProcessorSlot=0, conn=state)
        native.GetDeviceProperties.return_value = NS(Status='Success', Value=identity)
        native.Write.return_value = NS(Status='Success')
        with patch.object(publication, 'manifest_values', return_value={'ContentHash': 'A'*64}):
            comm = fixture.Guarded(native, 0x601FC87B, APP)
        target = next(iter(fixture.gen.externally_writable(APP)))
        comm.Write(target, 0)
        row_reader.manifest_identity.return_value = dict(Valid=True, Truncated=False, ContentHash='B'*64)
        with self.assertRaisesRegex(fixture.FixtureRefused, 'manifest pin'):
            comm.Write(target, 1)
        self.assertEqual(native.GetDeviceProperties.call_count, 2)
        native.Write.assert_called_once_with(target, 0)


class PrivateCopy(unittest.TestCase):
    def test_every_accounted_private_fact_copies_exact_native_dints(self):
        self.assertEqual(observation.validate(APP), [])
        facts = observation.facts(APP)
        self.assertEqual(len(facts), 13)
        surfaces = observation._surfaces(APP)
        tags = {source: st.structure(members) for members, source in surfaces.values()}
        tags[observation.tag(APP)] = st.structure(observation.records(APP)[0].members)
        tags[observation.index_tag(APP)] = 0
        expected = {}
        # Copy-only hostile DINT patterns, not valid access/session states.
        for index, (surface, member, name, source) in enumerate(facts):
            value = ([(-2**31 + i) if i % 2 else (2**31 - 1 - i) for i in range(member.dimension)]
                     if member.dimension else -2**31 + index)
            tags[source][member.name] = value
            expected[name] = deepcopy(value)
        st.Controller(tags).run('\n'.join(observation.logic(APP)))
        self.assertEqual(tags[observation.tag(APP)], expected)


if __name__ == '__main__':
    unittest.main()

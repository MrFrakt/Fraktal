"""Bounded native acknowledgement reads preserve coherence and replay guards."""

import asyncio
import struct
import threading
import unittest
from unittest import mock
from types import SimpleNamespace

import fraktal_ab_gateway as gw
import fraktal_ab_projection as projection
import fraktal_ab_manifest_read as manifest_reader
import fraktal_ab_mailbox as mailbox
from test_fraktal_ab_gateway import _doc
from test_fraktal_ab_s9 import batch
from test_fraktal_ab_projection import good_header


class NativeControlReads(unittest.TestCase):
    def setUp(self):
        self.plan = projection.ReadPlan()
        self.header = good_header()
        self.plan.manifest = (self.header, {'Localization': [
            {'NumericKey': 77, 'PortableKey': 'fixture.refused'}]})
        self.calls = []
        self.headers = [self.header, self.header]
        self.comm = SimpleNamespace(Read=self.scalar)

    def scalar(self, tag):
        self.calls.append(tag)
        return SimpleNamespace(Status='Success', Value=-1)

    def raw(self, comm, tag):
        self.calls.append(tag)
        if tag == mailbox.response_tag_name(projection.APP):
            return struct.pack('<iii', -1, 0, 77), 'Success', 0
        return b'header', 'Success', 0

    def read(self):
        with mock.patch.object(manifest_reader, '_read_raw', side_effect=self.raw), \
             mock.patch.object(manifest_reader, 'decode_header', side_effect=self.headers):
            return projection.read_mailbox_document(self.comm, self.plan)

    def test_one_native_response_unsigned_sequences_and_controller_catalogue(self):
        values = self.read()['values']
        root = projection.APP.name
        self.assertEqual(values[f'{root}/HmiResponse/AckSequence'], 0xffffffff)
        self.assertEqual(values[f'{root}/HmiRequest/Sequence'], 0xffffffff)
        self.assertFalse(values[f'{root}/HmiResponse/Accepted'])
        self.assertEqual(values[f'{root}/HmiResponse/Diagnostic'], 'fixture.refused')
        self.assertEqual(len(values), 4)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.calls.count(mailbox.response_tag_name(projection.APP)), 1)
        self.assertFalse(any('Report' in tag for tag in self.calls))

    def test_changed_leading_header_refuses_before_reading_response(self):
        changed = {**self.header, 'ConfigRevision': self.header['ConfigRevision'] + 1}
        self.headers = [changed, changed]
        with self.assertRaises(projection.ProjectionRefused):
            self.read()
        self.assertEqual(len(self.calls), 1)

    def test_changed_trailing_header_cannot_publish_a_torn_answer(self):
        self.headers = [self.header, {**self.header,
            'ConfigRevision': self.header['ConfigRevision'] + 1}]
        with self.assertRaises(projection.ProjectionRefused):
            self.read()

    def test_short_response_is_a_failure(self):
        with mock.patch.object(manifest_reader, '_read_raw', return_value=(b'1234', 'Success', 0)):
            with self.assertRaises(projection.ReadFailed):
                projection.read_mailbox(self.comm, include_report=False)


class _Reader:
    def __init__(self):
        self.snapshots = 0
        self.controls = 0
        self.sequence, self.ack = 4, 4
        self.fail = False
        self.active = False
        self.mailbox_paths = frozenset(f'Press/{leaf}' for leaf in projection.MAILBOX_CONTROL_LEAVES)

    def __call__(self):
        self.snapshots += 1
        return _doc(self.values())

    def values(self):
        return {'Press/HmiRequest/Sequence': self.sequence,
                'Press/HmiResponse/AckSequence': self.ack,
                'Press/HmiResponse/Accepted': True,
                'Press/HmiResponse/Diagnostic': ''}

    def mailbox(self):
        if self.active:
            raise AssertionError('native reader was entered concurrently')
        self.active = True
        try:
            self.controls += 1
            if self.fail:
                raise OSError('fixture native read failed')
            return {'values': self.values()}
        finally:
            self.active = False


class GatewayControlReads(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.reader = _Reader()
        self.writer = mock.Mock(return_value=True)
        self.station = gw.Station(self.reader, cache_ttl=100)
        self.gateway = gw.Gateway(self.station, write_token='fixture',
            write_roots=frozenset({'Press'}), write_fn=self.writer)
        self.state = gw._ConnState()
        self.state.authenticated = True
        await self.gateway._snapshot(self.state)

    async def test_targeted_ack_uses_fresh_control_read_and_keeps_complete_cache(self):
        paths, revision, old = list(self.station.paths), self.station.revision, self.station._doc
        self.reader.ack = 5
        result = await self.gateway._read_values(self.state, dict(revision=revision,
            indices=[paths.index('Press/HmiResponse/AckSequence')]))
        self.assertEqual(result['Press/HmiResponse/AckSequence'], 5)
        self.assertEqual((self.reader.snapshots, self.reader.controls), (1, 1))
        self.assertIs(self.station._doc, old)
        self.assertEqual(self.station.paths, paths)
        self.assertEqual(self.station.revision, revision)

    async def test_pending_request_refuses_even_when_full_snapshot_was_cached(self):
        self.reader.sequence = 5
        with self.assertRaises(gw.WriteRefused):
            await self.gateway._write_batch(self.state, batch(6))
        self.writer.assert_not_called()
        self.assertEqual(self.reader.controls, 1)

    async def test_fresh_native_sequence_seeds_guard_without_a_snapshot(self):
        self.reader.sequence = self.reader.ack = 8
        with self.assertRaises(gw.WriteRefused):
            await self.gateway._write_batch(self.state, batch(8))
        self.writer.assert_not_called()
        self.assertTrue(await self.gateway._write_batch(self.state, batch(9)))
        self.assertEqual(self.reader.snapshots, 1)
        self.assertEqual(self.gateway._mailbox_sequences['Press/HmiRequest'], 9)

    async def test_failed_control_read_discards_cached_good_and_never_writes(self):
        self.reader.fail = True
        with self.assertRaises(OSError):
            await self.gateway._write_batch(self.state, batch(5))
        self.writer.assert_not_called()
        self.assertIsNone(self.station._doc)
        self.assertFalse(self.station.healthy)

    async def test_partial_success_cannot_restore_full_station_health(self):
        self.station._healthy = False
        self.station.last_refusal = 'fixture failed full station read'
        await self.station.mailbox_document()
        self.assertFalse(self.station.healthy)
        self.assertEqual(self.station.last_refusal, 'fixture failed full station read')

    async def test_stale_discovery_and_other_paths_do_not_use_partial_read(self):
        with self.assertRaises(gw.StaleRevision):
            await self.gateway._read_values(self.state, dict(revision=0, indices=[0]))
        await self.gateway._read_values(self.state, dict(revision=self.station.revision,
            indices=[self.station.paths.index('Press/ModeActivePublished')]))
        self.assertEqual(self.reader.controls, 0)

    async def test_control_reads_share_snapshot_lock(self):
        async with self.station._lock:
            task = asyncio.create_task(self.station.mailbox_document())
            await asyncio.sleep(0)
            self.assertEqual(self.reader.controls, 0)
        await task
        self.assertEqual(self.reader.controls, 1)

    async def test_cancelled_read_keeps_native_lock_until_thread_finishes(self):
        entered, release = threading.Event(), threading.Event()
        def blocked():
            entered.set()
            release.wait(2)
            return {'values': self.reader.values()}
        self.reader.mailbox = blocked
        task = asyncio.create_task(self.station.mailbox_document())
        await asyncio.to_thread(entered.wait, 2)
        task.cancel()
        await asyncio.sleep(0)
        self.assertTrue(self.station._lock.locked())
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(self.station._lock.locked())


class CleanupReads(unittest.TestCase):
    def test_validated_none_cleanup_does_not_allocate_a_native_connection(self):
        writer = gw.MailboxWriter('fixture', 0, '7036B510')
        with mock.patch('pylogix.PLC', side_effect=AssertionError('unexpected connection')):
            self.assertTrue(writer([(projection.APP.name + '/HmiRequest/Kind', 'int32', mailbox.NONE)], None))
            with self.assertRaises(gw.WriteRefused):
                writer([('Other/HmiRequest/Kind', 'int32', mailbox.NONE)], None)

    def test_reconnect_clears_manifest_before_any_partial_read(self):
        reader = gw.build_reader('fixture', 0, '7036B510')
        old = mock.Mock()
        reader.plc = old
        reader.plan.manifest = ({'fixture': 1}, {})
        reader._drop()
        with mock.patch.object(reader, '_open', return_value=mock.Mock()), \
             mock.patch.object(projection, 'read_document', return_value=_doc()) as complete, \
             mock.patch.object(projection, 'read_mailbox_document') as partial:
            self.assertEqual(reader.mailbox()['schema'], 'fraktal.ab.projection')
        old.Close.assert_called_once()
        complete.assert_called_once()
        partial.assert_not_called()


if __name__ == '__main__':
    unittest.main()

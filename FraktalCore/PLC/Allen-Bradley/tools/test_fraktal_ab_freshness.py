"""Deployment expiry is independent of RPC completion and partial Ack reads."""
import asyncio
from dataclasses import replace
import threading
import unittest
from unittest import mock

import fraktal_ab_declaration as decl
import fraktal_ab_gateway as gw
import fraktal_ab_projection as projection
from test_fraktal_ab_gateway import _doc, _authed, _Writes
from test_fraktal_ab_s9 import batch

BUDGET = decl.ReadBudget(500, 250, 2000, 3000, 1000, 2000, 3000)
PATH = 'Press/Probe'


class BudgetTests(unittest.TestCase):
    def test_invalid_limits_are_rejected_before_use(self):
        for changed in (dict(cache_ms=500), dict(fast_good_ms=500),
                        dict(fast_expiry_ms=2000), dict(slow_good_ms=1000),
                        dict(poll_period_ms=True), dict(connection_bytes=499)):
            bad = replace(BUDGET, **changed)
            self.assertTrue(bad.validate())
            with self.assertRaises(ValueError):
                gw.Station(lambda: _doc(), budget=bad)
        self.assertEqual(BUDGET.validate(), [])

    def test_native_reader_uses_declared_connection_before_identity_io(self):
        reader = gw._NativeReader('fixture', 0, 'fixture', 0)
        with mock.patch('pylogix.PLC') as plc, mock.patch.object(projection, 'verify_serial') as identity:
            def verify(comm, serial):
                self.assertEqual(comm.ConnectionSize, projection.APP.read_budget.connection_bytes)
                return serial, True
            identity.side_effect = verify
            reader._open()


class FreshnessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tick = 10.0
        self.doc = _doc({PATH: 42, 'Press/HmiRequest/Sequence': 0,
                         'Press/HmiResponse/AckSequence': 0})
        self.station = gw.Station(lambda: self.doc, clock=lambda: self.tick, budget=BUDGET)

    async def test_cache_hits_preserve_acquisition_and_advance_age(self):
        first = await self.station.document()
        self.tick += .1
        second = await self.station.document()
        self.assertEqual(first['dataValues'][PATH]['serverTimestampUs'],
                         second['dataValues'][PATH]['serverTimestampUs'])
        self.assertAlmostEqual(second['sampleAgeMs'], 100)
        self.assertAlmostEqual(second['dataValues'][PATH]['ageMs'], 100)
        self.assertEqual(first['dataValues'][PATH]['ageMs'], 0)

    async def test_late_and_expired_values_are_retained_only_as_metadata(self):
        await self.station.document()
        for seconds, status, reason in ((2, 0x40000000, 'read-late'), (3, 0x80000000, 'read-expired')):
            self.tick = 10 + seconds
            aged = self.station._aged(self.station._doc)
            self.assertNotIn(PATH, aged['values'])
            self.assertEqual(aged['dataValues'][PATH]['value'], 42)
            self.assertEqual(aged['dataValues'][PATH]['status'], status)
            self.assertEqual(aged['dataValues'][PATH]['qualityReason'], reason)
            self.assertFalse(self.station.healthy)
        fresh = await self.station.document(force=True)
        self.assertTrue(self.station.healthy)
        self.assertEqual(fresh['values'][PATH], 42)

    async def test_health_expires_while_a_worker_remains_blocked(self):
        await self.station.document()
        entered, release = threading.Event(), threading.Event()
        def blocked():
            entered.set()
            release.wait(2)
            return self.doc
        self.station._read_fn = blocked
        task = asyncio.create_task(self.station.document(force=True))
        try:
            while not entered.is_set():
                await asyncio.sleep(.001)
            self.tick += 3
            self.assertFalse(task.done())
            self.assertFalse(self.station.healthy)
        finally:
            release.set()
        returned = await task
        self.assertFalse(self.station.healthy, 'a delayed complete read is not fresh on completion')
        self.assertEqual(returned['dataValues'][PATH]['status'], 0x80000000)

    async def test_partial_ack_cannot_restore_expired_station(self):
        await self.station.document()
        partial = lambda: {'values': {'Press/HmiResponse/AckSequence': 0}}
        self.station._read_fn.mailbox = partial
        self.tick += 3
        await self.station.mailbox_document()
        self.assertFalse(self.station.healthy)
        self.assertEqual(self.station._sample_ts, 10)

    async def test_slow_metadata_ages_from_group_acquisition(self):
        self.doc['dataValues'][PATH] = dict(value=42, status=0, tier='slow', ageMs=2100)
        document = await self.station.document()
        self.assertTrue(self.station.healthy)
        self.assertNotIn(PATH, document['values'])
        self.assertEqual(document['dataValues'][PATH]['status'], 0x40000000)

    async def test_existing_bad_quality_is_never_promoted(self):
        self.doc['dataValues'][PATH] = dict(value=42, status=0x80320000, tier='fast', ageMs=0)
        result = await self.station.document()
        self.assertEqual(result['dataValues'][PATH]['status'], 0x80320000)
        self.assertNotIn(PATH, result['values'])

    async def test_utc_clock_jump_does_not_renew_monotonic_freshness(self):
        first = await self.station.document()
        self.tick += 2
        with mock.patch.object(gw.time, 'time_ns', return_value=1):
            self.assertFalse(self.station.healthy)
            aged = self.station._aged(self.station._doc)
        self.assertEqual(aged['dataValues'][PATH]['serverTimestampUs'],
                         first['dataValues'][PATH]['serverTimestampUs'])
        self.assertNotIn('sourceTimestampUs', aged['dataValues'][PATH])

    async def test_connection_page_cannot_revive_late_read_values(self):
        self.doc['configPages'] = {2: {PATH: 43}}
        await self.station.document()
        # A deliberately delayed refresh is coherent but no longer Good.
        def late():
            self.tick += 2.1
            return self.doc
        self.station._read_fn = late
        self.tick += 3
        gateway, state = gw.Gateway(self.station), _authed()
        state.config_model = 2
        result = await gateway._read_values(state, dict(revision=self.station.revision,
            indices=[self.station.paths.index(PATH)]))
        self.assertIsNone(result[PATH])

    async def test_late_full_preflight_refuses_without_delivery_or_reservation(self):
        await self.station.document()
        def late():
            self.tick += 2.1
            return self.doc
        self.station._read_fn = late
        self.tick += 3
        writes = _Writes()
        gateway = gw.Gateway(self.station, write_token='fixture', allow_all_root_mailboxes=True, write_fn=writes)
        with self.assertRaises(gw.WriteRefused):
            await gateway._write_batch(_authed(), batch(1))
        self.assertEqual(writes.calls, [])
        self.assertEqual(gateway._mailbox_sequences, {})

    async def test_command_delivery_rechecks_after_native_queue_wait(self):
        await self.station.document()
        writes = _Writes()
        gateway = gw.Gateway(self.station)
        self.tick += 2
        with self.assertRaises(gw.WriteRefused):
            await gateway._run_fresh_writer(writes, [], 'Press/HmiRequest')
        self.assertEqual(writes.calls, [])
        await self.station.document(force=True)
        self.assertTrue(await gateway._run_fresh_writer(writes, [], 'Press/HmiRequest'))

    async def test_read_failure_invalidates_cached_good_immediately(self):
        await self.station.document()
        def failed():
            raise OSError('fixture disconnect')
        self.station._read_fn = failed
        with self.assertRaises(OSError):
            await self.station.document(force=True)
        self.assertFalse(self.station.healthy)
        self.assertIsNone(self.station._doc)


class NativeTierTests(unittest.TestCase):
    def test_heartbeat_and_group_age_are_measured_before_io(self):
        tick, reads = [0.0], []
        plan = projection.ReadPlan(clock=lambda: tick[0], budget=replace(BUDGET, slow_period_ms=1500))
        plan.set_tiers([PATH], [], [PATH])
        def read():
            reads.append(tick[0])
            tick[0] += .1
            return 42
        plan.group('probe', ('Press/Probe',), read)
        doc = plan.metadata(dict(values={PATH: 42}, dataValues={}))
        self.assertAlmostEqual(doc['dataValues'][PATH]['ageMs'], 100)
        tick[0] = 1.4
        plan.group('probe', ('Press/Probe',), read)
        self.assertEqual(len(reads), 1)
        tick[0] = 1.5
        plan.group('probe', ('Press/Probe',), read)
        self.assertEqual(len(reads), 2)
        plan.set_tiers([], [PATH], [PATH])
        tick[0] = 4
        plan.group('probe', ('Press/Probe',), read)
        self.assertEqual(len(reads), 2)
        plan.targeted([PATH])
        plan.group('probe', ('Press/Probe',), read)
        self.assertEqual(len(reads), 3)

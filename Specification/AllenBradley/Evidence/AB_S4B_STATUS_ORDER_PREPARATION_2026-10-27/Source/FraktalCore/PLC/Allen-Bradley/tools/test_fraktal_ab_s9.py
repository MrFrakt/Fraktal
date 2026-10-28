"""S9 offline: real generated decoder/handler plus the production gateway.

No network or hardware I/O. Native packet planning uses the installed pylogix
serializer; the controller model executes emitted ST, including CPS and wiping.
"""

import asyncio
import copy
import threading
import unittest
from unittest import mock
from types import SimpleNamespace

import fraktal_ab_gateway as gw
import fraktal_ab_mailbox as mb
import fraktal_ab_mailbox_frame as frame
import fraktal_ab_generate as gen
import fraktal_ab_access as access
import fraktal_ab_projection as projection
from fraktal_ab_declaration import ReadBudget
import fraktal_ab_st_model as st
from test_fraktal_ab_manual import APP, Bench, REQUEST, RESPONSE
from test_fraktal_ab_gateway import _doc


class NativeBench:
    def __init__(self):
        self.bench = Bench()
        self.tags = self.bench.tags
        self.tags[gen.alarm_ring_tag(APP)] = st.structure(gen.alarm_ring_members())
        self.tags[f'FRK_{APP.name}_NowDate'] = 0
        self.tags[f'FRK_{APP.name}_NowTime'] = 0
        self.tags[REQUEST]['Frame'] = {'Words': [0] * frame.word_count(APP)}
        import fraktal_ab_sets as sets
        self.tags[REQUEST]['ConfigSet'] = st.structure(sets.request_members())
        self.tags[access.tag(APP, 'LoginRequest')] = copy.deepcopy(self.tags[REQUEST])
        self.tags[frame.sample_tag(APP)] = {'Words': [0] * frame.word_count(APP)}
        for name in ('Cursor', 'Word', 'Byte', 'Valid', 'Field'):
            self.tags[f'FRK_{APP.name}_HmiFrame{name}'] = 0
        self.tags[access.tag(APP, 'State')]['CurrentLevel'] = access.ADMIN
        self.decoder = st.parse('\n'.join(frame.logic(APP)))
        self.calls, self.acks = [], []
        self.ConnectionSize = 500

    def scan(self):
        before = self.tags[RESPONSE]['AckSequence']
        self.bench.plc.run(self.decoder)
        self.bench.scan()
        after = self.tags[RESPONSE]['AckSequence']
        if before != after:
            self.acks.append(after & 0xffffffff)

    def Write(self, path, value):
        self.calls.append(('write', path))
        parts = path.split('.')
        holder = self.tags
        for part in parts[:-1]:
            holder = holder[part]
        last = parts[-1]
        if '[' in last:
            name, index = last.rstrip(']').split('[')
            index = int(index)
            holder[name][index:index + len(value)] = value
        else:
            holder[last] = list(value) if isinstance(value, list) else value
        self.scan()  # deliberately interleave a scan after every primitive write
        return SimpleNamespace(Status='Success')

    def Read(self, path, count=None):
        value = self.tags
        for part in path.split('.'):
            value = value[part]
        return SimpleNamespace(Status='Success', Value=value)

    def GetDeviceProperties(self):
        self.calls.append(('identity', '7036B510'))
        return SimpleNamespace(Status='Success', Value=SimpleNamespace(SerialNumber='7036B510'))

    def doc(self):
        return _doc({'Press/HmiRequest/Sequence': self.tags[REQUEST]['Sequence'] & 0xffffffff,
                     'Press/HmiResponse/AckSequence': self.tags[RESPONSE]['AckSequence'] & 0xffffffff})

    def issue(self, sequence, **args):
        for path, value in mb.command_writes(APP, mb.SET_SESSION_TIMEOUT, sequence, **args):
            self.Write(path, value)


def batch(sequence, duration=1000):
    return {'writes': [dict(path='Press/HmiRequest/' + n, valueType=t, value=v)
                      for n, t, v in [('Kind', 'int32', mb.SET_SESSION_TIMEOUT),
                                      ('DurationMs', 'uint32', duration),
                                      ('Sequence', 'uint32', sequence)]]}


class FrameTests(unittest.TestCase):
    def test_login_frame_is_sampled_and_all_transport_secret_copies_are_wiped(self):
        from test_fraktal_ab_access import APP as test_app, USER, PIN, add_access, finish
        native = NativeBench()
        add_access(native.bench.plc, test_app)
        native.bench.handler = st.parse('\n'.join(mb.handler_logic(test_app)))
        native.tags[access.tag(APP, 'LoginRequest')] = copy.deepcopy(native.tags[REQUEST])
        for path, value in mb.command_writes(APP, mb.LOGIN, 1, User=USER.name, Secret=PIN.decode()):
            native.Write(path, value)
        self.assertEqual(native.tags[RESPONSE]['Accepted'], 1)
        held = finish(native.bench.plc, test_app)
        self.assertEqual((held['CurrentLevel'], held['LoginFailed']), (4, 0))
        self.assertEqual(held['LoginResultSequence'], 1)
        for tag in (REQUEST, access.tag(APP, 'LoginRequest')):
            self.assertFalse(any(native.tags[tag]['Secret']['DATA']))
            self.assertFalse(any(native.tags[tag]['Frame']['Words']))
        self.assertFalse(any(native.tags[frame.sample_tag(APP)]['Words']))

    def test_whole_request_is_one_unfragmented_native_packet_at_500(self):
        from pylogix import PLC
        comm = PLC()
        comm.ConnectionSize = 500
        path = frame.native_path(APP)
        words = frame.encode(APP, dict(Kind=mb.LOGIN, User='fixture', TextValue='a' * 64, Sequence=1))
        chunks = comm._convert_write_data(path, 0xc4, words)
        self.assertEqual(len(chunks), 1)
        wire = comm._add_write_service(comm._build_ioi(path, 0xc4), words, 0xc4)
        self.assertLessEqual(len(wire) + 2, 500)
        self.addCleanup(comm.Close)
        self.assertEqual(len(comm._convert_write_data(path, 0xc4, words + [0])), 2)

    def test_total_string_bound_and_each_member_bound_refuse_before_io(self):
        limit = frame.argument_bytes(APP)
        with self.assertRaises(ValueError):
            frame.encode(APP, dict(Sequence=1, TargetPath='a' * 255, TextValue='b' * (limit - 254)))
        with self.assertRaises(ValueError):
            frame.encode(APP, dict(Sequence=1, User='a' * 33))
        with self.assertRaises(ValueError):
            frame.encode(APP, dict(Sequence=1, TextValue='é'))

    def test_round_trip_and_uint32_wrap_are_the_generated_decoder(self):
        for seq in (0x7fffffff, 0x80000000, 0xffffffff, 0):
            with self.subTest(sequence=seq):
                native = NativeBench()
                native.tags[f'FRK_{APP.name}_HmiLastSequence'] = frame.signed((seq - 1) & 0xffffffff)
                native.tags[REQUEST]['Sequence'] = frame.signed((seq - 1) & 0xffffffff)
                native.tags[RESPONSE]['AckSequence'] = frame.signed((seq - 1) & 0xffffffff)
                planned = mb.command_writes(APP, mb.SET_SESSION_TIMEOUT, seq, DurationMs=1000)
                self.assertEqual(planned[-1][1], seq if seq < 0x80000000 else seq - 0x100000000)
                self.assertEqual(planned[0][1][-1], planned[-1][1])
                native.issue(seq, DurationMs=1000, User='fixture', Secret='fixture-secret')
                self.assertEqual(native.acks, [seq])
                self.assertEqual(native.tags[RESPONSE]['Accepted'], 1)
                self.assertEqual(native.tags[access.tag(APP, 'State')]['SessionTimeout'], 1000)
                self.assertEqual(native.tags[REQUEST]['Secret']['DATA'], [0] * mb.SECRET_LENGTH)
                self.assertEqual(native.tags[REQUEST]['Frame']['Words'], [0] * frame.word_count(APP))
                self.assertEqual(native.tags[frame.sample_tag(APP)]['Words'], [0] * frame.word_count(APP))

    def test_partial_payload_and_early_commit_refuse_without_late_execution(self):
        native = NativeBench()
        words = frame.encode(APP, dict(Kind=mb.SET_SESSION_TIMEOUT, DurationMs=1000, Sequence=1))
        for cursor in range(len(words) - 1):
            native.tags[REQUEST]['Frame']['Words'][cursor] = words[cursor]
            native.scan()
        self.assertEqual(native.acks, [])
        native.Write(REQUEST + '.Sequence', 1)
        self.assertEqual(native.tags[RESPONSE]['Accepted'], 0)
        native.Write(frame.native_path(APP), words)
        for _ in range(3):
            native.scan()
        self.assertEqual(native.acks, [1])
        self.assertNotEqual(native.tags[access.tag(APP, 'State')]['SessionTimeout'], 1000)
        native.issue(2, DurationMs=2000)
        self.assertEqual(native.tags[access.tag(APP, 'State')]['SessionTimeout'], 2000)

    def test_out_of_order_arguments_are_safe_when_commit_is_last(self):
        native = NativeBench()
        words = frame.encode(APP, dict(Kind=mb.SET_SESSION_TIMEOUT, DurationMs=1000, Sequence=1))
        for index in reversed(range(len(words))):
            native.tags[REQUEST]['Frame']['Words'][index] = words[index]
            native.scan()
        self.assertEqual(native.acks, [])
        native.Write(REQUEST + '.Sequence', 1)
        self.assertEqual(native.acks, [1])
        self.assertEqual(native.tags[RESPONSE]['Accepted'], 1)

    def test_corrupt_lengths_and_schema_refuse_without_array_fault(self):
        for index, value in [(0, 2), (5, -1), (5, 0x7fffffff), (5, 255), (8, 33)]:
            with self.subTest(index=index, value=value):
                native = NativeBench()
                words = frame.encode(APP, dict(Kind=mb.SET_SESSION_TIMEOUT, DurationMs=1000, Sequence=1))
                words[index] = value
                if index == 5 and value == 255:
                    words[6] = 160  # each length legal, aggregate illegal
                native.Write(frame.native_path(APP), words)
                native.Write(REQUEST + '.Sequence', 1)
                self.assertEqual(native.tags[RESPONSE]['Accepted'], 0)

    def test_exact_identity_precedes_each_primitive_write(self):
        native = NativeBench()
        writer = gw.MailboxWriter('fixture', 0, '7036B510', APP, set_store=object())
        values = [(w['path'], w['valueType'], w['value']) for w in batch(1)['writes']]
        self.assertTrue(writer._write_base(gw._GuardedConnection(native, '7036B510'), values))
        self.assertEqual([kind for kind, _ in native.calls], ['identity', 'write', 'identity', 'write'])

    def test_identity_change_after_payload_prevents_commit(self):
        native = NativeBench()
        original = native.GetDeviceProperties
        def identity():
            reply = original()
            if len(native.calls) > 1:
                reply.Value.SerialNumber = '00000000'
            return reply
        native.GetDeviceProperties = identity
        writer = gw.MailboxWriter('fixture', 0, '7036B510', APP, set_store=object())
        values = [(w['path'], w['valueType'], w['value']) for w in batch(1)['writes']]
        with self.assertRaises(gw.WriteRefused):
            writer._write_base(gw._GuardedConnection(native, '7036B510'), values)
        self.assertEqual(native.acks, [])


class CrashTests(unittest.IsolatedAsyncioTestCase):
    async def test_five_replay_boundaries_and_fresh_recovery(self):
        for boundary in ('payload-before-commit', 'commit-before-ack', 'ack-before-completion', 'stale-reconnect', 'wrap'):
            with self.subTest(boundary=boundary):
                native = NativeBench()
                initial = 0xffffffff if boundary == 'wrap' else 7
                native.tags[REQUEST]['Sequence'] = frame.signed(initial)
                native.tags[RESPONSE]['AckSequence'] = frame.signed(initial)
                native.tags[f'FRK_{APP.name}_HmiLastSequence'] = frame.signed(initial)
                seq = (initial + 1) & 0xffffffff
                failed = False
                def write(writes, mailbox):
                    nonlocal failed
                    values = {p.rsplit('/', 1)[-1]: v for p, _, v in writes}
                    planned = mb.command_writes(APP, values.pop('Kind'), values.pop('Sequence'), **values)
                    if not failed and boundary == 'payload-before-commit':
                        native.Write(*planned[0])
                        failed = True
                        raise OSError('fixture interruption')
                    for path, payload in planned:
                        native.Write(path, payload)
                    if not failed and boundary in ('commit-before-ack', 'ack-before-completion'):
                        failed = True
                        raise OSError('fixture interruption')
                    return True
                gateway = gw.Gateway(gw.Station(native.doc, cache_ttl=0), write_token='fixture', write_roots=frozenset({'Press'}), write_fn=write)
                state = gw._ConnState()
                state.authenticated = True
                if boundary in ('payload-before-commit', 'commit-before-ack', 'ack-before-completion'):
                    with self.assertRaises(OSError):
                        await gateway._write_batch(state, batch(seq))
                else:
                    self.assertTrue(await gateway._write_batch(state, batch(seq)))
                before = list(native.calls)
                with self.assertRaises(gw.WriteRefused):
                    await gateway._write_batch(state, batch(seq))
                self.assertEqual(native.calls, before)
                if boundary in ('stale-reconnect', 'payload-before-commit'):
                    gateway = gw.Gateway(gw.Station(native.doc), write_token='fixture', write_roots=frozenset({'Press'}), write_fn=write)
                    if boundary == 'stale-reconnect':
                        with self.assertRaises(gw.WriteRefused):
                            await gateway._write_batch(state, batch(seq))
                self.assertTrue(await gateway._write_batch(state, batch((seq + 1) & 0xffffffff, 2000)))
                self.assertEqual(len(native.acks), 1 if boundary == 'payload-before-commit' else 2)
                self.assertEqual(native.tags[access.tag(APP, 'State')]['SessionTimeout'], 2000)

    async def test_cancelled_native_worker_keeps_writer_lock_until_finished(self):
        entered, released = threading.Event(), threading.Event()
        def write(*_):
            entered.set()
            released.wait(2)
            return True
        gateway = gw.Gateway(gw.Station(lambda: _doc()), write_token='fixture', write_roots=frozenset({'Press'}), write_fn=write)
        state = gw._ConnState()
        state.authenticated = True
        task = asyncio.create_task(gateway._write_batch(state, batch(1)))
        await asyncio.to_thread(entered.wait, 2)
        task.cancel()
        await asyncio.sleep(.01)
        self.assertTrue(gateway._mailbox_lock.locked())
        released.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(gateway._mailbox_lock.locked())
        self.assertEqual(gateway._mailbox_sequences['Press/HmiRequest'], 1)

    async def test_reconnect_cannot_overwrite_a_committed_unacknowledged_frame(self):
        write = mock.Mock(return_value=True)
        doc = _doc({'Press/HmiRequest/Sequence': 8, 'Press/HmiResponse/AckSequence': 7})
        gateway = gw.Gateway(gw.Station(lambda: doc), write_token='fixture', write_roots=frozenset({'Press'}), write_fn=write)
        state = gw._ConnState()
        state.authenticated = True
        with self.assertRaises(gw.WriteRefused):
            await gateway._write_batch(state, batch(9))
        write.assert_not_called()

    async def test_failed_forced_read_cannot_return_cached_good(self):
        failing = False
        def read():
            if failing:
                raise OSError('fixture read failure')
            return _doc()
        station = gw.Station(read, cache_ttl=100)
        await station.document()
        failing = True
        with self.assertRaises(OSError):
            await station.document(force=True)
        with self.assertRaises(OSError):
            await station.document()
        self.assertFalse(station.healthy)

    async def test_tiers_intersect_all_viewers_and_targeted_read_forces_native(self):
        calls = []
        def read():
            return _doc({'Press/Profiler/HistoryHead': 1})
        read.set_tiers = lambda slow, excluded, paths: calls.append((set(slow), set(excluded)))
        targeted = []
        read.targeted = lambda paths: targeted.extend(paths)
        gateway = gw.Gateway(gw.Station(read))
        first, second = gw._ConnState(), gw._ConnState()
        await gateway._snapshot(first)
        await gateway._snapshot(second)
        index = gateway.station.paths.index('Press/Profiler/HistoryHead')
        args = dict(revision=gateway.station.revision, excluded=[index])
        await gateway._set_read_tiers(first, args)
        self.assertEqual(calls[-1], (set(), set()))  # unconfigured second viewer needs live
        await gateway._set_read_tiers(second, args)
        self.assertEqual(calls[-1][1], {'Press/Profiler/HistoryHead'})
        result = await gateway._read_values(first, dict(revision=gateway.station.revision, indices=[index]))
        self.assertEqual(result['Press/Profiler/HistoryHead'], 1)
        self.assertEqual(targeted, ['Press/Profiler/HistoryHead'])
        self.assertNotIn('Press/Profiler/HistoryHead', (await gateway._snapshot(first))['values'])

    async def test_quality_timestamp_and_config_overlay_share_the_same_value(self):
        doc = _doc({'Press/Probe': 1})
        doc['configPages'] = {2: {'Press/Probe': 2}}
        station = gw.Station(lambda: doc)
        gateway = gw.Gateway(station)
        state = gw._ConnState()
        state.config_model = 2
        snapshot = await gateway._snapshot(state)
        sample = snapshot['dataValues']['Press/Probe']
        self.assertEqual(sample['value'], 2)
        self.assertEqual(sample['status'], 0)
        self.assertGreater(int(sample['serverTimestampUs']), 0)
        self.assertNotIn('sourceTimestampUs', sample)
        self.assertEqual((await gateway._snapshot(state))['dataValues']['Press/Probe']['serverTimestampUs'], sample['serverTimestampUs'])

    async def test_detail_viewers_share_good_native_data_without_renewing_age(self):
        tick, calls, forced = [0.0], [], []
        def read():
            calls.append(tick[0])
            return _doc({'Press/Profiler/HistoryHead': 1})
        read.targeted = lambda paths: forced.extend(paths)
        station = gw.Station(read, cache_ttl=100, clock=lambda: tick[0],
                             budget=ReadBudget(500, 250, 2000, 3000, 1000, 2000, 3000))
        gateway, state = gw.Gateway(station), gw._ConnState()
        await gateway._snapshot(state)
        path = 'Press/Profiler/HistoryHead'
        state.excluded = frozenset({path})
        args = dict(revision=station.revision, indices=[station.paths.index(path)],
                    includeDataValues=True)
        tick[0] = .1
        first = await gateway._read_values(state, args)
        tick[0] = .2
        second = await gateway._read_values(state, args)
        self.assertEqual(first['values'][path], 1)
        self.assertEqual(second['dataValues'][path]['ageMs'], 200)
        self.assertEqual(first['dataValues'][path]['serverTimestampUs'],
                         second['dataValues'][path]['serverTimestampUs'])
        self.assertEqual(calls, [0.0])
        self.assertEqual(forced, [])
        self.assertEqual(station._sample_ts, 0.0)
        tick[0] = 3.1
        await gateway._read_values(state, args)
        self.assertEqual(len(calls), 2,
                         'expired cached detail must force a native refresh')
        self.assertEqual(forced, [])

    async def test_snapshot_processing_bracket_preserves_fresh_and_cached_age(self):
        tick = [0.0]
        def read():
            tick[0] += .1
            return _doc({'Press/Probe': 1})
        station = gw.Station(read, clock=lambda: tick[0],
            budget=ReadBudget(500, 250, 2000, 3000, 1000, 2000, 3000))
        gateway, state = gw.Gateway(station), gw._ConnState()
        fresh = await gateway._snapshot(state)
        self.assertAlmostEqual(fresh['sampleAgeMs'], 100)
        self.assertAlmostEqual(fresh['responseProcessingMs'], 100)
        self.assertNotIn('_agedAt', fresh)
        stamp = fresh['dataValues']['Press/Probe']['serverTimestampUs']
        tick[0] = .2
        cached = await gateway._snapshot(state)
        self.assertAlmostEqual(cached['sampleAgeMs'], 200)
        self.assertEqual(cached['responseProcessingMs'], 0)
        self.assertEqual(cached['dataValues']['Press/Probe']['serverTimestampUs'], stamp)
        self.assertEqual(station._sample_ts, 0.0)
        self.assertNotIn('_agedAt', cached)

    async def test_bad_detail_cannot_be_reused_or_revived_after_native_failure(self):
        fail, calls = [False], []
        def read():
            calls.append(1)
            if fail[0]:
                raise OSError('fixture native failure')
            doc = _doc({'Press/Profiler/HistoryHead': 1})
            doc['dataValues'] = {'Press/Profiler/HistoryHead':
                dict(value=1, status=0x80320000, ageMs=0, tier='slow')}
            return doc
        read.targeted = lambda paths: None
        station = gw.Station(read, cache_ttl=100,
                            budget=ReadBudget(500, 250, 2000, 3000, 1000, 2000, 3000))
        gateway, state = gw.Gateway(station), gw._ConnState()
        await gateway._snapshot(state)
        path = 'Press/Profiler/HistoryHead'
        state.excluded = frozenset({path})
        fail[0] = True
        with self.assertRaises(OSError):
            await gateway._read_values(state, dict(revision=station.revision,
                indices=[station.paths.index(path)], includeDataValues=True))
        self.assertEqual(len(calls), 2)
        self.assertFalse(station.healthy)
        self.assertIsNone(station._doc)

    async def test_partial_native_ack_has_quality_without_renewing_station(self):
        tick, calls = [0.0], []
        path = 'Press/HmiResponse/AckSequence'
        def read():
            calls.append('complete')
            return _doc({path: 0})
        def mailbox():
            calls.append('control')
            tick[0] += .1
            return {'values': {path: 7}}
        read.mailbox, read.mailbox_paths = mailbox, (path,)
        station = gw.Station(read, clock=lambda: tick[0],
            budget=ReadBudget(500, 250, 2000, 3000, 1000, 2000, 3000))
        gateway, state = gw.Gateway(station), gw._ConnState()
        await station.document()
        revision = station.revision
        tick[0] = 3.1
        reply = await gateway._read_values(state, dict(revision=revision,
            indices=[station.paths.index(path)], includeDataValues=True))
        self.assertEqual(reply['values'][path], 7)
        self.assertEqual(reply['dataValues'][path]['status'], 0)
        self.assertAlmostEqual(reply['dataValues'][path]['ageMs'], 100)
        self.assertEqual(calls, ['complete', 'control'])
        self.assertFalse(station.healthy)
        self.assertEqual(station._sample_ts, 0.0)
        self.assertEqual(station.revision, revision)


class WriteVectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_cost_vector_measures_native_exclusion_targeting_and_shared_viewers(self):
        import fraktal_ab_s9_read_execute as read_vector
        comm = mock.Mock()
        comm.Read.return_value = {'sample': 1}
        def document(counted, plan):
            counted.Read('core-context')
            plan.group('profiler', ('Press/Profiler/',), lambda: counted.Read('profiler-context'))
            return plan.metadata(_doc({'Press/Profiler/HistoryHead': 1}))
        with mock.patch.object(projection, 'read_document', side_effect=document):
            result = await read_vector.measure(comm, 2)
        self.assertFalse(result['wrote'])
        self.assertTrue(result['passed'])
        self.assertEqual(result['summary']['steady']['nativeReadCalls'], [2, 2])
        self.assertEqual(result['summary']['profiler-excluded']['nativeReadCalls'], [1, 1])
        self.assertEqual(result['summary']['profiler-targeted']['nativeReadCalls'], [2])
        self.assertEqual(result['summary']['profiler-slow']['nativeReadCalls'], [1, 1])
        self.assertEqual(result['summary']['six-viewer-burst']['nativeReadCalls'], [2, 2])

    async def test_supervised_hardware_vector_and_failure_restore_session_and_timeout(self):
        import fraktal_ab_s9_write_execute as vector
        import tempfile
        for fail in (False, True):
            with self.subTest(interrupted=fail):
                native = NativeBench()
                native.IPAddress, native.ProcessorSlot = 'fixture', 0
                state = native.tags[access.tag(APP, 'State')]
                state.update(UserLength=7, UserBytes=list(b'fixture') + [0] * 25, SessionTimeout=888888)
                account = dict(user='fixture', level=4, pin='test-only')
                class Client:
                    def __init__(self, *_):
                        pass
                    async def login(self, account):
                        state.update(CurrentLevel=account['level'], LoginFailed=0,
                                     UserLength=len(account['user']),
                                     UserBytes=list(account['user'].encode()) + [0] * (32 - len(account['user'])))
                        return {'accepted': True}, copy.deepcopy(state)
                    async def command(self, kind, **arguments):
                        sequence = (native.tags[REQUEST]['Sequence'] + 1) & 0xffffffff
                        for path, value in mb.command_writes(APP, kind, sequence, **arguments):
                            native.Write(path, value)
                        return {'accepted': bool(native.tags[RESPONSE]['Accepted'])}
                real_write = native.Write
                def write(path, value):
                    if fail and path.endswith('Words[0]'):
                        return SimpleNamespace(Status='fixture transport failure')
                    return real_write(path, value)
                native.Write = write
                evidence = {}
                with tempfile.TemporaryDirectory() as directory, \
                     mock.patch.object(vector.users, 'credentials', return_value={4: account}), \
                     mock.patch.object(vector.users, 'Client', Client), \
                     mock.patch.object(projection, 'read_access', side_effect=lambda *_: copy.deepcopy(state)), \
                     mock.patch.object(projection, 'read_document', side_effect=lambda *_: native.doc()):
                    await vector.vector(native, native, '7036B510', directory, evidence)
                self.assertTrue(evidence['cleanupPassed'], evidence.get('cleanup'))
                self.assertEqual(evidence['passed'], not fail)
                self.assertEqual(evidence['restored'], evidence['original'])
                if not fail:
                    self.assertEqual(len(evidence['rows']), 17)


class ReadPlanTests(unittest.TestCase):
    def test_native_exclusion_slow_heartbeat_targeted_and_fast_promotion(self):
        tick, reads = [0.0], []
        plan = projection.ReadPlan(clock=lambda: tick[0])
        paths = ['Press/Profiler/HistoryHead', 'Press/Profiler/LastWork']
        def read():
            reads.append(tick[0])
            return {'HistoryHead': len(reads)}
        prefixes = ('Press/Profiler/',)
        plan.set_tiers([], paths, paths)
        plan.group('profiler', prefixes, read)
        tick[0] = 2
        plan.group('profiler', prefixes, read)
        self.assertEqual(reads, [0])
        plan.forced = frozenset([paths[0]])
        plan.group('profiler', prefixes, read)
        plan.forced = frozenset()
        self.assertEqual(reads, [0, 2])
        plan.set_tiers(paths, [], paths)
        tick[0] = 2.9
        plan.group('profiler', prefixes, read)
        self.assertEqual(reads, [0, 2])
        tick[0] = 3
        plan.group('profiler', prefixes, read)
        self.assertEqual(reads, [0, 2, 3])
        plan.set_tiers([paths[0]], [], paths)  # one fast leaf keeps the whole record fast
        plan.group('profiler', prefixes, read)
        self.assertEqual(reads, [0, 2, 3, 3])

    def test_manifest_cache_requires_matching_trailing_header(self):
        import fraktal_ab_manifest_read as reader
        from test_fraktal_ab_projection import good_header
        header = good_header()
        plan = projection.ReadPlan()
        functions = ['read_mailbox', 'read_io', 'read_persist', 'read_records', 'read_models',
                     'read_alarm_log', 'read_oee', 'read_profiler', 'read_state_flags',
                     'read_system_health', 'read_access', 'read_data_access', 'read_line']
        from contextlib import ExitStack
        with ExitStack() as stack:
            for function in functions:
                stack.enter_context(mock.patch.object(projection, function, return_value=None))
            stack.enter_context(mock.patch('fraktal_ab_press_execute.read_unit', return_value={}))
            stack.enter_context(mock.patch('fraktal_ab_press_execute.read_chart', return_value={}))
            stack.enter_context(mock.patch('fraktal_ab_press_execute.read_module', return_value={}))
            stack.enter_context(mock.patch('fraktal_ab_models.read', return_value=[m.code for m in projection.APP.models]))
            stack.enter_context(mock.patch.object(projection, 'project', side_effect=lambda *_: _doc()))
            stack.enter_context(mock.patch.object(reader, '_read_raw', return_value=(b'fixture', 'Success', 0)))
            decode = stack.enter_context(mock.patch.object(reader, 'decode_header', return_value=header))
            tables = stack.enter_context(mock.patch.object(reader, 'read_table', return_value={'rows': []}))
            projection.read_document(object(), plan=plan)
            count = tables.call_count
            projection.read_document(object(), plan=plan)
            self.assertEqual(tables.call_count, count)
            plan.manifest = None
            decode.side_effect = [header, dict(header, ConfigRevision=header['ConfigRevision'] + 1)]
            with self.assertRaises(projection.ProjectionRefused):
                projection.read_document(object(), plan=plan)
            self.assertIsNone(plan.manifest)

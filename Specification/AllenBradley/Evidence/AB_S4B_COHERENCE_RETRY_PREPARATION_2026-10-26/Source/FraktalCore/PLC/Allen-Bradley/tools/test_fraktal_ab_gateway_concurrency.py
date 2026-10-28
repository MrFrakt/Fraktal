"""A slow set transaction must not monopolize its viewer's read channel.

Fake WebSocket and native writer only: no socket, PLC, or document store.
"""
import asyncio
import json
import threading
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_gateway as gw
import fraktal_ab_mailbox as mb
from test_fraktal_ab_gateway import _doc


class Connection:
    def __init__(self):
        self.request = type('Request', (), {'headers': {'Authorization': 'Bearer fixture'}})()
        self.incoming = asyncio.Queue()
        self.replies = asyncio.Queue()
        self.close_code = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        value = await self.incoming.get()
        if value is None:
            raise StopAsyncIteration
        return value

    async def send(self, message):
        await self.replies.put(json.loads(message))

    async def close(self, code, reason):
        self.close_code = code
        # A real close handshake yields while active native work drains.
        await asyncio.sleep(.01)
        self.incoming.put_nowait(None)

    def request_rpc(self, rid, method, params):
        self.incoming.put_nowait(json.dumps(dict(protocol=gw.PROTOCOL,
            id=rid, method=method, params=params)))

    def list_sets(self, rid, sequence):
        self.request_rpc(rid, 'writeBatch', {'writes': [
            dict(path='Press/HmiRequest/Kind', valueType='int32', value=mb.LIST_CONFIG_SETS),
            dict(path='Press/HmiRequest/Sequence', valueType='uint32', value=sequence)]})


class BlockingWriter:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = []

    def set_command(self, writes, mailbox, session):
        self.calls.append(writes)
        self.started.set()
        if not self.release.wait(2):
            raise RuntimeError('fixture writer was not released')
        return True


class ViewerConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tick = 10.0
        self.station = gw.Station(lambda: _doc({
            'Press/HmiRequest/Sequence': 0,
            'Press/HmiResponse/AckSequence': 0}), clock=lambda: self.tick,
            budget=decl.ReadBudget(500, 250, 2000, 3000, 1000, 2000, 3000))
        await self.station.document()
        self.writer = BlockingWriter()
        self.gateway = gw.Gateway(self.station, write_token='fixture',
            write_roots=frozenset({'Press'}), write_fn=self.writer)
        self.connection = Connection()
        self.handler = asyncio.create_task(self.gateway.handler(self.connection))

    async def asyncTearDown(self):
        self.writer.release.set()
        self.connection.incoming.put_nowait(None)
        await asyncio.wait_for(self.handler, 3)

    async def start_set_request(self):
        self.connection.list_sets(1, 1)
        self.assertTrue(await asyncio.to_thread(self.writer.started.wait, 1))

    async def test_complete_samples_continue_on_the_same_socket_during_a_set_request(self):
        await self.start_set_request()
        self.tick += 3.1  # even the previous complete sample has now expired
        self.connection.request_rpc(2, 'snapshot', {})
        reply_task = asyncio.create_task(self.connection.replies.get())
        done, _ = await asyncio.wait({reply_task}, timeout=.2)
        if not done:
            reply_task.cancel()
        self.assertTrue(done, 'the slow set transaction blocked its own viewer reads')
        reply = reply_task.result()
        self.assertEqual(reply['id'], 2)
        self.assertTrue(reply['ok'])
        self.assertEqual(reply['result']['values']['Press/Status/Name'], 'Press')
        self.assertEqual(reply['result']['sampleAgeMs'], 0)
        self.assertTrue(self.station.healthy)
        self.assertFalse(self.writer.release.is_set())
        self.assertEqual(len(self.writer.calls), 1)

    async def test_disconnect_cancels_a_queued_command_without_replaying_the_active_one(self):
        await self.start_set_request()
        self.connection.list_sets(2, 2)
        self.connection.incoming.put_nowait(None)
        await asyncio.sleep(.02)
        self.writer.release.set()
        await self.handler
        self.assertEqual(len(self.writer.calls), 1)
        self.assertEqual(self.gateway._mailbox_sequences['Press/HmiRequest'], 1)
        self.assertEqual(self.gateway._states, set())

    async def test_request_limit_discards_queued_commands_and_drains_native_work(self):
        await self.start_set_request()
        for rid in range(2, gw.MAX_PENDING_REQUESTS + 2):
            self.connection.list_sets(rid, rid)
        await asyncio.sleep(.04)
        self.assertEqual(self.connection.close_code, 1013)
        self.assertFalse(self.handler.done(), 'shutdown released an active native worker')
        self.writer.release.set()
        await self.handler
        self.assertEqual(len(self.writer.calls), 1)
        self.assertEqual(self.gateway._states, set())

    async def test_multiplexed_commands_remain_serialized_and_ordered(self):
        await self.start_set_request()
        self.connection.list_sets(2, 2)
        await asyncio.sleep(.02)
        self.assertEqual(len(self.writer.calls), 1)
        self.writer.release.set()
        replies = [await asyncio.wait_for(self.connection.replies.get(), 1)
                   for _ in range(2)]
        self.assertEqual([reply['id'] for reply in replies], [1, 2])
        self.assertTrue(all(reply['ok'] and reply['result'] for reply in replies))
        self.assertEqual(len(self.writer.calls), 2)

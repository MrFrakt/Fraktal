"""The host adapter's pylogix port against a fake controller on synthetic Templates.

The Templates are the binding tests' synthetic packing, not a measured Logix
layout; native Templates and timing are S6-Q gates. What is proven here: the
reply decodes to plain values, a request is the payload then its commit, an
acknowledgement is awaited for a bounded time, and nothing is ever resent.
"""
import struct
import unittest
from types import SimpleNamespace

import fraktal_ab_canonical_reader as reader
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_host_adapter as adapter
import fraktal_ab_host_cip as cip
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
from test_fraktal_ab_host_service_binding import pack


def encode_record(objects, sizes, handle, value):
    raw = bytearray(sizes[handle])

    def put(base, rows, value):
        for row in rows:
            if row['name'].startswith('ZZZZZZZZZZ') or row['name'] not in value:
                continue
            items = value[row['name']] if row['array'] else [value[row['name']]]
            for k, item in enumerate(items):
                if row['struct']:
                    child = reader.member_table(objects[row['handle']])
                    at = base + row['offset'] + k * sizes[row['handle']]
                    width = reader.is_string(child)
                    if width is not None:
                        length, data = [r for r in child if not r['name'].startswith('ZZZZZZZZZZ')]
                        encoded = item.encode()
                        struct.pack_into('<i', raw, at + length['offset'], len(encoded))
                        raw[at + data['offset']:at + data['offset'] + len(encoded)] = encoded
                    else:
                        put(at, child, item)
                else:
                    struct.pack_into('<i', raw, base + row['offset'] + 4 * k, item)
    put(0, reader.member_table(objects[handle]), value)
    return bytes(raw)


class FakeController:
    """Reply bytes from a dict; a commit request acknowledges itself unless told not to."""

    def __init__(self, port_row, templates, handles, *, acknowledge=True, refuse=False):
        self.row, self.templates, self.handles = port_row, templates, handles
        self.objects, self.sizes = reader.template_objects(templates)
        self.reply = dict(SchemaVersion=1, Serial=41, AckSequence=41, Accepted=1, ErrorCode=0, JobSequence=7,
                          JobService=1, JobOperation=29, JobPhase=1, NextChunk=0, JobName='alpha', JobText='')
        self.sent, self.acknowledge, self.refuse = [], acknowledge, refuse
        self.ConnectionSize = 508
        self.conn = SimpleNamespace(send=self.send)

    def Read(self, symbol):
        assert symbol == self.row['ReplySymbol'], symbol
        return SimpleNamespace(Status='Success',
                               Value=encode_record(self.objects, self.sizes, self.handles[host.REPLY], self.reply))

    def send(self, request):
        self.sent.append(request)
        if self.refuse:
            return 1, None
        if request[:1] == b'\x4d' and request.endswith(struct.pack('<HHI', 0xc4, 1, (self.reply['Serial'] + 1) & 0xffffffff)):
            if self.acknowledge:
                sequence = self.reply['Serial'] + 1
                self.reply.update(Serial=sequence, AckSequence=sequence, Accepted=1)
        return 0, None


class Port(unittest.TestCase):
    def setUp(self):
        app = demo.application()
        self.row = next(r for r in host.rows(dataclass_replace(app)) if r['Service'] == 1)
        definitions = {}
        host.augment(app, definitions, snapshot_count=5)
        self.templates, self.handles = pack(definitions, (host.REQUEST, host.REPLY))
        self.capture = dict(templates=self.templates, symbols=[
            dict(name=self.row['RequestSymbol'], handle=self.handles[host.REQUEST], arrayRank=0),
            dict(name=self.row['ReplySymbol'], handle=self.handles[host.REPLY], arrayRank=0),
            dict(name=self.row['CommitSymbol'], atomic=0xc4, arrayRank=0)],
            manifest=dict(configRevision=4242, legacyContentHash='5A1B2C' + '0' * 58,
                          commandBindings=[dict(RootSymbol=self.row['RootSymbol'])]))
        self.now = [0.0]

    def port(self, **fake):
        comm = FakeController(self.row, self.templates, self.handles, **fake)
        def sleep(seconds):
            self.now[0] += seconds
        return comm, cip.CipPort(comm, self.capture, [self.row], wait=0.1, answer_s=1.0,
                                 clock=lambda: self.now[0], sleep=sleep)

    def test_the_reply_decodes_to_plain_values(self):
        comm, port = self.port()
        reply = port.reply()
        self.assertEqual((reply['JobName'], reply['JobText'], reply['Serial']), ('alpha', '', 41))
        self.assertIsInstance(reply['Snapshot']['Values'], list)

    def test_a_request_is_its_payload_then_its_commit_and_returns_its_acknowledgement(self):
        comm, port = self.port()
        answer = port.submit(dict(Service=1, JobSequence=7, Operation=29, Argument=0, Chunk=0, Final=1, Status=1),
                             dict(Kind=binding.NONE))
        self.assertEqual(answer['AckSequence'], 42)
        self.assertEqual(len(comm.sent), 2)
        self.assertTrue(comm.sent[1].endswith(struct.pack('<HHI', 0xc4, 1, 42)))
        self.assertGreaterEqual(comm.ConnectionSize, self.row['ConnectionBytes'])

    def test_an_unacknowledged_or_refused_request_is_never_resent(self):
        for fake in (dict(acknowledge=False), dict(refuse=True)):
            with self.subTest(fake=fake):
                comm, port = self.port(**fake)
                with self.assertRaises(adapter.Unanswered):
                    port.submit(dict(Service=1, JobSequence=7, Operation=29, Argument=0, Chunk=0, Final=1, Status=1),
                                dict(Kind=binding.NONE))
                self.assertEqual(len(comm.sent), 1 if fake.get('refuse') else 2)

    def test_a_sparse_chunk_is_completed_and_never_widened(self):
        body = binding.complete(dict(Kind=binding.RECORDS, Keys=['a', 'b'], Values=[1, 2]), 8)
        self.assertEqual((body['Keys'], body['Values'], body['Line'], body['Total']),
                         (['a', 'b', *[''] * 6], [1, 2, *[0] * 6], '', 0))
        for bad in (dict(Unknown=1), dict(Values=[0] * 9), dict(Keys='a')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                binding.complete(bad, 8)

    def test_plain_turns_every_string_into_text(self):
        value = dict(a={'string': True, 'width': 4, 'LEN': 2, 'bytes': b'hi'.hex()}, b=[{'string': True, 'width': 4,
                     'LEN': 0, 'bytes': ''}], c=3)
        self.assertEqual(cip.plain(value), dict(a='hi', b=[''], c=3))


def dataclass_replace(app):
    import dataclasses
    return dataclasses.replace(app, canonical_host_services=True)


if __name__ == '__main__':
    unittest.main()

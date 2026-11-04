"""O11 harness command client: request shape, refusals, no replay, real loopback."""
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import unittest

import fraktal_ab_harness_commands as hc

REPOSITORY = Path(__file__).resolve().parents[3] / 'HMI/lib/data/opcua_repository.dart'


class Socket:
    def __init__(self, replies=(), fail=None):
        self.sent, self.replies, self.fail, self.closed = [], list(replies), fail, False

    def send(self, message):
        self.sent.append(json.loads(message))

    def recv(self, timeout):
        if self.fail:
            raise self.fail
        reply = self.replies.pop(0)
        return json.dumps(reply(self.sent[-1]) if callable(reply) else reply)

    def close(self):
        self.closed = True


def ok(request):
    return dict(id=request['id'], ok=True, result=True)


class Encoding(unittest.TestCase):
    def test_arguments_match_the_hmi_repository_request(self):
        source = REPOSITORY.read_text(encoding='utf-8')
        found = re.findall(r"OpcUaWrite\('\$request/(\w+)', OpcUaWriteType\.(\w+),", source)
        expected = [(n, t) for n, t, unused in hc.ARGUMENTS] + [('Sequence', 'uint32')]
        self.assertEqual(found, expected)

    def test_every_argument_is_written_with_its_zero_and_sequence_last(self):
        writes = hc.encode('Press', 7, dict(Kind=4, IntValue=-3))['writes']
        self.assertEqual([w['path'] for w in writes],
                         [f'Press/HmiRequest/{n}' for n, unused, unused in hc.ARGUMENTS]
                         + ['Press/HmiRequest/Sequence'])
        values = {w['path'].rsplit('/', 1)[1]: (w['valueType'], w['value']) for w in writes}
        self.assertEqual(values['Kind'], ('int32', 4))
        self.assertEqual(values['IntValue'], ('int32', -3))
        self.assertEqual(values['BoolValue'], ('boolean', False))
        self.assertEqual(values['TargetPath'], ('string', ''))
        self.assertEqual(values['Sequence'], ('uint32', 7))

    def test_a_multi_segment_root_is_kept_verbatim(self):
        writes = hc.encode('PLC1/MAIN/Unit', 1, {})['writes']
        self.assertEqual(writes[-1]['path'], 'PLC1/MAIN/Unit/HmiRequest/Sequence')

    def test_invalid_requests_refuse_before_any_io(self):
        client = hc.GatewayCommands('ws://127.0.0.1:8080/fraktal',
                                    connect=lambda *a, **k: self.fail('connected'))
        cases = [('Press', 1, dict(Missing=1)), ('Press', 1, dict(Kind=True)),
                 ('Press', 1, dict(Kind=2**31)), ('Press', 1, dict(DurationMs=-1)),
                 ('Press', 1, dict(BoolValue=1)), ('Press', 1, dict(TargetPath=3)),
                 ('Press', -1, {}), ('Press', 2**32, {}), ('', 1, {}), ('Press/..', 1, {}),
                 ('Press/HmiRequest', 1, {}), (None, 1, {})]
        for root, sequence, arguments in cases:
            with self.subTest(root=root, sequence=sequence, arguments=arguments), \
                    self.assertRaises(ValueError):
                client.write_batch(root, sequence, **arguments)

    def test_only_a_loopback_plain_gateway_url_is_accepted(self):
        for url in ('ws://example.com/fraktal', 'wss://127.0.0.1/fraktal', 'http://127.0.0.1/',
                    'ws://user:pw@127.0.0.1/fraktal', 'ws://127.0.0.1/fraktal?token=x',
                    'ws://10.0.0.5/fraktal'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                hc.GatewayCommands(url, connect=lambda *a, **k: None)
        for url, origin in (('ws://127.0.0.1:8080/fraktal', 'http://127.0.0.1'),
                            ('ws://localhost:8081/fraktal', 'http://localhost'),
                            ('ws://[::1]:8080/fraktal', 'http://[::1]')):
            seen = {}
            client = hc.GatewayCommands(url, connect=lambda u, **k: seen.update(k) or Socket([ok]))
            client.write_batch('Press', 1)
            self.assertEqual(seen['origin'], origin)


class Transport(unittest.TestCase):
    def client(self, socket):
        self.connects = 0
        def connect(url, **unused):
            self.connects += 1
            return socket
        return hc.GatewayCommands('ws://127.0.0.1:8080/fraktal', connect=connect)

    def test_one_request_per_call_on_one_connection(self):
        socket = Socket([ok, ok])
        client = self.client(socket)
        self.assertEqual(client.write_batch('Press', 5, Kind=3), hc.BatchReply(True, True, None))
        client.write_batch('Press', 6, Kind=3)
        self.assertEqual(self.connects, 1)
        self.assertEqual([m['id'] for m in socket.sent], [1, 2])
        self.assertEqual({m['protocol'] for m in socket.sent}, {hc.PROTOCOL})
        self.assertEqual({m['method'] for m in socket.sent}, {'writeBatch'})

    def test_a_gateway_refusal_is_a_reply_not_a_transport_failure(self):
        socket = Socket([lambda r: dict(id=r['id'], ok=False, error='Write root not permitted.')])
        reply = self.client(socket).write_batch('Press', 5)
        self.assertEqual(reply, hc.BatchReply(False, None, 'Write root not permitted.'))
        self.assertFalse(socket.closed)

    def test_transport_failure_closes_and_is_never_replayed(self):
        socket = Socket(fail=TimeoutError('no reply'))
        client = self.client(socket)
        with self.assertRaises(hc.GatewayCommandUnavailable):
            client.write_batch('Press', 5)
        self.assertTrue(socket.closed)
        with self.assertRaises(hc.GatewayCommandUnavailable):
            client.write_batch('Press', 6)
        self.assertEqual((self.connects, len(socket.sent)), (1, 1))

    def test_a_reply_for_another_request_or_malformed_closes(self):
        for reply in (dict(id=9, ok=True, result=True), dict(id=1, ok='yes'), [1]):
            socket = Socket([reply])
            client = self.client(socket)
            with self.subTest(reply=reply), self.assertRaises(hc.GatewayCommandUnavailable):
                client.write_batch('Press', 5)
            self.assertTrue(socket.closed)


class Rows:
    """Successive coherent observations of the four mailbox leaves."""
    def __init__(self, *observations):
        self.observations, self.reads = list(observations), 0

    def read_row(self, paths):
        self.reads += 1
        request, ack, accepted, diagnostic = self.observations.pop(0)
        return dict(values=dict(zip(paths, (request, ack, accepted, diagnostic))))


class Writer:
    def __init__(self, reply=hc.BatchReply(True, True, None)):
        self.calls, self.reply = [], reply

    def write_batch(self, root, sequence, **arguments):
        self.calls.append((root, sequence, arguments))
        return self.reply


class Command(unittest.TestCase):
    def setUp(self):
        self.now = 0.0

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

    def run_command(self, writer, rows, settle=1.0, **arguments):
        return hc.command(writer, rows, 'Press', 4, settle=settle, clock=self.clock,
                          sleep=self.sleep, **arguments)

    def test_next_sequence_is_reserved_from_the_committed_request(self):
        writer = Writer()
        rows = Rows((41, 41, True, ''), (42, 41, False, ''), (42, 42, True, 'ok.key'))
        answer = self.run_command(writer, rows, IntValue=2)
        self.assertEqual(writer.calls, [('Press', 42, dict(Kind=4, IntValue=2))])
        self.assertEqual(answer, dict(sequence=42, sent=True, accepted=True, diagnostic='ok.key'))

    def test_a_dint_published_sequence_wraps_as_uint32(self):
        writer = Writer()
        rows = Rows((-1, -1, True, ''), (0, 0, True, ''))
        self.assertEqual(self.run_command(writer, rows)['sequence'], 0)
        self.assertEqual(writer.calls[0][1], 0)

    def test_an_unsettled_mailbox_writes_nothing(self):
        writer = Writer()
        with self.assertRaisesRegex(AssertionError, 'settled'):
            self.run_command(writer, Rows((42, 41, True, '')))
        self.assertEqual(writer.calls, [])

    def test_a_refused_batch_returns_without_waiting(self):
        rows = Rows((5, 5, True, ''))
        answer = self.run_command(Writer(hc.BatchReply(False, None, 'refused')), rows)
        self.assertEqual(answer, dict(sequence=6, sent=False, accepted=False, error='refused'))
        self.assertEqual(rows.reads, 1)

    def test_a_missing_acknowledgement_times_out_without_a_second_write(self):
        writer = Writer()
        rows = Rows(*([(5, 5, True, '')] + [(6, 5, False, '')] * 100))
        with self.assertRaisesRegex(AssertionError, 'no acknowledgement of sequence 6'):
            self.run_command(writer, rows, settle=0.5)
        self.assertEqual(len(writer.calls), 1)


class Loopback(unittest.TestCase):
    def test_real_websocket_carries_a_loopback_origin_and_one_json_request(self):
        from websockets.sync.server import serve
        seen = []

        def handler(connection):
            seen.append(connection.request.headers.get('Origin'))
            request = json.loads(connection.recv())
            seen.append(request)
            connection.send(json.dumps(dict(id=request['id'], ok=True, result=True)))

        with serve(handler, '127.0.0.1', 0) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.socket.getsockname()[1]
            client = hc.GatewayCommands(f'ws://127.0.0.1:{port}/fraktal', timeout=5)
            try:
                reply = client.write_batch('Press', 9, Kind=2)
            finally:
                client.close()
                server.shutdown()
            thread.join(5)
        self.assertEqual(reply, hc.BatchReply(True, True, None))
        self.assertEqual(seen[0], 'http://127.0.0.1')
        self.assertEqual(seen[1]['params']['writes'][-1],
                         dict(path='Press/HmiRequest/Sequence', valueType='uint32', value=9))

    def test_import_graph_contains_no_station_generator_or_runtime(self):
        program = ('import sys; import fraktal_ab_harness_commands; '
                   'assert not set(sys.modules) & {"fraktal_ab_station", "fraktal_ab_generate", '
                   '"fraktal_ab_declaration", "fraktal_ab_projection", "fraktal_ab_gateway", '
                   '"fraktal_ab_mailbox", "pylogix"}')
        result = subprocess.run([sys.executable, '-c', program], cwd=Path(__file__).parent,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

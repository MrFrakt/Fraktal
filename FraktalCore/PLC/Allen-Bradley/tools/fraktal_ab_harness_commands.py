"""O11 harness commands through the brand-neutral gateway protocol.

A command is the HMI repository's request: the nine Core ``HmiRequest``
arguments, absent ones at their Core zero value, then ``Sequence``, in one
``writeBatch`` to a loopback write-enabled gateway. Any brand's gateway accepts
it, so the brand's one command encoder stays in its transport. The sequence is
reserved before sending and never reused. Nothing is queued, retried or
replayed, and a transport failure closes the client because the commit's
outcome is then ambiguous. The harness observes the acknowledgement through its
own controller reader, never through the gateway under test.

String capacities, write roots and permissions remain the gateway's,
transport's and PLC's to enforce; this client only encodes valid JSON values.
"""
from dataclasses import dataclass
import ipaddress
import json
import time
import urllib.parse

PROTOCOL = 'fraktal.opcua.gateway.v1'
# Core ST_HmiRequest arguments in the HMI repository's write order
# (lib/data/opcua_repository.dart), each with its gateway value type and zero.
ARGUMENTS = (('Kind', 'int32', 0), ('TargetPath', 'string', ''), ('NameValue', 'string', ''),
             ('TextValue', 'string', ''), ('User', 'string', ''), ('Secret', 'string', ''),
             ('IntValue', 'int32', 0), ('BoolValue', 'boolean', False),
             ('DurationMs', 'uint32', 0))
RANGES = {'int32': (-2**31, 2**31 - 1), 'uint32': (0, 2**32 - 1)}


class GatewayCommandUnavailable(RuntimeError):
    """The transport failed; whether the commit landed is unknown. Never retried."""


@dataclass(frozen=True)
class BatchReply:
    ok: bool
    result: object
    error: str | None


def _value(field, kind, value):
    if kind == 'boolean':
        valid = type(value) is bool
    elif kind == 'string':
        valid = type(value) is str
    else:
        low, high = RANGES[kind]
        valid = type(value) is int and low <= value <= high
    if not valid:
        raise ValueError(f'{field} is not a valid {kind}')
    return value


def encode(root, sequence, arguments):
    """The writeBatch params for one request; refuses before any I/O."""
    segments = root.split('/') if isinstance(root, str) else ['']
    if any(s in ('', '.', '..') or s == 'HmiRequest' for s in segments):
        raise ValueError('invalid root browse path')
    unknown = set(arguments) - {name for name, unused, unused in ARGUMENTS}
    if unknown:
        raise ValueError('unknown HmiRequest argument: ' + ', '.join(sorted(unknown)))
    writes = [dict(path=f'{root}/HmiRequest/{name}', valueType=kind,
                   value=_value(name, kind, arguments.get(name, zero)))
              for name, kind, zero in ARGUMENTS]
    # Sequence is the commit marker and is deliberately written last.
    writes.append(dict(path=f'{root}/HmiRequest/Sequence', valueType='uint32',
                       value=_value('Sequence', 'uint32', sequence)))
    return dict(writes=writes)


def _loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (TypeError, ValueError):
        return False


class GatewayCommands:
    """One request at a time over one connection; closed for good on failure."""

    def __init__(self, url, *, connect=None, timeout=5.0):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != 'ws' or not _loopback(parts.hostname) or parts.username \
                or parts.password or parts.query or parts.fragment:
            raise ValueError('harness commands use a loopback ws:// gateway only')
        if not 0 < timeout <= 30:
            raise ValueError('gateway command timeout must be within 30 s')
        host = f'[{parts.hostname}]' if ':' in parts.hostname else parts.hostname
        self._url, self._origin, self._timeout = url, f'http://{host}', timeout
        if connect is None:
            from websockets.sync.client import connect
        self._connect, self._socket, self._id, self._closed = connect, None, 0, False

    def write_batch(self, root, sequence, **arguments):
        params = encode(root, sequence, arguments)
        if self._closed:
            raise GatewayCommandUnavailable('gateway command client closed after a failure')
        self._id += 1
        message = json.dumps(dict(protocol=PROTOCOL, id=self._id, method='writeBatch',
                                  params=params))
        try:
            if self._socket is None:
                self._socket = self._connect(self._url, origin=self._origin,
                                             open_timeout=self._timeout)
            self._socket.send(message)
            reply = json.loads(self._socket.recv(timeout=self._timeout))
            if type(reply) is not dict or reply.get('id') != self._id \
                    or type(reply.get('ok')) is not bool:
                raise ValueError('unexpected gateway reply')
        except Exception as error:
            self.close()
            raise GatewayCommandUnavailable('gateway command outcome unknown') from error
        error = reply.get('error')
        return BatchReply(reply['ok'], reply.get('result'),
                          None if reply['ok'] else str(error) if error is not None else '')

    def close(self):
        self._closed = True
        socket, self._socket = self._socket, None
        if socket is not None:
            try:
                socket.close()
            except Exception:
                pass


def command(client, rows, root, kind, *, settle, clock=time.monotonic, sleep=time.sleep,
            **arguments):
    """Issue one command and wait for its acknowledgement, as the repository does.

    ``rows.read_row`` observes the controller directly. The request is refused
    unless the previous one is acknowledged; the next sequence is reserved from
    the controller's own committed request. An acknowledgement is not a result:
    the caller still reads the machine.
    """
    request, response = f'{root}/HmiRequest/Sequence', f'{root}/HmiResponse/'
    paths = (request, response + 'AckSequence', response + 'Accepted', response + 'Diagnostic')
    values = rows.read_row(paths)['values']
    previous = values[request] & 0xffffffff
    if values[paths[1]] & 0xffffffff != previous:
        raise AssertionError('mailbox has no settled acknowledgment; nothing written')
    sequence = (previous + 1) & 0xffffffff
    reply = client.write_batch(root, sequence, Kind=kind, **arguments)
    if not reply.ok or reply.result is not True:
        return dict(sequence=sequence, sent=False, accepted=False, error=reply.error)
    deadline = clock() + settle
    while clock() < deadline:
        values = rows.read_row(paths)['values']
        if values[paths[1]] & 0xffffffff == sequence:
            return dict(sequence=sequence, sent=True, accepted=values[paths[2]],
                        diagnostic=values[paths[3]])
        sleep(0.02)
    raise AssertionError(f'no acknowledgement of sequence {sequence}')

"""V6.11 host-service metadata: the client half of the shared host ingress.

Client-side protocol code, like fraktal_ab_command_binding. It imports no
station declaration or generator. Endpoints, chunk extents, StringFamily widths
and connection bounds all come from the manifest row and controller Templates.
The PLC owns key resolution, validation, job identity and final application;
a host only transports bounded chunks addressed by scope and key.
"""
import re
import struct

from fraktal_ab_command_binding import WritePlan, _path as symbol_path

MINOR = 11
VERSION = 1
HEADER_FIELDS = frozenset(('HostServiceBindingsCount', 'HostServiceBindingsCapacity',
                           'HostServiceBindings'))
SERVICES = dict(ConfigSets=1, ConfigProvider=2, LiveDocuments=3, HostEvents=4)
MUTATING = frozenset((1, 2, 3))
FIELD = frozenset(('RootSymbol', 'Service', 'Version', 'RequestSymbol', 'ChunkMember',
                   'MaximumChunkBytes', 'ConnectionBytes', 'CommitSymbol', 'ReplySymbol',
                   'CanonicalRoot', 'AccessGate'))
TEXT_FIELDS = frozenset(('RootSymbol', 'RequestSymbol', 'ChunkMember', 'CommitSymbol',
                         'ReplySymbol', 'CanonicalRoot'))
ENDPOINTS = ('RequestSymbol', 'ChunkMember', 'CommitSymbol', 'ReplySymbol')
SHARED = ('RequestSymbol', 'ChunkMember', 'CommitSymbol', 'ReplySymbol',
          'MaximumChunkBytes', 'ConnectionBytes')
GATE_COUNT = 12  # Core E_GatedAction; Access.Required has one slot per gate
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,39}\Z')
PATH = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*)+\Z')

# The host writes the envelope; SchemaVersion, ManifestRevision and
# StagedSequence are the encoder's, exactly as the typed command header is.
HEADER = ('SchemaVersion', 'ManifestRevision', 'StagedSequence')
ENVELOPE = ('Service', 'JobSequence', 'Operation', 'Argument', 'Chunk', 'Final', 'Status')
SCALARS = ('Kind', 'Count', 'Total', 'SetSchema', 'ConfigRev', 'RecordKind', 'CreatedSeconds',
           'Synchronized')
TEXTS = dict(Scope=80, Name=80, Model=64, Line=480)
COLUMNS = ('Revisions', 'RecordKinds', 'ValueTypes', 'Values')
KEY_WIDTH = 160
REPLY = ('SchemaVersion', 'Serial', 'AckSequence', 'Accepted', 'ErrorCode', 'JobSequence',
         'JobService', 'JobOperation', 'JobPhase', 'NextChunk', 'JobInt', 'JobBool',
         'Restoring', 'SessionPermits')
REPLY_TEXTS = dict(JobName=80, JobText=255)
SNAPSHOT = ('Kind', 'Count', 'ModelOrdinal', 'Date', 'Clock', 'Synchronized', 'Revision')

# Request.Status: the host's outcome for the job phase it answers.
OK, FAILED, REFUSED, LOST, UNAVAILABLE = 1, 2, 3, 4, 5
# Body.Kind
NONE, HEADER_CHUNK, RECORDS, CATALOG, TEXT = 0, 1, 2, 3, 4
# Reply.JobPhase
FETCH, STORE, PRESENT, SNAPSHOT_PHASE, RESTORE = 1, 2, 3, 4, 5
# Reply.ErrorCode: the PLC's verdict on the last consumed commit. Any refused
# chunk that claimed the active job abandons it; nothing is ever half-applied.
INVALID, COLLIDED, STALE_SERIAL, STALE_REVISION, NO_JOB, ORDER, ACCESS, BUSY, NOT_RESTORING = range(1, 10)


def bindings(rows):
    """Validate the table alone; cross-table rules live in the manifest."""
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1024:
        raise ValueError('invalid host-service binding table')
    seen, ingress, endpoints = set(), {}, {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELD:
            raise ValueError('invalid host-service binding descriptor')
        if any(type(row[k]) is not int for k in FIELD - TEXT_FIELDS) \
                or any(not isinstance(row[k], str) for k in TEXT_FIELDS):
            raise ValueError('invalid host-service binding field type')
        root, service = row['RootSymbol'], row['Service']
        if row['Version'] != VERSION or service not in SERVICES.values() \
                or not IDENTIFIER.fullmatch(root) or (root, service) in seen:
            raise ValueError('unsupported or duplicate host service')
        seen.add((root, service))
        if service in MUTATING:
            if any(not IDENTIFIER.fullmatch(row[k]) for k in ENDPOINTS) \
                    or len({row[k] for k in ENDPOINTS} | {root}) != 5 \
                    or not 500 <= row['ConnectionBytes'] <= 4000 \
                    or not 1 <= row['MaximumChunkBytes'] <= row['ConnectionBytes'] - 256 \
                    or row['CanonicalRoot'] != '' or not -1 <= row['AccessGate'] < GATE_COUNT \
                    or (service != SERVICES['LiveDocuments'] and row['AccessGate'] != -1):
                raise ValueError('invalid host-service endpoint, bound or gate')
            shared = tuple(row[k] for k in SHARED)
            # One ingress per root: every mutating service shares its endpoints,
            # so PLC-owned job identity covers all host writers together.
            if ingress.setdefault(root, shared) != shared:
                raise ValueError('host services of one root must share one ingress')
            for name in (row['RequestSymbol'], row['CommitSymbol'], row['ReplySymbol']):
                if endpoints.setdefault(name, root) != root:
                    raise ValueError('host-service endpoint shared between roots')
        elif any(row[k] != '' for k in ENDPOINTS) or row['MaximumChunkBytes'] != 0 \
                or row['ConnectionBytes'] != 0 or row['AccessGate'] != -1 \
                or row['CanonicalRoot'] != root + '/HostEvents' \
                or len(row['CanonicalRoot'].encode()) > 255 or not PATH.fullmatch(row['CanonicalRoot']):
            # HostEvents has no writable state: a read-only canonical ring.
            raise ValueError('host events advertise only their read-only canonical ring')
    for root, (request, chunk, commit, reply, *_unused) in ingress.items():
        if any(name in ingress for name in (request, commit, reply)):
            raise ValueError('host-service endpoint collides with a root')
    return rows


def schema(row, symbols, objects, sizes, member_table, is_string):
    """Validate the shared ingress Templates; returns (records per chunk, snapshot extent)."""
    if row['Service'] not in MUTATING:
        raise ValueError('host events have no ingress schema')

    def structured(name):
        symbol = symbols.get(name)
        if not symbol or symbol.get('arrayRank', 0) or symbol.get('handle') not in objects:
            raise ValueError('host-service structured Symbol unavailable: ' + name)
        handle = symbol['handle']
        if is_string(member_table(objects[handle])) is not None:
            raise ValueError('host-service endpoint must be structured')
        return handle

    def members(handle):
        return {m['name']: m for m in member_table(objects[handle]) if not m['name'].startswith('ZZZZZZZZZZ')}

    def dint(m, count=0):
        return not m['struct'] and m['atomic'] == 0xC4 and bool(m['array']) == bool(count) \
            and (not count or m['info'] == count)

    def string(m, width, count=0):
        return m['struct'] and m['handle'] in objects and bool(m['array']) == bool(count) \
            and (not count or m['info'] == count) and is_string(member_table(objects[m['handle']])) == width

    handle = structured(row['RequestSymbol'])
    outer = members(handle)
    if set(outer) != {*HEADER, *ENVELOPE, row['ChunkMember']} or sizes[handle] > row['MaximumChunkBytes'] \
            or any(not dint(outer[n]) for n in (*HEADER, *ENVELOPE)):
        raise ValueError('host request envelope layout or size bound differs')
    body = outer[row['ChunkMember']]
    if not body['struct'] or body['array'] or body['handle'] not in objects:
        raise ValueError('host chunk must be a structured scalar')
    chunk = members(body['handle'])
    keys = chunk.get('Keys')
    extent = keys['info'] if keys and keys['array'] else 0
    if set(chunk) != {*SCALARS, *TEXTS, 'Keys', *COLUMNS} or not 1 <= extent <= 64 \
            or any(not dint(chunk[n]) for n in SCALARS) \
            or any(not string(chunk[n], width) for n, width in TEXTS.items()) \
            or not string(keys, KEY_WIDTH, extent) or any(not dint(chunk[n], extent) for n in COLUMNS):
        raise ValueError('host chunk layout differs from V6.11')
    commit = symbols.get(row['CommitSymbol'])
    # Atomic Symbols are retained by discovery even though they have no Template.
    if not commit or commit.get('arrayRank', 0) or commit.get('atomic') != 0xC4:
        raise ValueError('host commit must be a DINT scalar Symbol')
    reply = members(structured(row['ReplySymbol']))
    snapshot = reply.get('Snapshot')
    if set(reply) != {*REPLY, *REPLY_TEXTS, 'Snapshot'} or any(not dint(reply[n]) for n in REPLY) \
            or any(not string(reply[n], width) for n, width in REPLY_TEXTS.items()) \
            or not snapshot['struct'] or snapshot['array'] or snapshot['handle'] not in objects:
        raise ValueError('host reply layout differs from V6.11')
    held = members(snapshot['handle'])
    values = held.get('Values')
    count = values['info'] if values and values['array'] else 0
    if set(held) != {*SNAPSHOT, 'Values'} or not 1 <= count <= 100000 \
            or any(not dint(held[n]) for n in SNAPSHOT) or not dint(values, count):
        raise ValueError('host reply snapshot layout differs from V6.11')
    return extent, count


def next_sequence(reply):
    """The next commit: the PLC-published serial plus one, in uint32 order.

    AckSequence names the last CONSUMED commit, which may be a refused stale
    one; only Serial is the accepted position a writer may advance from.
    """
    serial = reply['Serial']
    if type(serial) is not int or not -(1 << 31) <= serial < (1 << 31):
        raise ValueError('host reply serial is not a DINT')
    return (serial + 1) & 0xffffffff


def outcome(reply, sequence):
    """None until the PLC consumed this commit; then (accepted, error code)."""
    if (reply['AckSequence'] & 0xffffffff) != sequence:
        return None
    if reply['Accepted'] not in (0, 1) or (reply['Accepted'] == 1) != (reply['ErrorCode'] == 0):
        raise ValueError('host reply verdict is inconsistent')
    return bool(reply['Accepted']), reply['ErrorCode']


def complete(body, extent):
    """A sparse chunk with every field it does not name at its empty value."""
    out = {**{n: 0 for n in SCALARS}, **{n: '' for n in TEXTS}, 'Keys': [''] * extent,
           **{n: [0] * extent for n in COLUMNS}}
    for name, value in body.items():
        if name not in out:
            raise ValueError('unknown host chunk field: ' + name)
        if isinstance(out[name], list):
            if not isinstance(value, list) or len(value) > extent:
                raise ValueError('host chunk column exceeds the negotiated extent')
            value = list(value) + out[name][len(value):]
        out[name] = value
    return out


def write_plan(capture, descriptor, envelope, body, sequence, *, connection_bytes):
    """Encode one 0x4D request write and the separate final DINT commit.

    Pure protocol code: no network write, no key resolution, no retry. The
    caller sends the payload, then the commit, and never resends an
    ambiguous outcome; the PLC refuses a replay as stale.
    """
    from fraktal_ab_canonical_reader import snapshot
    snapshot(capture)  # validates manifest, Templates, roles and absence of input records
    if descriptor not in capture['manifest'].get('hostServiceBindings', []):
        raise ValueError('unnegotiated host-service binding')
    return encode(descriptor, capture['symbols'], capture['templates'], capture['manifest']['configRevision'],
                  envelope, body, sequence, connection_bytes=connection_bytes)


def encode(descriptor, symbol_rows, templates, manifest_revision, envelope, body, sequence, *, connection_bytes):
    """The native encoding alone, from Templates; `write_plan` is the negotiated entry."""
    from fraktal_ab_canonical_reader import template_objects, member_table, is_string
    bindings([descriptor])
    if descriptor['Service'] not in MUTATING:
        raise ValueError('host events accept no writes')
    if type(connection_bytes) is not int or connection_bytes < descriptor['ConnectionBytes']:
        raise ValueError('host connection is below the PLC-published minimum')
    if not isinstance(envelope, dict) or set(envelope) != set(ENVELOPE) \
            or envelope['Service'] != descriptor['Service']:
        raise ValueError('complete host envelope for this service required')
    if type(sequence) is not int or not 0 <= sequence <= 0xffffffff:
        raise ValueError('sequence is not UInt32')
    objects, sizes = template_objects(templates)
    symbols = {s['name']: s for s in symbol_rows}
    extent, _unused = schema(descriptor, symbols, objects, sizes, member_table, is_string)
    if not isinstance(body, dict) or set(body) != {*SCALARS, *TEXTS, 'Keys', *COLUMNS}:
        raise ValueError('complete host chunk required')
    handle = symbols[descriptor['RequestSymbol']]['handle']
    template = next(t for t in templates if t['handle'] == handle)
    crc = template.get('structureHandle')
    if type(crc) is not int or not 0 <= crc <= 0xffff:
        raise ValueError('Template attribute 1 structure handle unavailable')
    outer = {m['name']: m for m in member_table(objects[handle])}
    data = bytearray(sizes[handle])

    def integer(at, value, lower=-(1 << 31), upper=(1 << 31) - 1):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError('host scalar is outside its DINT range')
        struct.pack_into('<I', data, at, value & 0xffffffff)

    def text(at, rows, value, width):
        if not isinstance(value, str):
            raise ValueError('host text requires a string')
        raw = value.encode('utf-8')
        if len(raw) > width or b'\0' in raw:
            raise ValueError('host text exceeds native width or contains NUL')
        parts = {m['name']: m for m in rows}
        struct.pack_into('<i', data, at + parts['LEN']['offset'], len(raw))
        start = at + parts['DATA']['offset']
        data[start:start + len(raw)] = raw

    for name, value in (('SchemaVersion', VERSION), ('ManifestRevision', manifest_revision),
                        ('StagedSequence', sequence)):
        integer(outer[name]['offset'], value & 0xffffffff, 0, 0xffffffff)
    for name in ENVELOPE:
        integer(outer[name]['offset'], envelope[name])
    base = outer[descriptor['ChunkMember']]['offset']
    chunk = {m['name']: m for m in member_table(objects[outer[descriptor['ChunkMember']]['handle']])}
    for name in SCALARS:
        integer(base + chunk[name]['offset'], body[name])
    for name, width in TEXTS.items():
        text(base + chunk[name]['offset'], member_table(objects[chunk[name]['handle']]), body[name], width)
    keys = chunk['Keys']
    stride = sizes[keys['handle']]
    if not isinstance(body['Keys'], list) or len(body['Keys']) != extent:
        raise ValueError('host chunk key column extent differs')
    for index, value in enumerate(body['Keys']):
        text(base + keys['offset'] + index * stride, member_table(objects[keys['handle']]), value, KEY_WIDTH)
    for name in COLUMNS:
        if not isinstance(body[name], list) or len(body[name]) != extent:
            raise ValueError('host chunk column extent differs')
        for index, value in enumerate(body[name]):
            integer(base + chunk[name]['offset'] + 4 * index, value)
    path = symbol_path(descriptor['RequestSymbol'])
    payload = bytes((0x4d, len(path) // 2)) + path + struct.pack('<HHH', 0x02a0, crc, 1) + data
    path = symbol_path(descriptor['CommitSymbol'])
    commit = bytes((0x4d, len(path) // 2)) + path + struct.pack('<HHI', 0xc4, 1, sequence)
    # The same conservative connected-message allowance as the command writer.
    if len(payload) + 110 > connection_bytes or len(commit) + 110 > connection_bytes:
        raise ValueError('host chunk does not fit one connected Write Tag request')
    return WritePlan(descriptor['RequestSymbol'], descriptor['CommitSymbol'], len(data), payload, commit)

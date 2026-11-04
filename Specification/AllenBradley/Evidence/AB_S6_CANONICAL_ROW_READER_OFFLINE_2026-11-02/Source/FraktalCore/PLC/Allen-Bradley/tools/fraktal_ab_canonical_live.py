"""S6 read-only, declaration-free acquisition of one canonical row at a time.

The S1 capture validates the discovered schema. It never supplies a live value:
every returned leaf and occupied-array count is reread inside its published
seqlock. Different owners are separate rows, never a whole-document proof.
There is no write, automatic reconnect, fallback on failure or value retention.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
import re
import struct
import time
from types import MappingProxyType

from fraktal_ab_canonical_reader import (
    MAX_LEAVES, decode, is_string, member_table, read_document, scalar_value,
    snapshot, template_objects, template_structure_handle,
)
from fraktal_ab_s0_canonical_measure import ATOMIC

SEGMENT = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)(?:\[(-?\d+)\])?\Z')


@dataclass(frozen=True)
class Location:
    path: str
    symbol: str
    source: str
    offset: int
    row: dict
    annotation: dict
    width: int
    requirements: tuple
    bit: int | None = None


class CoherenceUnavailable(ValueError):
    """No values accompany a failed proof; diagnostics contain timing/counters."""
    def __init__(self, reason, attempts, failures):
        super().__init__(reason)
        self.attempts, self.failures = attempts, tuple(failures)


def _later(candidate, previous):
    distance = (candidate - previous) & 0x7fffffff
    return 0 < distance < 0x40000000


class CanonicalRowReader:
    def __init__(self, capture, read_raw, read_counter, *, clock_ns=time.monotonic_ns,
                 sleep=time.sleep):
        # A private copy also keeps S1's derived annotation cache out of evidence.
        capture = deepcopy(capture)
        snapshot(capture)
        self._manifest = capture['manifest']
        if self._manifest.get('schemaMinor', 0) < 7:
            raise ValueError('live row reads require published V6.7 coherence bindings')
        self._objects, self._sizes = template_objects(capture['templates'])
        self._symbols = {s['name']: s for s in capture['symbols']}
        from fraktal_ab_canonical_manifest import type_tables
        self._annotations, self._exceptions = type_tables(
            self._manifest['typeAnnotations'], self._manifest['pathExceptions'])
        roots = [s['name'] for s in capture['symbols']
                 if not s.get('arrayRank', 0) and s.get('handle') in self._objects
                 and any(r['name'] == 'Status' and r['struct']
                         for r in member_table(self._objects[s['handle']]))]
        self._sources = [(root, root) for root in roots]
        self._sources += [(b['TargetRoot'], b['SourceSymbol']) for b in self._manifest['bindings']]
        self._sources += [(p['CanonicalRoot'], p['SourceSymbol']) for p in self._manifest['dataProducts']]
        self._raw, self._counter = read_raw, read_counter
        self._clock, self._sleep = clock_ns, sleep
        self._locations = {}

    def _resolve_in(self, path, prefix, source):
        if not path.startswith(prefix + '/'):
            return None
        handle = self._symbols[source]['handle']
        physical, logical, offset, requirements = source, prefix, 0, []
        segments = path[len(prefix) + 1:].split('/')
        for depth, segment in enumerate(segments):
            if depth >= 64:
                raise ValueError('canonical path exceeds depth budget')
            match = SEGMENT.fullmatch(segment)
            if not match:
                raise ValueError('invalid canonical path segment')
            name, index = match.groups()
            if index is not None and str(int(index)) != index:
                raise ValueError('array index spelling is not canonical')
            rows = member_table(self._objects[handle])
            row = next((r for r in rows if r['name'] == name), None)
            if row is None:
                return None
            key = logical + '/' + name
            annotation = dict(self._annotations.get((self._objects[handle].Name, name), {}))
            annotation.update(self._exceptions.get(re.sub(r'\[-?\d+\]', '[*]', key), {}))
            count_member = annotation.pop('countMember', None)
            physical += '.' + name
            offset += row['offset']
            bit = row['info'] if not row['struct'] and row['atomic'] == 0xC1 else None
            width = self._sizes[row['handle']] if row['struct'] else (
                8 if row['atomic'] == 0xCC else ATOMIC.get(row['atomic'], ('', 0))[1])
            if not width:
                raise ValueError('unsupported native leaf type')
            if bool(row['array']) != (index is not None):
                return None  # The array itself is not a scalar canonical leaf.
            if row['array']:
                lower, extent = annotation.get('lowerBound'), annotation.get('elementCount')
                if type(lower) is not int or type(extent) is not int:
                    raise ValueError('array lacks published logical bounds')
                ordinal = int(index) - lower
                packed = annotation.get('logicalType') == 'BOOL' and row['atomic'] == 0xD3
                capacity = row['info'] * 32 if packed else row['info']
                if not 0 < extent <= capacity or not 0 <= ordinal < extent \
                        or ordinal not in annotation.get('indices', range(extent)):
                    raise ValueError('canonical array index outside published selection')
                if count_member:
                    requirements.append((logical + '/' + count_member, ordinal, extent))
                if packed:
                    physical += '[' + str(ordinal // 32) + ']'
                    offset += (ordinal // 32) * 4
                    bit = ordinal % 32
                elif row['atomic'] == 0xC1:
                    physical += '[' + str(ordinal) + ']'
                    offset += ordinal // 8
                    bit = ordinal % 8
                else:
                    physical += '[' + str(ordinal) + ']'
                    offset += ordinal * width
                logical = key + '[' + index + ']'
            else:
                logical = key
            if depth == len(segments) - 1:
                if row['struct'] and is_string(member_table(self._objects[row['handle']])) is None:
                    return None
                return Location(path, physical, source, offset,
                                MappingProxyType(row), MappingProxyType(annotation),
                                width, tuple(requirements), bit)
            if not row['struct'] or is_string(member_table(self._objects[row['handle']])) is not None:
                return None
            handle = row['handle']
        return None

    def location(self, path):
        """Resolve through Templates and PLC bindings, including logical bounds."""
        if not isinstance(path, str) or len(path.encode('utf-8')) > 255:
            raise ValueError('canonical path must be text')
        if path not in self._locations:
            if len(self._locations) >= MAX_LEAVES:
                raise ValueError('canonical location cache budget exceeded')
            found = [loc for prefix, source in self._sources
                     if (loc := self._resolve_in(path, prefix, source)) is not None]
            if len(found) != 1:
                raise ValueError('canonical leaf absent or ambiguous: ' + path)
            self._locations[path] = found[0]
        return self._locations[path]

    def _binding(self, path):
        for binding in self._manifest.get('ownerReadBindings', []):
            prefix = binding['CanonicalPrefix']
            members = json.loads(binding['MembersJson'])
            selections = [prefix + '/' + member for member in members] if members else [prefix]
            if any(path == p or path.startswith(p + '/') for p in selections):
                return (binding['RevisionSymbol'], binding['ProgressSymbol'], 2,
                        binding['MaximumProofWindowUs'], binding['MinimumUpdateIntervalUs'])
        for binding in self._manifest['readCoherenceBindings']:
            prefix = binding['CanonicalPrefix']
            if path == prefix or path.startswith(prefix + '/'):
                return (binding['RevisionSymbol'], binding['RevisionSymbol'], 1,
                        binding['MutationPeriodUs'], binding['MutationPeriodUs'])
        raise ValueError('canonical leaf has no published coherence owner')

    def _decode(self, location, raw):
        row = dict(location.row, name='Value', offset=0, array=0, info=0)
        # A symbolic BOOL read already returns the selected bit as one byte.
        if row['atomic'] == 0xC1 and not row['struct']:
            if len(raw) != 1:
                raise ValueError('BOOL scalar reply length mismatch')
            return bool(raw[0]), 'Boolean'
        if len(raw) != location.width:
            raise ValueError('native scalar reply length mismatch')
        value = decode(raw, 0, [row], self._objects, location.width,
                       template_sizes=self._sizes, strict=True, native_times=True)['Value']
        if row['struct']:
            return bytes.fromhex(value['bytes']).decode('utf-8'), 'String'
        if location.annotation.get('logicalType') == 'BOOL' and row['atomic'] == 0xD3:
            return bool(value >> location.bit & 1), 'Boolean'
        return scalar_value(value, row['atomic'], location.annotation)

    def read_row(self, paths):
        """Acquire one owner, at most 20 attempts within one second.

        Occupancy counts are part of the same proof. A coherent but unoccupied
        index refuses; a changed count/revision retries. No result contains
        bootstrap values or values from a failed attempt.
        """
        paths = tuple(paths)
        if not paths or len(paths) != len(set(paths)) or len(paths) > MAX_LEAVES:
            raise ValueError('empty, duplicate or excessive canonical row selection')
        selected, pending = {}, list(paths)
        while pending:
            path = pending.pop()
            if path in selected:
                continue
            selected[path] = self.location(path)
            pending.extend(p for p, unused, capacity in selected[path].requirements)
            if len(selected) > MAX_LEAVES:
                raise ValueError('canonical row dependency budget exceeded')
        bindings = {self._binding(p) for p in selected}
        if len(bindings) != 1:
            raise ValueError('mixed coherence owners require separate canonical rows')
        revision, progress, protocol, window_us, period_us = bindings.pop()
        started, failures, attempt = self._clock(), [], 0

        def bounded(operation):
            if self._clock() - started >= 1_000_000_000:
                raise CoherenceUnavailable('canonical row deadline exceeded', attempt, failures)
            value = operation()
            if self._clock() - started >= 1_000_000_000:
                raise CoherenceUnavailable('canonical row deadline exceeded', attempt, failures)
            return value

        def counter(symbol):
            value = bounded(lambda: self._counter(symbol))
            if type(value) is not int or not 0 <= value <= 2147483646:
                raise ValueError('invalid canonical revision/progress counter')
            return value

        initial = counter(progress)
        for attempt in range(1, 21):
            if self._clock() - started >= 1_000_000_000:
                break
            if initial % 2:
                initial = counter(progress)
            proof_start = self._clock()
            before = counter(revision)
            if before % 2:
                failures.append(dict(attempt=attempt, reason='odd-before', before=before))
            else:
                samples = {p: bounded(lambda loc=loc: self._raw(loc)) for p, loc in selected.items()}
                after = counter(revision)
                proof_end = self._clock()
                advanced = after if protocol == 1 else counter(progress)
                elapsed = self._clock() - started
                if elapsed >= 1_000_000_000:
                    break
                if before == after and not after % 2 and proof_end - proof_start < window_us * 1000 \
                        and not initial % 2 and not advanced % 2 and _later(advanced, initial):
                    decoded = {p: self._decode(selected[p], raw) for p, raw in samples.items()}
                    for loc in selected.values():
                        for count_path, ordinal, capacity in loc.requirements:
                            count, count_type = decoded[count_path]
                            if count_type in ('Int64', 'UInt64'):
                                count = int(count)  # canonical 64-bit integers are decimal strings
                            if type(count) is not int or count <= ordinal:
                                raise ValueError('canonical array index is not occupied')
                            if count > capacity:
                                raise ValueError('canonical array count exceeds capacity')
                    elapsed = self._clock() - started
                    if elapsed >= 1_000_000_000:
                        raise CoherenceUnavailable('canonical row deadline exceeded', attempt, failures)
                    return dict(schema='fraktal.ab.canonical-row',
                                values={p: decoded[p][0] for p in paths},
                                types={p: decoded[p][1] for p in paths},
                                revision=after, progress=advanced, protocol=protocol,
                                attempts=attempt, sourceStartedNs=started,
                                acquisitionNs=elapsed, proofWindowNs=proof_end - proof_start)
                failures.append(dict(attempt=attempt, reason='proof-or-progress-unavailable',
                                     before=before, after=after, windowNs=proof_end - proof_start))
            if attempt < 20:
                self._sleep(min(period_us, 1000) / 1_000_000)
        raise CoherenceUnavailable('canonical row coherence unavailable', attempt, failures)


def open_reader(comm, *, expect_serial):
    """None means no canonical manifest; present malformed/ambiguous fails closed."""
    from fraktal_ab_canonical_manifest import manifest_candidates
    from fraktal_ab_canonical_reader import discover_templates
    identity = comm.GetDeviceProperties()
    if identity.Status != 'Success' or identity.Value is None \
            or int(str(identity.Value.SerialNumber), 0) != int(expect_serial, 16):
        raise ValueError('controller serial guard failed')
    reply = comm.GetTagList(allTags=False)
    if reply.Status != 'Success':
        raise ValueError('Symbol discovery failed')
    objects = discover_templates(comm)
    candidates = manifest_candidates(
        [dict(name=t.TagName, handle=t.DataTypeValue, arrayRank=t.Array)
         for t in reply.Value if t.Struct],
        [dict(handle=h, members=member_table(udt)) for h, udt in objects.items()])
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError('canonical manifest ambiguous; legacy fallback refused')
    # S1 performs the full physical manifest/schema validation before caching.
    unused, capture = read_document(comm, expect_serial=expect_serial)
    sizes = {t['handle']: t['byteSize'] for t in capture['templates']}
    handles = {t['handle']: template_structure_handle(comm, t['handle'])
               for t in capture['templates'] if is_string(t['members']) is not None}

    def raw(location):
        row = location.row
        # A DWORD array location already names its physical word; pylogix's
        # BOOL-array /32 rewrite must not be applied a second time.
        ioi = comm._build_ioi(location.symbol, 0xC4)
        status, packet = comm.conn.send(comm._add_read_service(ioi, 1))
        if status != 0 or packet is None or len(packet) < 52:
            raise ValueError('canonical scalar read failed')
        service, reserved, general, extended, code = struct.unpack('<BBBBH', packet[46:52])
        if (service, reserved, general, extended) != (0xCC, 0, 0, 0):
            raise ValueError('invalid canonical scalar reply header')
        if row['struct']:
            if code != 0x02A0 or len(packet) < 54 \
                    or struct.unpack('<H', packet[52:54])[0] != handles[row['handle']]:
                raise ValueError('canonical StringFamily reply type mismatch')
            value = packet[54:]
        else:
            if code != row['atomic']:
                raise ValueError('canonical scalar reply type mismatch')
            value = packet[52:]
        expected = sizes[row['handle']] if row['struct'] else location.width
        if len(value) != expected:
            raise ValueError('canonical scalar reply length mismatch')
        return bytes(value)

    def counter(symbol):
        reply = comm.Read(symbol)
        if reply.Status != 'Success':
            raise ValueError('canonical counter read failed')
        return reply.Value

    return CanonicalRowReader(capture, raw, counter)

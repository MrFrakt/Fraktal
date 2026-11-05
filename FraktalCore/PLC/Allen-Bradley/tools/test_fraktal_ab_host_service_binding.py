"""V6.11 client protocol: Template schema, native encoding and manifest table.

Templates here are laid out from the generated definitions by a synthetic
packer; they prove the client follows Template offsets, widths and extents,
not a measured Logix ABI. Native layout is an S6-Q gate.
"""
from copy import deepcopy
import struct
import unittest

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_reader as reader
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
import fraktal_ab_owner_read_fixture as owner_fixture
from test_fraktal_ab_canonical_reader import member


def pack(definitions, roots):
    """Synthetic Templates for `roots`: DINT/StringFamily members, packed in order."""
    templates, handles, sizes = [], {}, {}

    def build(kind):
        if kind in handles:
            return handles[kind]
        handle = 0x700 + len(templates)
        handles[kind] = handle
        entry = dict(handle=handle, name=kind)
        templates.append(entry)
        if kind.startswith(pub.PREFIX + 'String'):
            width = pub.string_width(kind)
            entry.update(byteSize=4 + -(-width // 4) * 4,
                         members=[member('LEN', 0xc4, 0), member('DATA', 0x20c2, 4, width)])
        else:
            rows, offset = [], 0
            for m in definitions[kind]:
                if m.kind == 'DINT':
                    rows.append(member(m.name, 0x20c4 if m.count else 0xc4, offset, m.count))
                    offset += 4 * (m.count or 1)
                else:
                    child = build(m.kind)
                    rows.append(member(m.name, 0x8000 | (0x2000 if m.count else 0) | child, offset, m.count))
                    offset += sizes[child] * (m.count or 1)
            entry.update(byteSize=offset, members=rows, structureHandle=0xb000 | handle)
        sizes[handle] = entry['byteSize']
        return handle

    return templates, {kind: build(kind) for kind in roots}


class Schema(unittest.TestCase):
    def setUp(self):
        self.app = demo.application()
        self.row = next(r for r in host.rows(self.app) if r['Service'] == 1)
        self.definitions = {}
        host.augment(self.app, self.definitions, snapshot_count=5)

    def capture(self, definitions=None):
        templates, handles = pack(definitions or self.definitions, (host.REQUEST, host.REPLY))
        symbols = [dict(name=self.row['RequestSymbol'], handle=handles[host.REQUEST], arrayRank=0),
                   dict(name=self.row['ReplySymbol'], handle=handles[host.REPLY], arrayRank=0),
                   dict(name=self.row['CommitSymbol'], atomic=0xc4, arrayRank=0)]
        return templates, symbols

    def schema(self, templates, symbols, row=None):
        objects, sizes = reader.template_objects(templates)
        return binding.schema(row or self.row, {s['name']: s for s in symbols}, objects, sizes,
                              reader.member_table, reader.is_string)

    def test_the_generated_layout_negotiates_its_chunk_and_snapshot_extents(self):
        self.assertEqual(self.schema(*self.capture()), (host.RECORDS_PER_CHUNK, 5))

    def test_each_layout_deviation_refuses(self):
        M, S = pub.Member, pub.string_type
        def changed(kind, name, replacement):
            d = deepcopy(self.definitions)
            d[kind] = tuple(replacement if m.name == name else m for m in d[kind] if replacement or m.name != name)
            return d
        cases = {
            'missing envelope': changed(host.REQUEST, 'Status', None),
            'narrow line': changed(host.CHUNK, 'Line', M('Line', S(479))),
            'scalar text': changed(host.CHUNK, 'Keys', M('Keys', S(binding.KEY_WIDTH))),
            'short column': changed(host.CHUNK, 'Values', M('Values', 'DINT', count=host.RECORDS_PER_CHUNK - 1)),
            'wide key': changed(host.CHUNK, 'Keys', M('Keys', S(255), count=host.RECORDS_PER_CHUNK)),
            'no snapshot': changed(host.REPLY, 'Snapshot', None),
            'scalar snapshot values': changed(host.SNAPSHOT, 'Values', M('Values', 'DINT')),
            'text reply serial': changed(host.REPLY, 'Serial', M('Serial', S(40))),
        }
        for name, definitions in cases.items():
            with self.assertRaises(ValueError, msg=name):
                self.schema(*self.capture(definitions))
        templates, symbols = self.capture()
        with self.assertRaisesRegex(ValueError, 'size bound'):
            self.schema(templates, symbols, dict(self.row, MaximumChunkBytes=1000))
        with self.assertRaisesRegex(ValueError, 'commit'):
            self.schema(templates, [s for s in symbols if s['name'] != self.row['CommitSymbol']])

    def encode(self, sequence=7, **change):
        templates, symbols = self.capture()
        envelope = dict(Service=1, JobSequence=12, Operation=29, Argument=0, Chunk=1, Final=0, Status=1)
        body = dict(Kind=binding.RECORDS, Count=2, Total=2, SetSchema=0, ConfigRev=0, RecordKind=1,
                    CreatedSeconds=0, Synchronized=0, Scope='Press', Name='', Model='', Line='',
                    Keys=['press.stroke', 'press.dwellMs', *[''] * 6], Revisions=[5480224] * 8,
                    RecordKinds=[1] * 8, ValueTypes=[0, 3, *[0] * 6], Values=[-12, 2500, *[0] * 6])
        for key, value in change.items():
            (envelope if key in envelope else body)[key] = value
        return templates, symbols, binding.encode(self.row, symbols, templates, 4242, envelope, body,
                                                 sequence, connection_bytes=4000)

    def test_the_encoder_follows_template_offsets_and_writes_the_commit_separately(self):
        templates, symbols, plan = self.encode(sequence=0xfffffffe)
        handle = next(s['handle'] for s in symbols if s['name'] == self.row['RequestSymbol'])
        path = bytes((0x91, len(self.row['RequestSymbol']))) + self.row['RequestSymbol'].encode()
        path += b'\0' * (len(path) % 2)
        header = bytes((0x4d, len(path) // 2)) + path + struct.pack('<HHH', 0x02a0, 0xb000 | handle, 1)
        self.assertTrue(plan.payload_request.startswith(header))
        value = reader.decode_record(plan.payload_request[len(header):], handle, templates)
        self.assertEqual((value['SchemaVersion'], value['ManifestRevision'], value['StagedSequence']), (1, 4242, -2))
        self.assertEqual((value['JobSequence'], value['Chunk'], value['Status']), (12, 1, 1))
        chunk = value['Body']
        self.assertEqual(bytes.fromhex(chunk['Keys'][1]['bytes']).decode(), 'press.dwellMs')
        self.assertEqual((chunk['Keys'][2]['LEN'], chunk['Values'][:2]), (0, [-12, 2500]))
        self.assertTrue(plan.commit_request.endswith(struct.pack('<HHI', 0xc4, 1, 0xfffffffe)))
        self.assertNotIn('press.stroke', repr(plan))

    def test_a_sparse_chunk_is_completed_and_never_widened(self):
        body = binding.complete(dict(Kind=binding.RECORDS, Keys=['a', 'b'], Values=[1, 2]), 8)
        self.assertEqual((body['Keys'], body['Values'], body['Line'], body['Total']),
                         (['a', 'b', *[''] * 6], [1, 2, *[0] * 6], '', 0))
        for bad in (dict(Unknown=1), dict(Values=[0] * 9), dict(Keys='a')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                binding.complete(bad, 8)

    def test_the_encoder_refuses_rather_than_truncating_or_coercing(self):
        cases = [dict(Line='x' * 481), dict(Scope='a\0b'), dict(Keys=['k'] * 7), dict(Values=[1] * 9),
                 dict(Count=1 << 31), dict(Service=3), dict(Status='1'), dict(Revisions=[True] * 8)]
        for case in cases:
            with self.assertRaises(ValueError, msg=case):
                self.encode(**case)
        with self.assertRaisesRegex(ValueError, 'UInt32'):
            self.encode(sequence=1 << 32)
        templates, symbols = self.capture()
        ring = next(r for r in host.rows(self.app) if r['Service'] == 4)
        with self.assertRaisesRegex(ValueError, 'no writes'):
            binding.encode(ring, symbols, templates, 1, {}, {}, 1, connection_bytes=4000)
        with self.assertRaisesRegex(ValueError, 'minimum'):
            binding.encode(self.row, symbols, templates, 1, {}, {}, 1, connection_bytes=3999)


def physical(definitions, kind, value):
    if kind.startswith(pub.PREFIX + 'String'):
        raw = value.encode('utf-8')
        return dict(string=True, width=pub.string_width(kind), LEN=len(raw), bytes=raw.hex())
    if kind not in definitions:
        return value
    return {m.name: ([physical(definitions, m.kind, v) for v in value[m.name]] if m.count
                     else physical(definitions, m.kind, value[m.name])) for m in definitions[kind]}


class ManifestTable(unittest.TestCase):
    """V6.11 extends V6.10 additively: same tables, one more, one more owner row."""

    @classmethod
    def setUpClass(cls):
        cls.app = demo.application()
        cls.v610 = owner_fixture.fixture(cls.app)
        cls.definitions = pub.schema(cls.app)
        host.augment(cls.app, cls.definitions, snapshot_count=1)

    def record(self, *, hosts=None, ring_owner=True, mutate=None):
        n = self.v610['normalized']
        header = deepcopy(self.v610['physicalManifest'])
        hosts = deepcopy(host.rows(self.app) if hosts is None else hosts)
        owners = deepcopy(n['ownerReadBindings'])
        if ring_owner:
            parent = next(o for o in owners if o['CanonicalPrefix'] == self.app.name + '/Status')
            owners.append(dict(parent, CanonicalPrefix=self.app.name + '/HostEvents', MembersJson='[]',
                               RevisionSymbol='FRK_Press_HostRingRevision'))
        digest = wire.content_hash([], n['legacyContentHash'], n['publicationStage'], minor=11,
                                   bindings=n['bindings'], services=n['services'],
                                   type_annotations=n['typeAnnotations'], path_exceptions=n['pathExceptions'],
                                   products=n['dataProducts'], commands=n['commandBindings'],
                                   operations=n['commandOperations'],
                                   read_coherence_bindings=n['readCoherenceBindings'],
                                   read_services=n['readServices'], owner_read_bindings=owners,
                                   host_service_bindings=hosts)
        header.update(SchemaMinor=11, ContentHash=digest, ConfigRevision=wire.revision(digest),
                      OwnerReadBindings=owners, OwnerReadBindingsCount=len(owners),
                      OwnerReadBindingsCapacity=len(owners), HostServiceBindings=hosts,
                      HostServiceBindingsCount=len(hosts), HostServiceBindingsCapacity=len(hosts))
        if mutate:
            mutate(header)
        definitions = dict(self.definitions)
        kind = pub.header_type(self.app)
        definitions[kind] = tuple(pub.Member(m.name, m.kind, count=len(owners)) if m.name == 'OwnerReadBindings'
                                  else m for m in definitions[kind]) + tuple(
            pub.Member(m.name, m.kind, count=len(hosts)) if m.count else m for m in host.manifest_members(self.app))
        return physical(definitions, kind, header)

    def test_v611_normalizes_its_host_rows_into_the_hashed_document(self):
        normalized = wire.normalize(self.record())
        self.assertEqual(normalized['schemaMinor'], 11)
        self.assertEqual(normalized['hostServiceBindings'], host.rows(self.app))
        self.assertNotEqual(normalized['contentHash'], self.v610['normalized']['contentHash'])
        for key, value in self.v610['normalized'].items():
            if key not in ('schemaMinor', 'contentHash', 'configRevision', 'ownerReadBindings'):
                self.assertEqual(normalized[key], value, key)

    def test_a_row_changed_after_hashing_is_refused(self):
        def mutate(header):
            # Still a valid table: every ingress row moves together, unhashed.
            for row in header['HostServiceBindings']:
                if row['Service'] != 4:
                    row['MaximumChunkBytes'] = 3000
        with self.assertRaisesRegex(ValueError, 'hash'):
            wire.normalize(self.record(mutate=mutate))

    def test_cross_table_rules_refuse(self):
        rows = host.rows(self.app)
        with self.assertRaisesRegex(ValueError, 'owner-read'):
            wire.normalize(self.record(ring_owner=False))
        foreign = [dict(r, RootSymbol='Oven', **({'CanonicalRoot': 'Oven/HostEvents'} if r['Service'] == 4 else {}))
                   for r in rows]
        with self.assertRaisesRegex(ValueError, 'command binding'):
            wire.normalize(self.record(hosts=foreign))
        without_ring = [r for r in rows if r['Service'] != 4]
        with self.assertRaisesRegex(ValueError, 'owner-read|owner member'):
            wire.normalize(self.record(hosts=without_ring))

    def test_the_v610_record_is_unchanged_by_the_new_minor(self):
        record = physical(pub.schema(self.app), pub.header_type(self.app), self.v610['physicalManifest'])
        self.assertEqual(wire.normalize(record), self.v610['normalized'])


if __name__ == '__main__':
    unittest.main()

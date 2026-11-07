"""Verify stored values independently, including banks, masks and owner changes."""
from copy import deepcopy
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_live as live
import fraktal_ab_canonical_reader as canonical
import fraktal_ab_harness_documents as documents
import fraktal_ab_host_services as host
from fraktal_ab_live_medium import FileMedium
import test_fraktal_ab_host_service_binding as synthetic


class HostStatus(unittest.TestCase):
    def make(self):
        schema = synthetic.Schema()
        schema.setUp()
        templates, symbols = schema.capture()
        reader = object.__new__(live.CanonicalRowReader)
        row = dict(schema.row, ReplySymbol='UnrelatedReply')
        symbols[1]['name'] = row['ReplySymbol']
        reader._manifest = {'hostServiceBindings': [row]}
        reader._symbols = {s['name']: s for s in symbols}
        reader._objects, reader._sizes = canonical.template_objects(templates)
        handle = symbols[1]['handle']
        fields = {r['name']: r for r in canonical.member_table(reader._objects[handle])}
        raw = bytearray(reader._sizes[handle])
        for key, value in dict(SchemaVersion=1, Accepted=1, Restoring=1, SessionPermits=0, JobSequence=-1).items():
            struct.pack_into('<i', raw, fields[key]['offset'], value)
        calls = []
        reader._body = live.LeafBody(lambda location: calls.append(location) or bytes(raw))
        return reader, raw, fields, calls

    def test_one_native_cps_reply_follows_the_published_symbol_and_layout(self):
        reader, raw, fields, calls = self.make()
        result = reader.host_status('Press')
        self.assertEqual((result['Restoring'], result['SessionPermits'], result['JobSequence']), (1, 0, -1))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].symbol, 'UnrelatedReply')
        self.assertEqual(calls[0].width, len(raw))

    def test_fragmented_or_invalid_status_refuses_without_a_fake_row_proof(self):
        reader, raw, fields, calls = self.make()
        reader._manifest['hostServiceBindings'][0]['ConnectionBytes'] = len(raw)
        with self.assertRaisesRegex(ValueError, 'fragmentation'):
            reader.host_status('Press')
        self.assertEqual(calls, [])
        reader, raw, fields, calls = self.make()
        struct.pack_into('<i', raw, fields['Accepted']['offset'], 2)
        with self.assertRaisesRegex(ValueError, 'invalid host reply'):
            reader.host_status('Press')

    def test_unknown_root_or_incomplete_packet_returns_no_status(self):
        reader, raw, fields, calls = self.make()
        with self.assertRaises(ValueError):
            reader.host_status('Other')
        reader._body = live.LeafBody(lambda location: bytes(raw[:-1]))
        with self.assertRaises(ValueError):
            reader.host_status('Press')


class Reader:
    prefix = 'UnrelatedConfiguration/View'
    def __init__(self):
        self._manifest = dict(legacyContentHash='ABCDEF1234567890', readServices=[
            dict(RootSymbol='Press', Kind=1, Version=1, CanonicalRoot=self.prefix)])
        self.values = {self.prefix + '/' + n: v for n, v in dict(
            SchemaVersion=1, RootIdentity='Press', Revision=11, DefinitionCount=3, ValueCount=5).items()}
        defs = [('recipe.value', 0, 0, True), ('station.value', 1, 2, False), ('line.value', 2, 0, False)]
        for i, (key, kind, value_type, scoped) in enumerate(defs):
            for name, value in dict(DefinitionIndex=i, WriteKey=key, ConfigKind=kind,
                                    ValueType=value_type, ModelScoped=scoped).items():
                self.values[f'{self.prefix}/Definitions[{i}]/{name}'] = value
        rows = [(0, 0, '', '10'), (1, 0, '', '1'), (2, 0, '', '30'),
                (0, 1, 'M1', '41'), (0, 2, 'M2', '52')]
        for i, (index, bank, code, text) in enumerate(rows):
            for name, value in dict(DefinitionIndex=index, ModelOrdinal=bank, ModelCode=code,
                                    ValueText=text, Readable=True, Revision=11).items():
                self.values[f'{self.prefix}/Values[{i}]/{name}'] = value
        self.values.update({'Press/AvailableModelCount': 2, 'Press/Model/ModelCode': 'M2',
            'Press/AvailableModels[1]/ModelCode': 'M1', 'Press/AvailableModels[2]/ModelCode': 'M2',
            'Press/Status/ConfigRev': 11, 'Press/ConfigPersist/RestoreLost': False,
            'Press/ConfigPersist/Failed': False, 'Press/ConfigPersist/Pending': False})
        self.calls = []
        self.restoring = [0]

    def read_row(self, paths):
        self.calls.append(tuple(paths))
        return {'values': {p: self.values[p] for p in paths}}

    def host_status(self, root):
        value = self.restoring.pop(0) if len(self.restoring) > 1 else self.restoring[0]
        return dict(Restoring=value)


class Documents(unittest.TestCase):
    def test_live_contents_use_all_published_kinds_banks_and_boolean_text(self):
        reader = Reader()
        expected, epoch = documents.expected_documents(reader, 'Press')
        self.assertEqual(epoch, 11)
        self.assertEqual(set(expected), {'Press.station', 'Press.line', 'Press.model1', 'Press.model2'})
        self.assertEqual(expected['Press.station']['header']['model'], 'M2')
        self.assertEqual(expected['Press.station']['records']['station.value']['value'], 'TRUE')
        self.assertEqual(expected['Press.model1']['records']['recipe.value']['value'], '41')
        self.assertEqual(expected['Press.model2']['records']['recipe.value']['value'], '52')
        self.assertTrue(all(d['header']['configRev'] == 0xabcdef for d in expected.values()))
        self.assertTrue(any('Press/AvailableModels[2]/ModelCode' in call for call in reader.calls))

    def test_mask_duplicate_missing_bank_or_changed_epoch_never_passes(self):
        cases = [('Values[1]/Readable', False), ('Values[4]/ModelOrdinal', 1),
                 ('Definitions[1]/WriteKey', 'recipe.value'), ('Values[3]/ModelCode', 'Other'),
                 ('Values[2]/Revision', 12)]
        for path, value in cases:
            reader = Reader()
            reader.values[reader.prefix + '/' + path] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                documents.expected_documents(reader, 'Press')
        reader = Reader()
        reader.values['Press/Status/ConfigRev'] = 12
        with self.assertRaises(ValueError):
            documents.expected_documents(reader, 'Press')

    def test_read_only_medium_check_requires_every_value_and_a_confirmed_file(self):
        reader = Reader()
        expected, _ = documents.expected_documents(reader, 'Press')
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory)
            medium = FileMedium(store / 'live')
            self.assertFalse(documents.medium_matches(store, expected))
            for key, wanted in expected.items():
                medium.write(key, [dict(wanted['header'], schema=1, created=7, clock=0), *wanted['records'].values()])
            self.assertTrue(documents.medium_matches(store, expected))
            # FileMedium.read can reopen a valid file that was never confirmed.
            # The acceptance verifier must also require the authority index.
            index = store / 'live/index.json'
            confirmed = index.read_bytes()
            index.unlink()
            self.assertFalse(documents.medium_matches(store, expected))
            index.write_bytes(confirmed)
            self.assertTrue(documents.medium_matches(store, expected))
            wanted = expected['Press.model2']
            bad = deepcopy([dict(wanted['header'], schema=1, created=8, clock=0), *wanted['records'].values()])
            bad[1]['value'] = '51'
            medium.write('Press.model2', bad)
            self.assertFalse(documents.medium_matches(store, expected))

    def test_ready_waits_for_restore_and_all_documents_and_rejects_loss(self):
        reader = Reader()
        reader.restoring = [1, 0]
        session = NS(reader=reader, root='Press', expected_serial='601FC87B')
        now = [0.0]
        lease = NS(store=Path('unused'), guard=lambda **target: True, failure='', health={'state': 'kept'})
        with patch.object(documents.fixture, '_session', return_value=session), \
                patch.object(documents, 'medium_matches', side_effect=[False, True]) as medium:
            result = documents.ready(object(), object(), lease, timeout=1,
                clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s))
        self.assertTrue(result['wasRestoring'])
        self.assertEqual(medium.call_count, 2)
        self.assertEqual(len(result['confirmedKeys']), 4)
        reader.values['Press/ConfigPersist/RestoreLost'] = True
        with patch.object(documents.fixture, '_session', return_value=session), self.assertRaisesRegex(ValueError, 'loss'):
            documents.ready(object(), object(), lease)


if __name__ == '__main__':
    unittest.main()

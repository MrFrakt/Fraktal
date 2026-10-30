"""Cross-language peer apparatus preserves measured bytes, never claims ABI."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_reader as reader
import fraktal_ab_genealogy_s4b_owner_demo as demo
from fraktal_ab_owner_read_fixture import apparatus

ROOT = Path(__file__).resolve().parents[4]
CAPTURE = ROOT/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz'


class OwnerFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = CAPTURE.read_bytes()
        cls.original = json.loads(gzip.decompress(cls.raw))
        cls.capture = apparatus(demo.application(), cls.raw)

    def test_preserves_all_native_record_bytes_values_and_types(self):
        self.assertFalse(self.capture['apparatus']['nativeCapture'])
        self.assertEqual(self.original['records'], self.capture['records'])
        old, new = reader.snapshot(self.original), reader.snapshot(self.capture)
        self.assertEqual(new['nodeCount'], 5407)
        self.assertEqual(old['values'], new['values'])
        self.assertEqual(old['types'], new['types'])
        self.assertEqual(new['moduleCount'], 7)

    def test_missing_header_view_member_and_bad_counter_type_refuse(self):
        for change in ('missing', 'view', 'member', 'type'):
            c = deepcopy(self.capture)
            rows = c['manifest']['ownerReadBindings']
            if change == 'missing': rows.pop(1)
            elif change == 'view': rows.pop()
            elif change == 'member': rows[0]['MembersJson'] = '["Name","ModuleType","State"]'
            else:
                next(s for s in c['symbols'] if s['name']==rows[0]['RevisionSymbol'])['atomic']=0xc3
            with self.subTest(change=change), self.assertRaises(ValueError): reader.snapshot(c)

    def test_altered_source_cannot_be_silently_blessed_as_native(self):
        with self.assertRaisesRegex(ValueError, 'sealed'):
            apparatus(demo.application(), self.raw+b'changed')

    def acquire(self, capture):
        objects,sizes=reader.template_objects(capture['templates'])
        records={r['tag']:bytes.fromhex(r['rawHex']) for r in capture['records']}
        tags=[SimpleNamespace(TagName=s['name'],DataTypeValue=s.get('handle',s.get('atomic')),
                              Struct='handle' in s,Array=s.get('arrayRank',0)) for s in capture['symbols']]
        calls=[]
        class Comm:
            def GetDeviceProperties(self):
                return SimpleNamespace(Status='Success',Value=SimpleNamespace(SerialNumber='0x601FC87B'))
            def GetTagList(self,*,allTags):
                self.requested_all_tags=allTags
                return SimpleNamespace(Status='Success',Value=tags)
            def Read(self,name):
                calls.append(name)
                if name not in records:raise AssertionError('unexpected read '+name)
                return SimpleNamespace(Status='Success',Value=records[name])
        comm=Comm()
        with patch.object(reader,'discover_templates',return_value=objects), \
             patch.object(reader,'template_byte_size',side_effect=lambda comm,h:sizes[h]), \
             patch.object(reader,'template_structure_handle',return_value=40000):
            result,recorded=reader.read_document(comm,lambda *args:deepcopy(capture['manifest']),expect_serial='601FC87B')
        self.assertFalse(comm.requested_all_tags)
        self.assertEqual(set(calls),set(records))
        return result,recorded

    def test_live_acquisition_seam_records_all_owner_scalars_without_reading_command_payloads(self):
        actual,capture=self.acquire(self.capture)
        expected=reader.snapshot(self.capture)
        self.assertEqual(actual['values'],expected['values'])
        self.assertEqual(actual['types'],expected['types'])
        needed={b[k] for b in capture['manifest']['ownerReadBindings'] for k in ('RevisionSymbol','ProgressSymbol')}
        symbols={s['name']:s for s in capture['symbols']}
        self.assertTrue(all(symbols[n].get('atomic')==0xc4 and not symbols[n].get('arrayRank') for n in needed))
        self.assertEqual(len([s for s in capture['symbols'] if s['name'] in needed]),len(needed))

    def test_live_seam_refuses_missing_structured_array_or_non_dint_owner_counter(self):
        name=self.capture['manifest']['ownerReadBindings'][0]['RevisionSymbol']
        for change in ('missing','structured','array','atomic'):
            c=deepcopy(self.capture)
            symbol=next(s for s in c['symbols'] if s['name']==name)
            if change=='missing':c['symbols'].remove(symbol)
            elif change=='structured':symbol['handle']=1
            elif change=='array':symbol['arrayRank']=1
            else:symbol['atomic']=0xc3
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'DINT scalar'):
                self.acquire(c)


if __name__ == '__main__': unittest.main()

"""Cross-language peer apparatus preserves measured bytes, never claims ABI."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest

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


if __name__ == '__main__': unittest.main()

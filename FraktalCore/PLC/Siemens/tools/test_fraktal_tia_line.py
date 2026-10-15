"""Line declarations resolve against the same typed capabilities as config."""
import copy
import importlib.util
import unittest

from fraktal_tia_binding import Catalog, REPO
from fraktal_tia_declaration import DeclarationError
from fraktal_tia_line import Engine, Line

spec = importlib.util.spec_from_file_location('line_fixture', REPO/'FraktalCore/PLC/Siemens/Tests/Line/make_fixture.py')
FIX = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FIX)


class LineTests(unittest.TestCase):
    def engine(self, value=None, record=None):
        return Engine(Line.read(value or FIX.declaration(), ['StationA', 'StationB']),
                      Catalog.read([record or FIX.RECORD]))

    def test_all_values_are_line_kind_with_native_bounds_and_enum_domain(self):
        fields = self.engine().fields
        self.assertTrue(all(f.kind == Catalog.read().enums['E_ConfigKind']['LINE_CFG'] for f in fields))
        self.assertEqual(next(f for f in fields if f.member == 'Line.Small').maximum, 255)
        self.assertEqual(next(f for f in fields if f.member == 'Line.Grade').enum_values,
                         tuple(sorted(set(Catalog.read().enums['E_Mode'].values()))))

    def test_namespace_partial_duplicate_and_revision_errors_are_refused(self):
        for change in ('prefix', 'partial', 'duplicate', 'schema', 'revision', 'bound'):
            value = FIX.declaration()
            if change == 'prefix': value['values'][0]['key'] = 'taktMs'
            elif change == 'partial': value['values'].pop()
            elif change == 'duplicate': value['values'][-1]['key'] = value['values'][0]['key']
            elif change == 'schema': value['values'][0]['member'] = 'Line.SchemaVersion'
            elif change == 'revision': value['values'][0]['revision'] = 0
            else: value['values'][-1]['maximum'] = 256
            with self.subTest(change=change), self.assertRaises(DeclarationError): self.engine(value)

    def test_line_has_its_own_capacity_instead_of_module_twelve_value_limit(self):
        count = Catalog.read().capacities['MAX_LINE_RECORDS']
        value = FIX.declaration()
        value['values'] = [dict(member='Line.Slots[%d]'%n, key='line.slot.%d'%n,
                                revision=1, label='test.config.preset') for n in range(count)]
        record = ('ST_LineProbeConfig', 'STRUCT SchemaVersion : UINT := 1; Slots : ARRAY[0..%d] OF INT; END_STRUCT' % (count-1))
        self.assertEqual(len(self.engine(value, record).fields), count)
        value['values'].append(copy.deepcopy(value['values'][0]))
        value['values'][-1].update(member='Line.More', key='line.more')
        with self.assertRaises(DeclarationError): self.engine(value, record)

    def test_bad_roles_references_and_windows_fail_before_emission(self):
        for name, bad in (('role', 'MASTER'), ('roots', ['StationA', 'StationA']),
                          ('roots', ['StationA.Child']), ('id', 'x'*41), ('owner', ''),
                          ('stale_after_ms', True), ('stale_after_ms', 2147483648)):
            value = FIX.declaration(); value[name] = bad
            with self.subTest(name=name, bad=bad), self.assertRaises(DeclarationError): self.engine(value)

    def test_schema_and_storage_grammar_are_the_shared_config_rules(self):
        for record in ('STRUCT TaktMs : UDINT; SchemaVersion : UINT := 1; END_STRUCT',
                       FIX.RECORD[1].replace('SchemaVersion : UINT := 1', 'SchemaVersion : UINT := 0'),
                       FIX.RECORD[1].replace('Gain : LREAL', 'Gain : LTIME')):
            with self.subTest(record=record), self.assertRaises(DeclarationError):
                self.engine(record=(FIX.RECORD[0], record))


if __name__ == '__main__': unittest.main()

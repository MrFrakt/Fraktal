"""Schema completeness and native bounds for typed configuration providers."""
import importlib.util
import unittest

from fraktal_tia_binding import Catalog, REPO
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN

spec = importlib.util.spec_from_file_location('config_types', REPO/'FraktalCore/PLC/Siemens/Tests/ConfigTypes/make_fixture.py')
FIX = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FIX)


class ConfigTypeTests(unittest.TestCase):
    def build(self, value):
        return GEN.build(DECL.validate(value), True)

    def test_out_of_range_and_noncanonical_array_indices_are_not_capabilities(self):
        for target in ('Offsets[-2]', 'Offsets[2]', 'Offsets[01]', 'Offsets[+1]', 'Offsets[1+0]', 'Offsets'):
            value = FIX.declaration()
            field = next(f for f in value['types'][0]['config'] if f['key'] == 'offset.0')
            field['member'] = 'StationCfg.'+target
            with self.subTest(target=target), self.assertRaises(DECL.DeclarationError):
                self.build(value)

    def test_complete_model_regions_include_every_array_element(self):
        value = FIX.declaration()
        value['records']['ST_DeclarationParCfg'] = value['records']['ST_DeclarationParCfg'].replace('Preset : DINT := 10', 'Preset : ARRAY[-1..0] OF DINT')
        for module in value['types']:
            field = next(f for f in module['config'] if f['key'] == 'preset')
            field['member'] = 'ParCfg.Preset[-1]'
        with self.assertRaisesRegex(DECL.DeclarationError, 'complete ParCfg'):
            self.build(value)

    def test_storage_bounds_and_enum_domain_cannot_be_widened(self):
        for key, maximum in (('gain', 4e38), ('ratio', float('inf')), ('small', 256), ('grade', 100000)):
            value = FIX.declaration()
            field = next(f for f in value['types'][0]['config'] if f['key'] == key)
            field['maximum'] = maximum
            with self.subTest(key=key), self.assertRaises(DECL.DeclarationError):
                self.build(value)

    def test_float_initializers_cannot_smuggle_source_or_nonfinite_values(self):
        for initial in ('NaN', '1e309', '1e-400', '1.0 OR TRUE', 'INF', '1.0junk'):
            with self.subTest(initial=initial), self.assertRaises(ValueError):
                catalog = Catalog.read([('ST_TestCfg', 'STRUCT SchemaVersion : UINT := 1; Value : LREAL := '+initial+'; END_STRUCT')])
                catalog.resolve(['ST_TestCfg'])

    def test_native_subnormal_initializers_are_refused(self):
        for scalar, initial in (('REAL', '1e-40'), ('LREAL', '1e-310')):
            with self.subTest(scalar=scalar), self.assertRaisesRegex(ValueError, 'underflows native storage'):
                catalog = Catalog.read([('ST_TestCfg', 'STRUCT SchemaVersion : UINT := 1; Value : '+scalar+' := '+initial+'; END_STRUCT')])
                catalog.resolve(['ST_TestCfg'])


if __name__ == '__main__':
    unittest.main()

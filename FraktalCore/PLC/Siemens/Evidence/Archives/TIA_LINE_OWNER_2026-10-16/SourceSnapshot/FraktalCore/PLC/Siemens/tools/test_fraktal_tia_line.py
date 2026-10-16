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
spec = importlib.util.spec_from_file_location('line_owner_fixture', REPO/'FraktalCore/PLC/Siemens/Tests/Line/make_owner_fixture.py')
OWNER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(OWNER)


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

    def test_owner_declaration_round_trips_and_adds_no_registry_row(self):
        import fraktal_tia_generate as gen
        value = OWNER.declaration()
        model = gen.DECL.validate(value)
        sources, metadata = gen.build(model, True, line_workbench=True)
        self.assertEqual(metadata['declaration']['line'], value['line'])
        self.assertEqual(len(model.instances), 24)
        self.assertNotIn('RegIndex', sources['02_FRK_LineState.udt'])
        self.assertIn('FRK_LineManifest', ''.join(v for k,v in sources.items() if k.startswith('20_')))

    def test_line_restore_precedes_the_media_barrier_and_root_startup(self):
        import fraktal_tia_generate as gen
        sources, _ = gen.build(gen.DECL.validate(OWNER.declaration()), True, line_workbench=True)
        main = sources['30_FB_FraktalMain.scl']
        self.assertLess(main.index('"FRK_LineBoot"'), main.index('"FRK_DocBoot"'))
        self.assertLess(main.index('"FRK_DocBoot"'), main.index('"StationA"(ParentIndex'))
        self.assertLess(main.index('"FRK_PersistLineTick"'), main.index('"FRK_DocCyclic"'))

    def test_line_document_is_appended_and_shared_by_all_referencing_roots(self):
        import fraktal_tia_generate as gen
        value = OWNER.declaration()
        _, baseline = gen.build(gen.DECL.validate(OWNER.CONFIG.declaration()), True)
        sources, metadata = gen.build(gen.DECL.validate(value), True, line_workbench=True)
        previous = baseline['runtime']['persistence']['documents']
        documents = metadata['runtime']['persistence']['documents']
        self.assertEqual(documents[:-1], previous)
        self.assertEqual(documents[-1]['role'], 'line')
        self.assertLessEqual(documents[-1]['capacity'], Catalog.read().capacities['MAX_PERSIST_DOC_BYTES'])
        self.assertIn('IF #RootIndex = 1 OR #RootIndex = 2 THEN', sources['16_PersistStatus.scl'])
        self.assertIn('IF (#RootIndex = 1 OR #RootIndex = 2)', sources['16_PersistStatus.scl'])

    def test_unbound_mirrors_and_nonpersistent_lines_are_refused(self):
        import fraktal_tia_generate as gen
        for change in ('mirror', 'medium', 'nested-root'):
            value = OWNER.declaration()
            if change == 'mirror': value['line']['role'] = 'MIRROR'
            elif change == 'medium': value.pop('persistence')
            else: value['line']['roots'] = ['StationA.Satellite']
            with self.subTest(change=change), self.assertRaises(DeclarationError):
                gen.DECL.validate(value)

    def test_project_code_cannot_write_or_invoke_line_internals(self):
        import fraktal_tia_generate as gen
        for body in ('#Line.Revision := 3;', '#LineRevisionSeen := 3;', '"FRK_Line".Data.Dirty := TRUE;'):
            value = OWNER.declaration(); value['types'][0]['logic']['cyclic'] = body
            with self.subTest(body=body), self.assertRaises(DeclarationError):
                gen.build(gen.DECL.validate(value), True, line_workbench=True)

    def test_partial_line_profile_requires_explicit_workbench_generation(self):
        import fraktal_tia_generate as gen
        import tempfile
        from pathlib import Path
        model = gen.DECL.validate(OWNER.declaration())
        with self.assertRaisesRegex(DeclarationError, 'Core 1.5'):
            gen.build(model, True)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'frames'
            manifest = gen.generate(model, output, True, line_workbench=True)
            self.assertIs(manifest['line_workbench'], True)
            self.assertEqual(gen.verify(output), len(manifest['generated']))


if __name__ == '__main__': unittest.main()

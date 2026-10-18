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
    def test_calendar_contract_is_complete_and_uses_core_capacity(self):
        from fraktal_tia_line import calendar_contract
        facts=Catalog.read();fields,values,members=calendar_contract(facts)
        count=facts.capacities['MAX_WEEKLY_SHIFTS']
        record=('ST_CalendarBindingTest','STRUCT SchemaVersion : UINT := 1; '+fields+' END_STRUCT')
        line=Line.read(dict(id='TEST',owner='Owner',role='OWNER',roots=['StationA'],
            record=record[0],values=values,shifts=members,stale_after_ms=1000),['StationA'])
        engine=Engine(line,Catalog.read([record]))
        self.assertEqual(len(engine.fields),1+4*count)
        self.assertEqual({f.kind for f in engine.fields},{facts.enums['E_ConfigKind']['LINE_CFG']})
        self.assertIn('line.shift.%d.target'%count,{f.key for f in engine.fields})
        defaults=engine.sources()['05_FRK_LineDefaults.db']
        self.assertIn('Values.ShiftStartMin[%d] := -1;'%count,defaults)
        self.assertEqual(len({f.key for f in engine.fields}),len(engine.fields))

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
        for body in ('#Line.Revision := 3;', '#LineRevisionSeen := 3;', '"FRK_Line".Data.Dirty := TRUE;',
                     '"FRK_LineSetStage".Values.TaktMs := 1;', '"FRK_LineDefaults".Values.TaktMs := 1;'):
            value = OWNER.declaration(); value['types'][0]['logic']['cyclic'] = body
            with self.subTest(body=body), self.assertRaises(DeclarationError):
                gen.build(gen.DECL.validate(value), True, line_workbench=True)

    def test_line_sets_reuse_root_catalog_and_existing_persistence_slots(self):
        import fraktal_tia_generate as gen
        value = OWNER.declaration(); value['config_sets'] = {'capacity': 3}
        sources, metadata = gen.build(gen.DECL.validate(value), True, line_workbench=True)
        self.assertIn('Array[1..2, 1..3]', sources['05_FRK_SetStore.db'])
        self.assertIn('FRK_LineSetWalk', sources['18_LineSets.scl'])
        documents = metadata['runtime']['persistence']['documents']
        self.assertEqual(sum(d['role'] == 'set' for d in documents), 6)
        self.assertEqual(sum(d['role'] == 'line' for d in documents), 1)
        self.assertNotIn('LineSetStore', ''.join(sources))

    def test_line_set_capacity_is_complete_and_commit_is_owned_once(self):
        import fraktal_tia_generate as gen
        value = OWNER.declaration(); value['config_sets'] = {'capacity': 1}
        count = Catalog.read().capacities['MAX_LINE_RECORDS']
        value['records'][FIX.RECORD[0]] = 'STRUCT SchemaVersion : UINT := 1; Slots : ARRAY[0..%d] OF INT; END_STRUCT'%(count-1)
        value['line']['values'] = [dict(member='Line.Slots[%d]'%n, key='line.slot.%d'%n,
            revision=1, label='test.config.preset') for n in range(count)]
        sources, _ = gen.build(gen.DECL.validate(value), True, line_workbench=True)
        self.assertIn('Array[1..%d] of "ST_ConfigRecord"'%count, sources['02_FRK_SetPayload.udt'])
        self.assertEqual(sources['18_LineSets.scl'].count('"FRK_LineCommit"('), 1)
        self.assertIn('#Phase = 4 OR "FRK_Line".Ready', sources['18_LineSets.scl'])
        self.assertEqual(sources['17_Line.scl'].count('FUNCTION "FRK_LineCommit"'), 1)

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

    def test_complete_owner_and_bound_mirror_admit_without_workbench(self):
        import fraktal_tia_generate as gen
        spec=importlib.util.spec_from_file_location('line_complete_fixture',REPO/'FraktalCore/PLC/Siemens/Tests/Operations/make_frame_fixture.py')
        complete=importlib.util.module_from_spec(spec);spec.loader.exec_module(complete)
        value=complete.declaration()
        _,metadata=gen.build(gen.DECL.validate(value),True)
        self.assertNotIn('line_workbench',metadata)
        value['line']['role']='MIRROR'
        with self.assertRaisesRegex(DeclarationError,'bound .*image provider'):
            gen.build(gen.DECL.validate(value),True)
        value['line']['source']='F_TestLineImageSource'
        _,metadata=gen.build(gen.DECL.validate(value),True)
        self.assertNotIn('line_workbench',metadata)

    def test_public_profile_round_trip_preserves_admission(self):
        import fraktal_tia_generate as gen
        import tempfile
        from pathlib import Path
        spec=importlib.util.spec_from_file_location('line_roundtrip_fixture',REPO/'FraktalCore/PLC/Siemens/Tests/Operations/make_frame_fixture.py')
        complete=importlib.util.module_from_spec(spec);spec.loader.exec_module(complete)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'frames'
            manifest=gen.generate(gen.DECL.validate(complete.declaration()),out,True)
            self.assertNotIn('line_workbench',manifest)
            self.assertEqual(gen.verify(out),len(manifest['generated']))

    def test_bound_mirror_round_trip_and_restore_boot_order(self):
        import fraktal_tia_generate as gen
        value = OWNER.declaration(); value['config_sets'] = {'capacity': 2}
        value['line'].update(role='MIRROR', source='F_TestLineSource')
        model = gen.DECL.validate(value)
        sources, metadata = gen.build(model, True, line_workbench=True)
        self.assertEqual(metadata['declaration']['line']['source'], 'F_TestLineSource')
        main = sources['30_FB_FraktalMain.scl']
        self.assertLess(main.index('"FRK_LineBoot"(OwnerRole := FALSE'), main.index('"FRK_DocBoot"'))
        self.assertEqual(sources['17_Line.scl'].count('"F_TestLineSource"('), 1)
        self.assertIn('#Available AND #SourceError = 0', sources['17_Line.scl'])
        self.assertIn('OR "FRK_Line".Data.Applied THEN "FRK_PersistDirty"', sources['15_PersistMedium.scl'])
        self.assertNotIn('RegIndex', sources['05_FRK_LineSource.db'])
        root = ''.join(text for name,text in sources.items() if name.startswith('20_'))
        self.assertIn("LastRejectScope := 'BenchLineOwner'", root)

    def test_source_is_separate_and_owner_needs_no_provider(self):
        import fraktal_tia_generate as gen
        for source, role in (('FB_Bad','MIRROR'), ('F_Test','OWNER'), ('bad.name','MIRROR'), (True,'MIRROR')):
            value = OWNER.declaration(); value['line'].update(role=role,source=source)
            with self.subTest(source=source), self.assertRaises(DeclarationError):gen.DECL.validate(value)


if __name__ == '__main__': unittest.main()

"""Runtime catalog declaration admission and legacy compatibility."""
import importlib.util
from pathlib import Path
import unittest
from fraktal_tia_binding import Catalog
from fraktal_tia_declaration import DeclarationError
import fraktal_tia_generate as gen
from fraktal_tia_config import Layout
from fraktal_tia_models import Models

spec=importlib.util.spec_from_file_location('model_profile_fixture',Path(__file__).resolve().parents[1]/'Tests/DataClasses/make_fixture.py')
FIXTURE=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIXTURE)


class ModelProfileTests(unittest.TestCase):
    def service(self,value):
        model=gen.DECL.validate(value)
        return Models(Layout(model,Catalog.read(model.records)))

    def test_atomic_catalog_sizes_follow_consumed_records(self):
        value=FIXTURE.declaration();value['model_config']['capacity']=3
        service=self.service(value)
        self.assertEqual(service.records,max(len(rows) for rows in service.entries.values()))
        self.assertIn('FRK_ModelCapture_R1',service.typed_images())
        self.assertIn('FRK_ModelApply_R2',service.typed_images())
        self.assertLessEqual(len(service.key(1)),80)
        value['model_config']['capacity']=4
        with self.assertRaisesRegex(DeclarationError,'atomic runtime catalog data'):
            self.service(value)

    def test_model_identity_is_never_expanded_as_a_template_token(self):
        value=FIXTURE.declaration();value['model_config']['models'][0]='@CAPACITY@'
        value['model_config']['initial']='@CAPACITY@';value['model_config'].pop('seeds',None)
        value['model_config']['capacity']=3
        text=self.service(value).services()
        self.assertIn("#Catalog.Codes[1] <> '@CAPACITY@'",text)
        self.assertIn('#Catalog.Capacity <> 3',text)

    def test_missing_or_zero_capacity_keeps_runtime_creation_unavailable(self):
        value=FIXTURE.declaration();legacy=gen.definition(gen.DECL.validate(value))
        value['model_config']['capacity']=0
        model=gen.DECL.validate(value)
        self.assertEqual(model.model_capacity,0)
        self.assertEqual(gen.definition(model),legacy)

    def test_capacity_covers_seed_catalog_within_core_provider_bound(self):
        for capacity in (True,-1,1,2.5,Catalog.read().capacities['MAX_RECIPES']+1):
            value=FIXTURE.declaration();value['model_config']['capacity']=capacity
            with self.subTest(capacity=capacity),self.assertRaises(DeclarationError):gen.DECL.validate(value)

    def test_capacity_round_trip_and_atomic_medium(self):
        value=FIXTURE.declaration();value['model_config']['capacity']=3
        model=gen.DECL.validate(value)
        self.assertEqual(model.model_capacity,3)
        self.assertEqual(gen.definition(model)['model_config']['capacity'],3)
        sources,manifest=gen.build(model,True,line_workbench=True)
        documents=manifest['runtime']['persistence']['documents']
        self.assertEqual([d['root'] for d in documents if d['role']=='models'],[1,2])
        self.assertIn('FRK_ModelApply',sources['19_ModelServices.scl'])
        self.assertIn('FRK_PersistModelsSaved',sources['19_ModelServices.scl'])
        self.assertIn('ModelCapacity',next(s for s in sources.values() if 'FUNCTION_BLOCK "'+model.roots[0].type_name+'"' in s))
        frame=next(s for s in sources.values() if 'FUNCTION_BLOCK "'+model.roots[0].type_name+'"' in s)
        import tempfile
        import tia_lint
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            for filename,text in sources.items():(directory/filename).write_bytes(text.encode('ascii'))
            self.assertEqual([str(f) for f in tia_lint.lint([directory])],[])
        value['model_config'].pop('capacity')
        _,legacy=gen.build(gen.DECL.validate(value),True,line_workbench=True)
        self.assertEqual([(d['index'],d['key'],d['role']) for d in documents[:len(legacy['runtime']['persistence']['documents'])]],
                         [(d['index'],d['key'],d['role']) for d in legacy['runtime']['persistence']['documents']])

    def test_complete_set_source_dependency_is_explicit(self):
        value=FIXTURE.declaration();value['model_config']['capacity']=3;value.pop('config_sets')
        with self.assertRaisesRegex(DeclarationError,'parameter-set source support'):
            gen.build(gen.DECL.validate(value),True,line_workbench=True)

    def test_project_logic_cannot_write_catalog_or_call_its_private_services(self):
        for code in ('#ModelCapacity := 4;', '#ModelGenerationSeen := 0;',
                     '"FRK_ModelStore".Rows[1].Count := 4;', '"FRK_ModelDefaults"(RootIndex := 1);'):
            value=FIXTURE.declaration();value['model_config']['capacity']=3
            unit=next(t for t in value['types'] if t['name']==value['roots'][0]['type'])
            unit['logic']['cyclic']+='\n'+code
            with self.subTest(code=code),self.assertRaises(DeclarationError):
                gen.build(gen.DECL.validate(value),True,line_workbench=True)

    def test_local_retain_uses_same_catalog_transaction_without_load_db(self):
        value=FIXTURE.declaration();value['model_config']['capacity']=3;value.pop('persistence')
        value['records'].pop(value.pop('line')['record'])
        sources,manifest=gen.build(gen.DECL.validate(value),True,line_workbench=True)
        self.assertEqual(manifest['runtime']['models']['retention'],'LOCAL_RETAIN')
        self.assertIn('#FRK_ModelSaved := TRUE;',sources['19_ModelServices.scl'])
        import tia_lint
        frame=next(s for s in sources.values() if 'FUNCTION_BLOCK "'+value['roots'][0]['type']+'"' in s)
        block=next(b for b in tia_lint.parse_blocks(frame) if b.kind=='FUNCTION_BLOCK')
        self.assertEqual(next(d.section for d in block.decls if d.name=='OutImm'),'VAR')
        self.assertNotIn('ConfigCaptureOutImm',frame)


if __name__=='__main__':unittest.main()

"""Class declaration admission, durable layout compatibility and shared enforcement."""
import copy
import importlib.util
from pathlib import Path
import unittest

import fraktal_tia_generate as gen
from fraktal_tia_binding import Catalog
from fraktal_tia_data_classes import effective_level
from fraktal_tia_declaration import DeclarationError

PATH=Path(__file__).resolve().parents[1]/'Tests/DataClasses/make_fixture.py'
spec=importlib.util.spec_from_file_location('class_fixture_tests',PATH)
FIXTURE=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIXTURE)


class DataClassTests(unittest.TestCase):
    def test_root_type_lookup_keeps_iec_case_insensitivity(self):
        value=FIXTURE.declaration();value['roots'][0]['type']='FB_'+value['roots'][0]['type'][3:].lower()
        self.assertEqual(len(gen.DECL.validate(value).data_classes),2)

    def test_project_logic_cannot_mutate_class_authority(self):
        for body in ('"FRK_ClassPolicies".Rows[1].Generation := 0;',
                     '"FRK_ClassSave"(Access := #Access, Scope := \'StationA\');'):
            value=FIXTURE.declaration();value['types'][0]['logic']['Cyclic']=body
            with self.subTest(body=body),self.assertRaises(DeclarationError):gen.build(gen.DECL.validate(value),True,line_workbench=True)

    def test_classes_only_belong_to_deployed_root_units(self):
        for root in ('StationA.Satellite','Missing'):
            v=FIXTURE.declaration();v['data_classes'][root]=v['data_classes'].pop('StationA')
            with self.subTest(root=root),self.assertRaises(DeclarationError):gen.DECL.validate(v)

    def test_invalid_thresholds_ids_duplicates_and_capacity_refused(self):
        original=FIXTURE.declaration()
        for key,value in (('id',''),('id','x'*41),('id','\u00e9'),('label','x'*161),('read_level',True),('write_level',5),('read_level',-1)):
            v=copy.deepcopy(original);v['data_classes']['StationA'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(DeclarationError):gen.DECL.validate(v)
        for rows in ([],[original['data_classes']['StationA'][0]]*2,
                     [dict(id='c'+str(i),label='test.config.preset',read_level=0,write_level=0) for i in range(Catalog.read().capacities['MAX_DATA_CLASSES']+1)]):
            v=copy.deepcopy(original);v['data_classes']['StationA']=rows
            with self.subTest(rows=len(rows)),self.assertRaises(DeclarationError):gen.DECL.validate(v)

    def test_classes_round_trip_without_changing_existing_policy_documents(self):
        v=FIXTURE.declaration();model=gen.DECL.validate(v)
        self.assertEqual(gen.definition(model)['data_classes'],v['data_classes'])
        sources,meta=gen.build(model,True,line_workbench=True)
        old=copy.deepcopy(v);old.pop('data_classes')
        previous,oldmeta=gen.build(gen.DECL.validate(old),True,line_workbench=True)
        existing=oldmeta['runtime']['persistence']['documents']
        self.assertEqual(meta['runtime']['persistence']['documents'][:len(existing)],existing)
        self.assertEqual(previous['02_FRK_AccessPolicyImage.udt'],sources['02_FRK_AccessPolicyImage.udt'])
        self.assertEqual(len(meta['runtime']['persistence']['documents'])-len(existing),2)
        self.assertIn('VAR RETAIN',sources['05_FRK_ClassPolicies.db'])
        frame=next(s for n,s in sources.items() if n.endswith('FB_DeclarationUnit.scl'))
        self.assertIn('"FRK_ClassBoot"',frame);self.assertIn('"FRK_ClassOperation"',frame)
        self.assertIn('"FRK_PersistClassesDirty"',sources['13_UnitServices.scl'])

    def test_one_effective_level_for_module_line_and_set_paths(self):
        sources,_=gen.build(gen.DECL.validate(FIXTURE.declaration()),True,line_workbench=True)
        all_text='\n'.join(sources.values())
        self.assertNotIn('MAX(IN1 := #Access.Policy.Required[1], IN2 := "FRK_ConfigScratch".MinWrite)',all_text)
        self.assertNotIn('MAX(IN1 := #Access.Policy.Required[0], IN2 := "FRK_ConfigScratch".MinRead)',all_text)
        self.assertIn(effective_level(True),all_text)
        self.assertIn('IF #Phase = 5 AND',all_text)
        self.assertIn('IF NOT #WriteAccess AND',all_text)
        self.assertIn('Entry.ClassId := \'undeclared\'',all_text)


if __name__=='__main__':unittest.main()

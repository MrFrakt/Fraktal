"""Named-set deployment bounds, owner isolation and authority accounting."""
import unittest
from test_fraktal_tia_config import FIX
from fraktal_tia_binding import Catalog
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN


class SetTests(unittest.TestCase):
    def test_project_root_cannot_shadow_a_new_framework_store(self):
        value=FIX.declaration();value['config_sets']={'capacity':1};value['roots'][0]['name']='FRK_SetStore'
        with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)

    def test_store_is_opt_in_and_capacity_is_a_core_bound(self):
        for capacity in (-1, True, Catalog.read().capacities['MAX_CONFIG_SETS']+1):
            value=FIX.declaration();value['config_sets']={'capacity':capacity}
            with self.subTest(capacity=capacity),self.assertRaises(DECL.DeclarationError):DECL.validate(value)
        sources,_=GEN.build(DECL.validate(FIX.declaration()),True)
        self.assertNotIn('05_FRK_SetStore.db',sources)

    def test_set_deployment_survives_declaration_roundtrip(self):
        value=FIX.declaration();value['config_sets']={'capacity':3}
        model=DECL.validate(value)
        sources,manifest=GEN.build(model,True)
        self.assertEqual(manifest['declaration']['config_sets'],{'capacity':3})
        self.assertEqual(DECL.validate(manifest['declaration']).config_set_capacity,3)
        self.assertIn('Array[1..2, 1..3]',sources['05_FRK_SetStore.db'])
        self.assertIn('Array[1..2] of "FRK_SetWorkspace"',sources['05_FRK_SetRuntime.db'])
        self.assertIn('Array[1..24] of "ST_ConfigRecord"',sources['02_FRK_SetPayload.udt'])
        self.assertIn('Framework/Core/config_set_services.scl.in','\n'.join(manifest['runtime']['authority_inputs']))

    def test_project_cannot_mutate_published_set_results_or_private_store(self):
        for logic in ('#ConfigSetCount := 1;', '#ConfigSets[1].SetName := \'forged\';', '"FRK_SetStore".SchemaVersion := 99;', '"FRK_SetBoot"(Startup := TRUE);'):
            value=FIX.declaration();value['config_sets']={'capacity':1};value['types'][0]['logic']['Cyclic']=logic
            with self.subTest(logic=logic),self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)


if __name__=='__main__':unittest.main()

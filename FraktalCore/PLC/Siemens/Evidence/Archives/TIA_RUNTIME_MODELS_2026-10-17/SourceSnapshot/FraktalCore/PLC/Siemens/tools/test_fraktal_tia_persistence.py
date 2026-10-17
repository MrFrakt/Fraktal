import copy
import importlib.util
from pathlib import Path
import unittest

import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
from fraktal_tia_binding import REPO

spec=importlib.util.spec_from_file_location('config_fixture',REPO/'FraktalCore/PLC/Siemens/Tests/Config/make_fixture.py')
FIXTURE=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIXTURE)


class PersistenceDeclaration(unittest.TestCase):
    def setUp(self):
        self.value=FIXTURE.declaration()
        self.value['persistence']={'medium':'LOAD_DB','minimum_write_ms':1000,'queue_capacity':2}

    def test_profile_roundtrip(self):
        model=DECL.validate(self.value)
        again=DECL.validate(GEN.definition(model))
        self.assertEqual(model,again)

    def test_invalid_media_and_limits(self):
        for field,values in {'medium':['CARD_FILE','EXTERNAL',''], 'minimum_write_ms':[False,0,999,86400001], 'queue_capacity':[False,0,9]}.items():
            for value in values:
                declaration=copy.deepcopy(self.value);declaration['persistence'][field]=value
                with self.subTest(field=field,value=value),self.assertRaises(DECL.DeclarationError):DECL.validate(declaration)

    def test_empty_profile_allocates_nothing(self):
        self.value.pop('persistence')
        sources,_=GEN.build(DECL.validate(self.value),True)
        self.assertFalse(any('PersistMedium' in name or 'FRK_Load_D' in name for name in sources))

    def test_invalid_derived_keys_are_rejected(self):
        self.value['model_config']['models'][0]='invalid/model'
        self.value['model_config']['initial']='invalid/model'
        with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(self.value),True)

    def test_consumed_document_geometry(self):
        sources,_=GEN.build(DECL.validate(self.value),True)
        banks=[n for n in sources if n.startswith('06_FRK_Load_D')]
        # Two roots, station + two models + policy per root, and one user table.
        self.assertEqual(len(banks),18)
        self.assertTrue(all('UNLINKED' in sources[n] for n in banks))

    def test_decimal_config_limits_generate_native_numbers(self):
        for t in self.value['types']:
            t['config'][1]['minimum']=0.0
            t['config'][1]['maximum']=1000.0
        sources,_=GEN.build(DECL.validate(self.value),True)
        self.assertNotIn('1000.0.0',sources['15_PersistMedium.scl'])
        self.assertIn('Maximum := 1000.0',sources['15_PersistMedium.scl'])

    def test_named_set_apply_queues_its_live_document(self):
        self.value['config_sets']={'capacity':2}
        sources,_=GEN.build(DECL.validate(self.value),True)
        walks=[s for s in sources.values() if 'FUNCTION "FRK_CfgSetWalk_' in s]
        self.assertTrue(walks)
        for source in walks:
            self.assertIn('"FRK_ConfigCommit"(',source)
        commit=sources['14_ConfigServices.scl']
        self.assertIn('IF #Changed THEN "FRK_ConfigChanged"(',commit)
        self.assertIn('"FRK_PersistConfigSlot"(Scope := #Scope, ModelCode := #ModelCode, Kind := #Kind)',commit)
        self.assertIn('"FRK_PersistModelDirty"(RootIndex := #RootIndex)',commit)

    def test_restore_barrier_withdraws_selected_view_through_owning_quiesce(self):
        self.value['types'][0]['sequence_view']={'capacity':4,'branches':2,'annotations':2}
        sources,_=GEN.build(DECL.validate(self.value),True)
        text=sources['23_PersistQuiesce.scl']
        self.assertIn('"FRK_SeqViewWithdraw"(Owner := #Module.Core.RegIndex);',text)
        self.assertIn('#Module.ActiveSteps := "FRK_Views".V001.Cursors;',text)
        self.assertIn('#Module.CurrentStepElapsed := "FRK_Views".V001.Cursors[0].Elapsed;',text)
        # Row history survives the barrier; normal startup/mode clear owns reset.
        withdraw=sources['17_SequenceView.scl'].split('FUNCTION "FRK_ViewWithdraw"',1)[1].split('END_FUNCTION',1)[0]
        self.assertNotIn('#Count :=',withdraw)
        self.assertNotIn('#Rows[',withdraw)
        self.assertNotIn('"FRK_SeqViewWithdraw"',sources['40_Main.scl'])


if __name__=='__main__':unittest.main()

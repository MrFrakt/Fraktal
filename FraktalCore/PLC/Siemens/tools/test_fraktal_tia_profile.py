import importlib.util,tempfile,unittest
from pathlib import Path
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import fraktal_tia_examples as EX
from fraktal_tia_binding import Catalog

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('view_fixture',HERE/'Tests/SequenceView/make_fixture.py')
FIXTURE=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIXTURE)

class ProfileTests(unittest.TestCase):
    def test_unselected_station_pays_no_profile_storage(self):
        sources,_=GEN.build(DECL.validate(FIXTURE.CONFIG.declaration()),True)
        self.assertFalse(any('FRK_Profiles' in s for s in sources.values()))

    def test_profile_arrays_are_consumed_and_core_bounded(self):
        value=FIXTURE.select(FIXTURE.CONFIG.declaration())
        value['types'][0]['sequence_view']['capacity']=100
        sources,_=GEN.build(DECL.validate(value),True)
        name='FRK_CycleProfile_'+value['types'][0]['name'].removeprefix('FB_')
        self.assertIn('Array[1..'+str(Catalog.read().capacities['MAX_PROFILE_STEPS'])+']',sources['07_'+name+'.udt'])
        value['types'][0]['sequence_view']['capacity']=3
        sources,_=GEN.build(DECL.validate(value),True)
        self.assertIn('Array[1..3]',sources['07_'+name+'.udt'])

    def test_frame_and_step_own_profile_and_finish_flush(self):
        sources,_,_=EX.build()
        frame=sources['29_FB_PressDemoUnit.scl']
        self.assertIn('"FRK_SeqProfilePrepare"',frame)
        self.assertLess(frame.index('"FRK_SeqViewEnd"'),frame.index('"FRK_SeqProfileEnd"'))
        self.assertLess(frame.index('"FRK_Begin"'),frame.index('"FRK_SeqProfilePrepare"'))
        self.assertLess(frame.index('"FRK_End"'),frame.index('"FRK_SeqProfileEnd"'))
        self.assertIn('FRK_SeqProfileStep',sources['17_SequenceView.scl'])
        self.assertIn('IF #Seq.BranchIndex = 0',sources['16_SequenceServices.scl'])
        self.assertIn('FRK_SeqProfileComplete',sources['16_SequenceServices.scl'])
        self.assertNotIn('FRK_Profile',sources['40_PressDemoMain.scl'])

    def test_authored_logic_cannot_write_profiler(self):
        value=FIXTURE.select(FIXTURE.CONFIG.declaration())
        value['types'][0]['logic']['cyclic']='#Profiler.HistoryHead := 0;'
        with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)

    def test_replay_binds_profile_source(self):
        model=DECL.validate(FIXTURE.select(FIXTURE.CONFIG.declaration()))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'generated';GEN.generate(model,out,True)
            GEN.verify(out)
            p=out/'18a_CycleProfile.scl';p.write_bytes(p.read_bytes().replace(b'#Book.Last := #Book.Current',b'#Book.Last := #Book.Last'))
            with self.assertRaises(DECL.DeclarationError):GEN.verify(out)

if __name__=='__main__':unittest.main()

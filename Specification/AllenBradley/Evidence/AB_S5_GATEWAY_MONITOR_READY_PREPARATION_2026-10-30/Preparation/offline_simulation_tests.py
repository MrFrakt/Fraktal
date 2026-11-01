from pathlib import Path
import json,tempfile,unittest
from types import SimpleNamespace
from simulation_input import change,TAG
class Simulation(unittest.TestCase):
    def test_fixed_tag_is_a_declared_externally_writable_simulation_input(self):
        import sys
        sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
        import fraktal_ab_genealogy_s4b_owner_demo as fixture
        import fraktal_ab_generate as generator
        app=fixture.application()
        self.assertIn(TAG,app.sim_inputs)
        self.assertIn(TAG,generator.externally_writable(app))
    def test_original_zero_or_one_is_restored_exactly(self):
        for initial in (0,1):
            class Fake:
                value=initial
                def Read(self,tag):
                    self_tag=tag;assert self_tag==TAG
                    return SimpleNamespace(Status='Success',Value=self.value)
                def Write(self,tag,value):
                    assert tag==TAG and type(value) is int;self.value=value
            with self.subTest(initial=initial),tempfile.TemporaryDirectory() as temp:
                comm=Fake();directory=Path(temp)
                change(comm,directory,'prepare');self.assertEqual(comm.value,1)
                change(comm,directory,'restore');self.assertEqual(comm.value,initial)
                self.assertTrue(json.loads((directory/'simulation_restored.json').read_bytes())['passed'])
    def test_wrong_saved_tag_cannot_write(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            (directory/'simulation_original.json').write_text(json.dumps(dict(serial='601FC87B',tag='Other',original=0)))
            with self.assertRaisesRegex(ValueError,'scope'):change(None,directory,'restore')
    def test_no_repeated_preparation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);(directory/'simulation_original.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Single-use'):change(None,directory,'prepare')
if __name__=='__main__':unittest.main()

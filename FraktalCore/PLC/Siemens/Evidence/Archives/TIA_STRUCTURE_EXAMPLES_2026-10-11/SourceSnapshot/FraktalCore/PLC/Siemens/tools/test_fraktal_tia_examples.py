"""Reject graph corruption that a source hash or clean compiler cannot detect."""
from pathlib import Path
import tempfile
import unittest

import fraktal_tia_examples as EX
import fraktal_tia_ld as LD
from fraktal_tia_program_layout import split_main


class NativeGraphGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources, _, _ = EX.build()
        cls.ladder = cls.sources['26_FB_LD_PressDemoHome.xml']

    def compare(self, mutated):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = Path(tmp)/'before.xml', Path(tmp)/'after.xml'
            before.write_text(self.ladder, encoding='ascii')
            after.write_text(mutated, encoding='ascii')
            return LD.parity(before, after)

    def test_valid_but_wrong_return_connection_is_detected(self):
        self.assertIn('Name="Ret_Val"', self.ladder)
        changed = self.ladder.replace('Name="Ret_Val" />', 'Name="eno" />', 1)
        with self.assertRaisesRegex(ValueError, 'graph changed'):
            self.compare(changed)

    def test_valid_but_wrong_step_operand_is_detected(self):
        changed = self.ladder.replace('<ConstantValue>900</ConstantValue>', '<ConstantValue>0</ConstantValue>', 1)
        self.assertNotEqual(changed, self.ladder)
        with self.assertRaisesRegex(ValueError, 'graph changed'):
            self.compare(changed)

    def test_missing_called_node_is_rejected(self):
        changed = self.ladder.replace('<Call UId=', '<MissingCall UId=', 1).replace('</Call>', '</MissingCall>', 1)
        with self.assertRaisesRegex(ValueError, 'Unsupported part'):
            LD.dump(changed)

    def test_interface_pin_order_is_serialization_only(self):
        self.assertGreater(self.compare(self.ladder)['calls'], 0)


class MainExtraction(unittest.TestCase):
    def test_order_startup_and_local_scope_are_preserved(self):
        source='''ORGANIZATION_BLOCK "Main"
VAR_INPUT
    Initial_Call : Bool;
END_VAR
VAR_TEMP
    Prepared : Int;
    Observed : Int;
END_VAR
BEGIN
    #Prepared := 1;
    IF #Initial_Call THEN "Inputs".Value := #Prepared; END_IF;
    "GDB_FraktalMain"(Startup := #Initial_Call);
    #Observed := "Outputs".Value;
END_ORGANIZATION_BLOCK
'''
        main, routines=split_main(source)
        self.assertNotIn('VAR_TEMP', main)
        self.assertLess(main.index('F_ConfigBenchPrepare'), main.index('GDB_FraktalMain'))
        self.assertLess(main.index('GDB_FraktalMain'), main.index('F_ConfigBenchObserve'))
        before, after=routines.split('FUNCTION "F_ConfigBenchObserve"')
        self.assertIn('#Startup', before)
        self.assertNotIn('Observed', before)
        self.assertNotIn('Prepared', after)


if __name__=='__main__':
    unittest.main()

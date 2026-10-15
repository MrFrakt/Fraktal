"""Reject graph corruption that a source hash or clean compiler cannot detect."""
from pathlib import Path
import tempfile
import unittest

import fraktal_tia_examples as EX
import fraktal_tia_ld as LD
from fraktal_tia_program_layout import split_main
import fraktal_tia_graph as GRAPH
import json
import re


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


class PressRecoveryGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources,cls.definition,_=EX.build()
        cls.xml=cls.sources['27_FB_GRAPH_PressDemoAuto.xml']

    def test_graph_contains_the_two_recovery_exits_and_real_parallel_join(self):
        chart=GRAPH.dump(self.xml)
        self.assertEqual(len(chart['steps']),19)
        self.assertEqual([b['Type'] for b in chart['branches']],['AltBegin','SimBegin','AltBegin','AltEnd','SimEnd'])
        text=json.dumps(chart)
        self.assertIn('#Seq.RetVal',text)
        self.assertIn('#Branch1.RetVal',text)
        self.assertIn('#Branch2.RetVal',text)
        auto=next(c for c in self.definition['chains'] if c.get('process')=='auto')
        st=self.sources['23_FB_PressDemoAuto.scl']
        for step in auto['steps']:
            if 'jump1' in step:
                self.assertIn('OnAdvance := '+str(step['next'])+', OnJump1 := '+str(step['jump1']),st)

    def test_changed_comparison_wire_is_detected_even_with_identical_operands(self):
        altered=self.xml.replace('Name="pre" />','Name="in1" />',1)
        self.assertNotEqual(GRAPH.dump(self.xml),GRAPH.dump(altered))

    def test_chart_parameter_alias_cannot_be_discovered_as_another_root(self):
        self.assertIn('Name="HostStatus"',self.xml)
        self.assertNotIn('Member Name="Status"',self.xml)

    def test_main_is_a_calling_routine_and_optional_renditions_have_no_instances(self):
        main=self.sources['40_PressDemoMain.scl']
        body=main.split('\nBEGIN\n',1)[1].split('END_ORGANIZATION_BLOCK')[0]
        self.assertEqual(re.findall(r'"(\w+)"\(',body),['F_PressDemoReadInputs','GDB_FraktalMain','F_PressDemoWriteOutputs'])
        dbs='\n'.join(v for n,v in self.sources.items() if n.endswith('.db'))
        self.assertNotIn('"FB_LD_',dbs)
        self.assertNotIn('"FB_PressDemoAuto"',dbs)
        self.assertIn('"FB_GRAPH_PressDemoAuto"',dbs)


if __name__=='__main__':
    unittest.main()

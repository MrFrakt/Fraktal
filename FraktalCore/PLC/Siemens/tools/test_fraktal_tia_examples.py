"""Reject graph corruption that a source hash or clean compiler cannot detect."""
from pathlib import Path
import tempfile
import unittest

import fraktal_tia_examples as EX
import fraktal_tia_ld as LD
from fraktal_tia_program_layout import split_main, group
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
    def test_fixture_routines_and_sink_do_not_enter_core_groups(self):
        self.assertEqual(group('39c_AlarmPersistenceBench.scl','FUNCTION "F_AlarmPersistenceBench" : Void'),'Tests/ConfigBench/Fixtures')
        self.assertEqual(group('08_EventSink.scl','FUNCTION "F_TestEventSink" : Void'),'Tests/ConfigBench/Fixtures')
        self.assertEqual(group('13_UnitServices.scl','FUNCTION "FRK_AlarmHistoryBoot" : Void'),'Framework/Core')


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


class PressCommittedReplay(unittest.TestCase):
    def test_committed_press_replays_from_its_declaration(self):
        # A generator, template or press.json change must refresh the committed tree.
        self.assertGreater(EX.verify(Path(__file__).resolve().parents[1]/'Examples/PressDemo/generated')['replayed_sources'],0)


class PressOutputForcing(unittest.TestCase):
    def engineering(self):
        definition=json.loads((EX.EXAMPLE/'press.json').read_bytes())
        definition['integration']['output_forcing']=True
        return EX.build(definition)

    def test_shipped_press_has_no_force_surface(self):
        sources,definition,manifest=EX.build()
        self.assertFalse(definition['integration']['output_forcing'])
        self.assertFalse(any('FRK_Force' in text for text in sources.values()))
        self.assertNotIn('OUTPUT_FORCING',json.dumps(manifest['declaration']['engineering_gates']))

    def test_engineering_press_wires_request_permit_and_driver_apply_once(self):
        sources,_,manifest=self.engineering()
        unit=sources['29_FB_PressDemoUnit.scl'];driver=sources['38_PressDemoHardwareDriver.scl']
        self.assertEqual(unit.count('"FRK_ForceRequest"('),1)
        self.assertEqual(unit.count('"FRK_ForceTick"('),1)
        self.assertLess(unit.index('"FRK_AlarmShelfRequest"('),unit.index('"FRK_ForceRequest"('))
        self.assertLess(unit.index('"FRK_EngineeringTick"('),unit.index('"FRK_ForceTick"('))
        # Applied only in the physical-output branch, after the demand is written.
        branch=driver[driver.index('    ELSIF #USE_SIMULATION THEN'):]
        self.assertLess(branch.index('"GDB_PressDemoIO".StartLamp := "PressDemo"'),branch.index('"F_PressDemoApplyForces"();'))
        self.assertLess(branch.index('    ELSE\n'),branch.index('"F_PressDemoApplyForces"();'))
        self.assertEqual(sources['38_GDB_PressDemoFieldbus.db'].count('Forceable := TRUE'),6)
        gates={g['name']:g['active'] for g in manifest['declaration']['engineering_gates']}
        self.assertEqual(gates,{'USE_SIMULATION':True,'OUTPUT_FORCING':True})
        # The control-power coils and the shared lamp member are never forceable.
        self.assertNotIn('_000K9',sources['38_F_PressDemoApplyForces.scl'])
        self.assertNotIn('StartLamp',sources['38_F_PressDemoApplyForces.scl'])


class PressGraphRenditionGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources, cls.definition, _ = EX.build()

    def test_changeover_rendition_parity(self):
        xml = self.sources['27_FB_GRAPH_PressDemoChangeover.xml']
        scl = self.sources['23_FB_PressDemoChangeover.scl']
        ok, only_g, only_s = GRAPH.parity(xml, scl)
        self.assertTrue(ok)
        self.assertEqual(only_g, set())
        self.assertEqual(only_s, set())
        edges = {(e['from'], e['to']) for e in GRAPH.dump(xml)['edges']}
        self.assertIn((880, 810), edges)
        self.assertIn((880, 999), edges)

    def test_changeover_mutation_detected(self):
        xml = self.sources['27_FB_GRAPH_PressDemoChangeover.xml']
        scl = self.sources['23_FB_PressDemoChangeover.scl']
        mutated_scl = scl.replace('OnJump1 := 810', 'OnJump1 := 800')
        ok, only_g, only_s = GRAPH.parity(xml, mutated_scl)
        self.assertFalse(ok)
        self.assertEqual(only_g, {(880, 810)})
        self.assertEqual(only_s, {(880, 800)})

    def test_load_position_rendition_parity(self):
        xml = self.sources['27_FB_GRAPH_PressDemoLoadPosition.xml']
        scl = self.sources['23_00_FB_PressDemoLoadPosition.scl']
        ok, only_g, only_s = GRAPH.parity(xml, scl)
        self.assertTrue(ok)
        self.assertEqual(only_g, set())
        self.assertEqual(only_s, set())
        chart = GRAPH.dump(xml)
        self.assertEqual([s['step'] for s in chart['steps']], [240, 260, 280, 300])

    def test_load_position_mutation_detected(self):
        xml = self.sources['27_FB_GRAPH_PressDemoLoadPosition.xml']
        scl = self.sources['23_00_FB_PressDemoLoadPosition.scl']
        mutated_scl = scl.replace('OnAdvance := 280', 'OnAdvance := 300')
        ok, only_g, only_s = GRAPH.parity(xml, mutated_scl)
        self.assertFalse(ok)
        self.assertEqual(only_g, {(260, 280)})
        self.assertEqual(only_s, {(260, 300)})

    def test_home_rendition_parity(self):
        xml = self.sources['27_FB_GRAPH_PressDemoHome.xml']
        scl = self.sources['23_FB_PressDemoHome.scl']
        ok, only_g, only_s = GRAPH.parity(xml, scl)
        self.assertTrue(ok)
        self.assertEqual(only_g, set())
        self.assertEqual(only_s, set())
        chart = GRAPH.dump(xml)
        self.assertEqual([s['step'] for s in chart['steps']], [0, 900, 910, 999])

    def test_auto_rendition_parity(self):
        xml = self.sources['27_FB_GRAPH_PressDemoAuto.xml']
        scl = self.sources['23_FB_PressDemoAuto.scl']
        aux = {250, 300, 310}
        ok, only_g, only_s = GRAPH.parity(xml, scl, auxiliary=aux)
        self.assertTrue(ok)
        self.assertEqual(only_g, set())
        self.assertEqual(only_s, set())

    def test_auto_mutation_detected(self):
        xml = self.sources['27_FB_GRAPH_PressDemoAuto.xml']
        scl = self.sources['23_FB_PressDemoAuto.scl']
        mutated_scl = scl.replace('OnJump1 := 185', 'OnJump1 := 190')
        ok, only_g, only_s = GRAPH.parity(xml, mutated_scl, auxiliary={250, 300, 310})
        self.assertFalse(ok)
        self.assertEqual(only_g, {(180, 185)})
        self.assertEqual(only_s, {(180, 190)})


if __name__=='__main__':
    unittest.main()

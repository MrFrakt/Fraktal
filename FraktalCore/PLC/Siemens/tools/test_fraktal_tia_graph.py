"""The GRAPH writer and reader against TIA's own export (Part IV §3.5, S11): the
reader understands what TIA wrote, the writer emits the forms TIA compiled, and
the rendition gate fails on any step-graph difference from the SCL chain.

    python -m unittest discover -s FraktalCore/PLC/Siemens/tools -t FraktalCore/PLC/Siemens/tools
"""

import copy
import json
import pathlib
import re
import unittest

import fraktal_tia_graph as g

SPIKES = pathlib.Path(__file__).resolve().parents[1] / "Spikes"
REFERENCE = (SPIKES / "S11_Graph" / "reference" / "FB_GraphSample.xml").read_text(encoding="utf-8-sig")
CHAIN = json.loads((SPIKES / "S11_Graph" / "chain_auto.json").read_text(encoding="utf-8"))
SCL = (SPIKES / "S2_Shape" / "40_AutoSeq.scl").read_text(encoding="utf-8")


class ReaderTest(unittest.TestCase):
    def test_reads_the_chart_tia_drew(self):
        chart = g.dump(REFERENCE)
        self.assertEqual([(s["step"], s["init"]) for s in chart["steps"]], [(0, True), (100, False)])
        self.assertEqual([(e["from"], e["to"], e["link"]) for e in chart["edges"]],
                         [(0, 100, "Direct"), (100, 0, "Jump")])
        self.assertEqual(chart["edges"][0]["when"], {"language": "LAD", "operands": ["#_seq.RetVal", "1"], "boxes": ["Eq"]})
        self.assertEqual(chart["steps"][0]["actions"][0]["text"],
                         "CALL \"FRK_Seq_Step\" (StepNo := 0 StepName := 's.start' Seq := #_seq )")

    def test_writer_tokens_equal_tias_own(self):
        tia = re.search(r'<Action Qualifier="N">\n(.*?)\s*</Action>', REFERENCE.replace("\r\n", "\n"), re.S).group(1)
        tia_tokens = re.findall(r'<Token Text="([^"]*)" />', tia)
        ours = g.action_xml(g.call_text("FRK_Seq_Step", [("StepNo", "0"), ("StepName", "'s.start'"), ("Seq", "#_seq")]))
        self.assertEqual(re.findall(r'<Token Text="([^"]*)" />', ours), tia_tokens)


class WriterTest(unittest.TestCase):
    def setUp(self):
        self.xml = g.generate(CHAIN, REFERENCE)
        self.chart = g.dump(self.xml)

    def test_steps_and_edges_are_the_declaration(self):
        self.assertEqual([(s["step"], s["init"]) for s in self.chart["steps"]],
                         [(0, True), (100, False), (110, False), (120, False)])
        self.assertEqual([(e["from"], e["to"], e["link"]) for e in self.chart["edges"]],
                         [(0, 100, "Direct"), (100, 110, "Direct"), (110, 120, "Direct"), (120, 100, "Jump")])
        last = self.chart["edges"][-1]["when"]
        self.assertEqual(last, {"language": "FBD", "operands": ["#CylA.Done", "#CylB.Done"], "boxes": ["A"]})

    def test_execute_is_low_on_the_first_active_scan(self):
        acts = [(a["event"], a["text"]) for a in self.chart["steps"][1]["actions"]]
        order = [t for _, t in acts]
        self.assertEqual(acts[0], ("S1", "#Seq.Issued := FALSE"))
        self.assertLess(order.index("#Seq.Issued := FALSE"), order.index("#CylA.Execute := #Seq.Issued"))
        self.assertLess(order.index("#CylA.Execute := #Seq.Issued"), order.index("#Seq.Issued := TRUE"))
        self.assertEqual(acts[-1], ("S0", "#CylA.Execute := FALSE"))

    def test_interface_is_the_chains_not_the_templates(self):
        self.assertIn('<Member Name="CylB" Datatype="&quot;FB_SpkCylinderCM&quot;"', self.xml)
        static = re.search(r'\n  <Section Name="Static">\n(.*?)\n  </Section>\n', self.xml, re.S).group(1)
        self.assertEqual(re.findall(r'^    <Member Name="([^"]+)"', static, re.M), ["RT_DATA"])
        self.assertIn('\n  <Section Name="Temp" />\n', self.xml)
        self.assertNotIn("_seq", self.xml)
        self.assertIn("<Name>FB_SpkAutoGraph</Name>", self.xml)

    def test_parity_with_the_scl_rendition(self):
        self.assertEqual(g.parity(self.xml, SCL), (True, set(), set()))

    def test_parity_rejects_a_changed_edge(self):
        chain = copy.deepcopy(CHAIN)
        chain["steps"][3]["next"] = 110
        ok, only_graph, only_scl = g.parity(g.generate(chain, REFERENCE), SCL)
        self.assertFalse(ok)
        self.assertEqual((only_graph, only_scl), ({(120, 110)}, {(120, 100)}))

    def test_a_transition_without_condition_is_refused(self):
        chain = copy.deepcopy(CHAIN)
        chain["steps"][0]["when"] = []
        with self.assertRaises(ValueError):
            g.generate(chain, REFERENCE)

    def test_an_expression_is_not_an_operand(self):
        chain = copy.deepcopy(CHAIN)
        chain["steps"][1]["when"] = ["#CylA.Done OR #CylB.Done"]
        with self.assertRaises(ValueError):
            g.generate(chain, REFERENCE)

    def test_an_undeclared_target_is_refused(self):
        chain = copy.deepcopy(CHAIN)
        chain["steps"][1]["next"] = 999
        with self.assertRaises(ValueError):
            g.generate(chain, REFERENCE)


class SclEdgesTest(unittest.TestCase):
    def test_comments_do_not_declare_steps(self):
        self.assertEqual(g.scl_edges(SCL), {(0, 100), (100, 110), (110, 120), (120, 100)})
        self.assertEqual(g.scl_edges("// 5: not a label\n 7: \"FRK_Seq_Advance\"(OnAdvance := 9, OnJump1 := -1, Seq := #Seq);"),
                         {(7, 9)})


if __name__ == "__main__":
    unittest.main()

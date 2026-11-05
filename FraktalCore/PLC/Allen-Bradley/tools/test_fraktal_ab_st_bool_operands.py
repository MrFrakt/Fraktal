"""The BOOL-operand gate: what v38 refuses is found, what it accepts is not."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s6_host_demo as candidate
import fraktal_ab_st_bool_operands as gate
from test_fraktal_ab_generate import SEED_38

PROJECT = """<RSLogix5000Content><Controller>
<DataTypes><DataType Name="T_Ring"><Members>
<Member Name="Wrapped" DataType="BOOL"/><Member Name="Count" DataType="DINT"/></Members></DataType></DataTypes>
<AddOnInstructionDefinitions><AddOnInstructionDefinition Name="A_Probe">
<Parameters><Parameter Name="Enable" DataType="BOOL"/><Parameter Name="Limit" DataType="DINT"/></Parameters>
<LocalTags><LocalTag Name="Latched" DataType="BOOL"/></LocalTags>
<Routines><Routine Name="Logic"><STContent>{aoi}</STContent></Routine></Routines>
</AddOnInstructionDefinition></AddOnInstructionDefinitions>
<Tags><Tag Name="Flag" DataType="BOOL"/><Tag Name="Other" DataType="BOOL"/><Tag Name="Word" DataType="DINT"/>
<Tag Name="Ring" DataType="T_Ring"/><Tag Name="Source" DataType="T_Ring"/></Tags>
<Programs><Program Name="P"><Tags><Tag Name="Local" DataType="BOOL"/></Tags>
<Routines><Routine Name="Main"><STContent>{main}</STContent></Routine></Routines></Program></Programs>
</Controller></RSLogix5000Content>"""


def project(main, aoi='Latched := Enable;'):
    lines = lambda text: ''.join(f'<Line Number="{i}"><![CDATA[{line}]]></Line>'
                                 for i, line in enumerate(text.split('\n')))
    return ET.fromstring(PROJECT.format(main=lines(main), aoi=lines(aoi)))


class Rule(unittest.TestCase):
    def operands(self, main, aoi='Latched := Enable;'):
        return [f['operand'] for f in gate.findings(project(main, aoi))]

    def test_refused_forms_are_found(self):
        for line, operand in [('IF Ring.Wrapped <> (Source.Count <> 0) THEN Word := 1; END_IF;', 'Ring.Wrapped'),
                              ('Word := Flag + 1;', 'Flag'),
                              ('IF Flag = 1 THEN Word := 0; END_IF;', 'Flag'),
                              ('IF Local <> Other THEN Word := 0; END_IF;', 'Local'),
                              ('IF Word.3 = 1 THEN Word := 0; END_IF;', 'Word.3')]:
            with self.subTest(line=line):
                self.assertIn(operand, self.operands(line))

    def test_a_split_expression_is_one_statement(self):
        # The emitted formatter breaks long conditions; the operator may open the next line.
        self.assertEqual(self.operands('IF (Word > 0) OR (Ring.Wrapped\n<> (Source.Count <> 0)) THEN\nWord := 1;\nEND_IF;'),
                         ['Ring.Wrapped'])

    def test_accepted_forms_are_not(self):
        for line in ('Flag := Word <> 0;', 'Flag := Other;', 'IF Flag THEN Word := Word + 1; END_IF;',
                     'Flag := Flag OR (Word <> 0);', 'Flag := NOT Other AND Local;',
                     'IF Ring.Wrapped XOR (Source.Count <> 0) THEN Word := 1; END_IF;',
                     "Word := Ring.Count * 2; // Flag = 1 in a comment", 'IF S:FS THEN Word := 0; END_IF;'):
            with self.subTest(line=line):
                self.assertEqual(self.operands(line), [])

    def test_aoi_parameters_and_locals_resolve(self):
        self.assertEqual(self.operands('Word := 0;', 'IF Enable = 1 THEN Latched := Limit > 3; END_IF;'), ['Enable'])
        self.assertEqual(self.operands('Word := 0;', 'IF Enable AND (Limit > 3) THEN Latched := 1; END_IF;'), [])


class Emitted(unittest.TestCase):
    def test_the_v611_host_services_image_has_no_bool_operand(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'seed.L5X'
            source.write_text(SEED_38, encoding='utf-8')
            output = Path(directory) / 'app.L5X'
            gen.generate(candidate.application(), source, output)
            self.assertEqual(gate.findings(ET.parse(output).getroot()), [])


if __name__ == '__main__':
    unittest.main()

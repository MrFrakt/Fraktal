import tempfile
import unittest
from pathlib import Path

import fraktal_ab_readback as readback


SOURCE = '''<RSLogix5000Content><Controller Name="Test">
<DataTypes/><AddOnInstructionDefinitions/>
<Tags><Tag Name="Identity" DataType="DINT" TagType="Base" ExternalAccess="Read Only" Constant="false">
<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="42"/></Data></Tag></Tags>
<Programs><Program Name="Main" MainRoutineName="Logic"><Tags/><Routines>
<Routine Name="Logic" Type="ST"><STContent><Line Number="0"><![CDATA[X := 1;]]></Line></STContent></Routine>
<Routine Name="Ladder" Type="RLL"><RLLContent><Rung Number="0"><Text><![CDATA[MOVE(1,X);]]></Text></Rung></RLLContent></Routine>
</Routines></Program></Programs><Tasks/></Controller></RSLogix5000Content>'''


class NativeReadback(unittest.TestCase):
    def compare(self, exported):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/'source.L5X', Path(folder)/'export.L5X'
            a.write_text(SOURCE)
            b.write_text(exported)
            return readback.compare(a,b)

    def test_equal_artifact_passes(self):
        self.assertTrue(self.compare(SOURCE)['Equivalent'])

    def test_same_line_count_with_changed_st_is_rejected(self):
        result = self.compare(SOURCE.replace('X := 1;', 'X := 2;'))
        self.assertTrue(result['Inventory']['Equivalent'])
        self.assertEqual(result['ExecutableDifferences'], ['Main/Logic'])
        self.assertFalse(result['Equivalent'])

    def test_changed_rung_operand_is_rejected(self):
        self.assertFalse(self.compare(SOURCE.replace('MOVE(1,X)', 'MOVE(2,X)'))['Equivalent'])

    def test_identity_initial_value_loss_is_rejected(self):
        result = self.compare(SOURCE.replace('Value="42"', 'Value="0"'))
        self.assertTrue(result['Inventory']['Equivalent'])
        self.assertEqual(result['InitialValueDifferences'], ['Test/Identity'])
        self.assertFalse(result['Equivalent'])

    def test_presentation_is_ignored_and_quoted_whitespace_is_preserved(self):
        self.assertEqual(readback.normalized("(* note *) X := 'a b';\n"), "X:='a b';")
        self.assertNotEqual(readback.normalized("X := 'a b';"), readback.normalized("X := 'ab';"))
        self.assertEqual(readback.normalized('X:=1; // comment\n Y:=2;'), 'X:=1;Y:=2;')

    def test_sdk_empty_ascii_normalization_is_explicit_and_nonempty_text_is_kept(self):
        import xml.etree.ElementTree as ET
        def artifact(value):
            return ET.fromstring('<RSLogix5000Content><Controller Name="C"><Tags><Tag Name="S">'
                '<Data Format="Decorated"><DataValue Radix="ASCII">' + value +
                '</DataValue></Data></Tag></Tags></Controller></RSLogix5000Content>')
        self.assertEqual(readback.initials(artifact("''")), readback.initials(artifact('')))
        self.assertNotEqual(readback.initials(artifact("'asset'")), readback.initials(artifact('')))

    def test_native_ascii_escape_spellings_compare_by_actual_bytes(self):
        self.assertEqual(readback.ascii_payload("'a]]$3Eb'"), b'a]]>b')
        self.assertEqual(readback.ascii_payload("'$$$'tool'"), b"$'tool")
        with self.assertRaises(ValueError):
            readback.ascii_payload("'truncated$'")


if __name__ == '__main__':
    unittest.main()

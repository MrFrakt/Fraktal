import tempfile
import unittest
from pathlib import Path

from fraktal_ab_s2_fixture import AOIS, NESTING_DEPTH, generate


EMPTY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetType="Controller" TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33">
<DataTypes/>
<Modules><Module Name="Discrete_IO" Inhibited="false"/></Modules>
<AddOnInstructionDefinitions/>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


class S2FixtureTests(unittest.TestCase):
    def test_generates_declared_contract_and_nesting_chain(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            output = Path(temporary) / "fixture.L5X"
            source.write_text(EMPTY, encoding="utf-8")

            result = generate(source, output)
            text = output.read_text(encoding="utf-8")

            self.assertEqual(result["NestedAoiDepth"], NESTING_DEPTH)
            self.assertEqual(result["AoiDefinitions"], len(AOIS))
            self.assertEqual(
                text.count("<AddOnInstructionDefinition "), NESTING_DEPTH
            )
            self.assertIn('Name="Ctx" TagType="Base" DataType="FRK_T_S2Ctx" Usage="InOut"', text)
            self.assertIn('Name="Text" TagType="Base" DataType="STRING" Usage="InOut"', text)
            self.assertIn('Name="ScalarIn" TagType="Base" DataType="DINT" Usage="Input"', text)
            self.assertIn('Name="ScalarOut" TagType="Base" DataType="DINT" Usage="Output"', text)
            self.assertEqual(text.count('Name="Child"'), NESTING_DEPTH - 1)
            self.assertIn(
                "FRK_S2_Level08(FRK_S2_Instance,FRK_S2_Ctx,FRK_S2_Text,7,FRK_S2_Output);",
                text,
            )
            self.assertNotRegex(text, r"\b(?:Local|Discrete_IO):[IOC]")
            self.assertIn('Module Name="Discrete_IO" Inhibited="true"', text)
            self.assertIn('DisableUpdateOutputs="true"', text)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            output = Path(temporary) / "fixture.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                generate(source, output)

    def test_generates_requested_limit_probe_depth(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            output = Path(temporary) / "fixture.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            result = generate(source, output, 17)
            text = output.read_text(encoding="utf-8")
            self.assertEqual(result["NestedAoiDepth"], 17)
            self.assertIn("FRK_S2_Level17(FRK_S2_Instance", text)


if __name__ == "__main__":
    unittest.main()

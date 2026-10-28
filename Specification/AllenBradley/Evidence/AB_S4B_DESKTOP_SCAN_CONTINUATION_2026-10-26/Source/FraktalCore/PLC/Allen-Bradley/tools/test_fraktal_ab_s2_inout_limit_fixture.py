import tempfile
import unittest
from pathlib import Path

from fraktal_ab_s2_inout_limit_fixture import generate


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


class S2InOutLimitFixtureTests(unittest.TestCase):
    def test_generates_requested_inout_count_and_call_site(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            output = Path(temporary) / "limit.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            result = generate(source, output, 64)
            text = output.read_text(encoding="utf-8")

            self.assertEqual(result["InOutParameters"], 64)
            self.assertEqual(text.count('Usage="InOut"'), 64)
            self.assertIn('Name="FRK_S2_Ref064"', text)
            self.assertIn(
                "FRK_S2_InOutLimit(FRK_S2_InOutInstance,FRK_S2_Ref001,",
                text,
            )
            self.assertIn(",FRK_S2_Ref064);", text)
            self.assertNotRegex(text, r"\b(?:Local|Discrete_IO):[IOC]")
            self.assertIn('Module Name="Discrete_IO" Inhibited="true"', text)
            self.assertIn('DisableUpdateOutputs="true"', text)

    def test_rejects_count_outside_boundary_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "between 1 and 65"):
                generate(source, Path(temporary) / "limit.L5X", 66)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

import fraktal_ab_phase0_fixture as subject


EMPTY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33">
<DataTypes/>
<Modules><Module Name="Discrete_IO" Inhibited="false"></Module></Modules>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


class Phase0FixtureTests(unittest.TestCase):
    def test_generates_memory_only_v33_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "empty.L5X"
            output = root / "fixture.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            evidence = subject.generate(source, output)
            generated = output.read_text(encoding="utf-8")

        self.assertEqual(evidence["PhysicalIoReferences"], 0)
        self.assertEqual(evidence["ControllerTags"], 13)
        self.assertEqual(evidence["ProgramTags"], 2)
        self.assertIn('Inhibited="true"', generated)
        self.assertIn('DisableUpdateOutputs="true"', generated)
        self.assertIn('ExternalAccess="Read Only"', generated)
        self.assertIn('ExternalAccess="None"', generated)
        self.assertIn('DataType="STRING"', generated)
        self.assertIn('Dimensions="25"', generated)
        self.assertIn('Dimensions="1024"', generated)
        self.assertIn('Name="FRK_ProgramWriteDint"', generated)
        self.assertNotRegex(generated, r"\b(?:Local|Discrete_IO):[IOC]")

    def test_refuses_non_v33_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "empty.L5X"
            output = root / "fixture.L5X"
            source.write_text(EMPTY.replace('MajorRev="33"', 'MajorRev="37"'))
            with self.assertRaisesRegex(ValueError, "expected empty v33"):
                subject.generate(source, output)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "empty.L5X"
            output = root / "fixture.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                subject.generate(source, output)


if __name__ == "__main__":
    unittest.main()

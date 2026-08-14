import tempfile
import unittest
from pathlib import Path

from fraktal_ab_s2_signature_variant import generate


BASE = """<RSLogix5000Content TargetName="FRK_S2_Level01" TargetType="AddOnInstructionDefinition" TargetRevision="1.0 ">
<Controller><AddOnInstructionDefinitions>
<AddOnInstructionDefinition Name="FRK_S2_Level01" Revision="1.0">
<Parameters><Parameter Name="ScalarOut"/></Parameters>
<Routines><Routine><STContent>
<Line Number="3"><![CDATA[ScalarOut := Ctx.Result + Text.LEN;]]></Line>
</STContent></Routine></Routines>
</AddOnInstructionDefinition>
</AddOnInstructionDefinitions></Controller></RSLogix5000Content>"""


class S2SignatureVariantTests(unittest.TestCase):
    def test_generates_optional_minor_variant(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "base.L5X"
            output = Path(temporary) / "optional.L5X"
            source.write_text(BASE, encoding="utf-8")
            evidence = generate(source, output, False)
            text = output.read_text(encoding="utf-8")
            self.assertEqual(evidence["Revision"], "1.1")
            self.assertIn('Name="AddedInput"', text)
            self.assertIn('Required="false"', text)
            self.assertIn("Ctx.Result := Ctx.Result + AddedInput;", text)

    def test_generates_required_major_variant(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "base.L5X"
            output = Path(temporary) / "required.L5X"
            source.write_text(BASE, encoding="utf-8")
            evidence = generate(source, output, True)
            text = output.read_text(encoding="utf-8")
            self.assertEqual(evidence["Revision"], "2.0")
            self.assertIn('Required="true"', text)


if __name__ == "__main__":
    unittest.main()

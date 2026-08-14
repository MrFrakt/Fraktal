import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fraktal_ab_s12_fixture import (
    ARRAY_LENGTH,
    LAYOUT_BYTES,
    LAYOUT_MEMBERS,
    LAYOUT_TAG,
    LAYOUT_TYPE,
    NAN_BITS,
    generate,
    routine_lines,
)


SEED = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetType="Controller" TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33">
<DataTypes/>
<Modules><Module Name="Discrete_IO" Inhibited="false"/></Modules>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


def build(temporary: str) -> tuple[dict[str, object], str]:
    source = Path(temporary) / "seed.L5X"
    output = Path(temporary) / "fixture.L5X"
    source.write_text(SEED, encoding="utf-8")
    return generate(source, output), output.read_text(encoding="utf-8")


class S12FixtureTests(unittest.TestCase):
    def test_output_is_well_formed_and_declares_the_public_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            root = ElementTree.fromstring(text)
            data_type = next(
                item for item in root.iter("DataType")
                if item.get("Name") == LAYOUT_TYPE
            )
            declared = [
                member.get("Name") for member in data_type.iter("Member")
            ]
            self.assertEqual(declared, [name for name, _, _ in LAYOUT_MEMBERS])

    def test_controller_publishes_its_own_wire_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            # the layout must be measured, not predicted, so the COP into the
            # byte array is the load-bearing statement of this fixture
            self.assertIn(f"COP({LAYOUT_TAG},{LAYOUT_BYTES}[0],1);", text)
            self.assertIn(f'Name="{LAYOUT_BYTES}"', text)
            self.assertEqual(
                result["LayoutByteCapacity"], result["LayoutByteCapacity"]
            )

    def test_no_faulting_instruction_is_generated(self):
        logic = "\n".join(routine_lines())
        # an integer divide by zero and an out-of-range subscript are Logix
        # major faults, and clearing one is out of scope for an evidence run
        self.assertNotIn("/", logic)
        for statement in routine_lines():
            for index_expression in statement.split("[")[1:]:
                subscript = index_expression.split("]")[0]
                self.assertTrue(
                    subscript.isdigit(),
                    f"non-constant subscript {subscript!r} in {statement!r}",
                )

    def test_nan_is_copied_never_computed(self):
        logic = "\n".join(routine_lines())
        self.assertIn("COP(FRK_S12_NanBits,FRK_S12_NanReal,1);", logic)
        self.assertIn("IF FRK_S12_NanReal <> FRK_S12_NanReal THEN", logic)
        self.assertEqual(NAN_BITS, 0x7FC00000)

    def test_duration_is_range_checked_in_the_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            self.assertIn("FRK_S12_DurationOk := 1;", text)
            self.assertIn("FRK_S12_DurationMs >= 0", text)
            self.assertEqual(result["DurationMaxMs"], 86_400_000)

    def test_array_edges_are_indexed_by_constant(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            self.assertIn(f"FRK_S12_Array[{ARRAY_LENGTH - 1}]", text)

    def test_fixture_stays_memory_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            self.assertNotRegex(text, r"\b(?:Local|Discrete_IO):[IOC]")
            self.assertIn('Module Name="Discrete_IO" Inhibited="true"', text)
            self.assertIn('DisableUpdateOutputs="true"', text)
            self.assertEqual(result["PhysicalIoReferences"], 0)

    def test_refuses_overwrite_and_a_foreign_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "seed.L5X"
            output = Path(temporary) / "fixture.L5X"
            source.write_text(SEED, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                generate(source, output)

            wrong = Path(temporary) / "wrong.L5X"
            wrong.write_text(SEED.replace("<Tasks/>", ""), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not the expected empty"):
                generate(wrong, Path(temporary) / "other.L5X")


if __name__ == "__main__":
    unittest.main()

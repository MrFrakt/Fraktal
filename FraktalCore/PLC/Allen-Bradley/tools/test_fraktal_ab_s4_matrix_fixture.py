import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fraktal_ab_l5x_inventory import inventory
from fraktal_ab_s4_matrix_fixture import (
    AOI_NAME,
    CONTINUOUS_TASK,
    PERIODIC_TASK,
    PROGRAM_A,
    PROGRAM_B,
    RECORD_TYPE,
    STRING_TYPE,
    generate,
)


SEED = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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


def build(temporary: str) -> tuple[dict[str, object], str, dict[str, object]]:
    source = Path(temporary) / "seed.L5X"
    output = Path(temporary) / "matrix.L5X"
    source.write_text(SEED, encoding="utf-8")
    evidence = generate(source, output)
    return evidence, output.read_text(encoding="utf-8"), inventory(output)


class S4MatrixFixtureTests(unittest.TestCase):
    def test_output_is_well_formed(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text, _ = build(temporary)
            ElementTree.fromstring(text)

    def test_carries_both_task_types_with_their_schedules(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, census = build(temporary)
            self.assertEqual(census["Tasks"][PERIODIC_TASK]["type"], "PERIODIC")
            self.assertEqual(census["Tasks"][CONTINUOUS_TASK]["type"], "CONTINUOUS")
            self.assertEqual(census["Tasks"][PERIODIC_TASK]["scheduled"], [PROGRAM_A])
            self.assertEqual(census["Tasks"][CONTINUOUS_TASK]["scheduled"], [PROGRAM_B])
            # a continuous task carries no rate, and inventing one would be a
            # different construct
            self.assertIsNone(census["Tasks"][CONTINUOUS_TASK]["rate"])

    def test_carries_three_routine_languages_in_one_program(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, census = build(temporary)
            routines = census["Programs"][PROGRAM_A]["routines"]
            self.assertEqual(
                sorted(body["type"] for body in routines.values()),
                ["RLL", "SFC", "ST"],
            )

    def test_every_generated_routine_is_reached_from_the_main_routine(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text, census = build(temporary)
            main = census["Programs"][PROGRAM_A]["mainRoutine"]
            for name in census["Programs"][PROGRAM_A]["routines"]:
                if name == main:
                    continue
                # Studio raises a Verify warning for an unreachable routine, so
                # an emitted routine that nothing calls is a generator defect
                self.assertIn(f"JSR({name},0);", text, f"{name} is never called")

    def test_carries_the_record_shapes_a_manifest_needs(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, _, census = build(temporary)
            record = census["DataTypes"][RECORD_TYPE]["members"]
            names = [member["name"] for member in record]
            self.assertIn("Inner", names)
            self.assertIn("Samples", names)
            self.assertIn("Label", names)
            self.assertEqual(census["DataTypes"][STRING_TYPE]["family"], "StringFamily")
            self.assertEqual(
                census["ControllerTags"]["FRK_S4_Table"]["dimensions"],
                str(evidence["UdtArrayLength"]),
            )

    def test_declares_a_generated_enum_constant(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, census = build(temporary)
            self.assertEqual(
                census["ControllerTags"]["FRK_K_ModeAuto"]["constant"], "true"
            )

    def test_aoi_declares_all_three_scan_flags_with_routines(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, _, census = build(temporary)
            aoi = census["AddOnInstructions"][AOI_NAME]
            self.assertEqual(aoi["executePrescan"], "true")
            self.assertEqual(aoi["executePostscan"], "true")
            self.assertEqual(aoi["executeEnableInFalse"], "true")
            self.assertEqual(
                sorted(aoi["routines"]), sorted(evidence["AoiScanRoutines"])
            )

    def test_every_tag_declares_external_access_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, census = build(temporary)
            scopes = [census["ControllerTags"]] + [
                program["tags"] for program in census["Programs"].values()
            ]
            for scope in scopes:
                for name, tag in scope.items():
                    # an omitted attribute round-trips as Studio's default,
                    # which then reads as drift in a later comparison
                    self.assertIsNotNone(
                        tag["externalAccess"], f"{name} omits ExternalAccess"
                    )

    def test_carries_descriptions(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, census = build(temporary)
            self.assertGreaterEqual(census["DescriptionCount"], 4)

    def test_fixture_stays_memory_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, text, _ = build(temporary)
            self.assertNotRegex(text, r"\b(?:Local|Discrete_IO):[IOC]")
            self.assertIn('Module Name="Discrete_IO" Inhibited="true"', text)
            self.assertEqual(evidence["PhysicalIoReferences"], 0)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "seed.L5X"
            output = Path(temporary) / "matrix.L5X"
            source.write_text(SEED, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                generate(source, output)


if __name__ == "__main__":
    unittest.main()

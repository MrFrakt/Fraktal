"""Scope and type boundaries of the disposable native compiler probes."""
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_v38_native_probe as probe
from test_fraktal_ab_s12_type_probe import SEED


class NativeProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.seed = self.root / "seed.L5X"
        self.original = SEED.replace("1769-L24ER-QB1B", "1756-L81E").replace(
            'MajorRev="33"', 'MajorRev="38"')
        self.seed.write_text(self.original, encoding="utf-8")
        self.output = self.root / "cases"

    def generate(self):
        return probe.generate_all(self.seed, self.output)

    def test_compiler_expectations_do_not_become_runtime_acceptance(self):
        report = self.generate()
        self.assertEqual(report["Controller"], "1756-L81E")
        self.assertEqual(report["MajorRevision"], "38")
        self.assertIs(report["RuntimeAccepted"], False)
        self.assertIs(report["ExternalModuleAccepted"], False)
        self.assertEqual({c["Case"]: c["ExpectedBuild"] for c in report["Cases"]}, {
            "module_local": "pass", "task_intervals": "pass",
            "clock_arithmetic": "pass", "invalid_attribute": "fail",
            "maximum_interval_spelling": "observe",
        })

    def test_split_cases_isolate_one_attribute_without_losing_the_negative_control(self):
        report = probe.generate_all(self.seed, self.output, split_attributes=True)
        expected = probe.MODULE_ATTRIBUTES + probe.TASK_ATTRIBUTES + probe.CLOCK_ATTRIBUTES
        self.assertEqual(len(report["Cases"]), len(expected) + 1)
        statements = []
        for case in report["Cases"]:
            self.assertEqual(len(case["Statements"]), 1)
            if case["Case"] != "invalid_attribute":
                self.assertEqual(case["ExpectedBuild"], "observe")
                statements.extend(case["Statements"])
            else:
                self.assertEqual(case["ExpectedBuild"], "fail")
        self.assertCountEqual(statements, [a.statement for a in expected])

    def test_generated_projects_have_no_external_write_or_output_surface(self):
        for result in self.generate()["Cases"]:
            with self.subTest(case=result["Case"]):
                root = ET.parse(result["Output"]).getroot()
                controller = root.find("Controller")
                self.assertEqual(len(controller.find("AddOnInstructionDefinitions") or []), 0)
                for element in root.iter():
                    if element.tag in ("Tag", "Member"):
                        self.assertEqual(element.get("ExternalAccess"), "Read Only")
                task = controller.find("Tasks/Task")
                self.assertEqual(task.get("Type"), "PERIODIC")
                self.assertEqual(task.get("DisableUpdateOutputs"), "true")
                self.assertEqual(task.get("Rate"), "10")
                statements = result["Statements"]
                self.assertFalse(any("SSV(" in line or "Local:" in line for line in statements))
                lines = root.findall("Controller/Programs/Program/Routines/Routine/STContent/Line")
                self.assertTrue(all("\n" not in (line.text or "") for line in lines))
                self.assertEqual(len(lines), 1 + len(statements))

    def test_module_gsvs_use_int_for_native_int_attributes(self):
        self.generate()
        root = ET.parse(self.output / "native_module_local.L5X")
        members = {m.get("Name"): m.get("DataType")
                   for m in root.findall("Controller/DataTypes/DataType/Members/Member")}
        self.assertEqual(members, {
            "EntryStatus": "INT", "FaultCode": "INT", "FaultInfo": "DINT",
            "ModuleMode": "INT", "ForceStatus": "INT",
        })
        for line in root.findall("Controller/Programs/Program/Routines/Routine/STContent/Line"):
            if "GSV(" in (line.text or ""):
                self.assertTrue(line.text.startswith("GSV(MODULE,Local,")
                                or line.text.startswith("GSV(MODULE,,ForceStatus,"))

    def test_task_interval_word_buffers_are_two_dints(self):
        self.generate()
        root = ET.parse(self.output / "native_task_intervals.L5X")
        members = {m.get("Name"): (m.get("DataType"), m.get("Dimension"))
                   for m in root.findall("Controller/DataTypes/DataType/Members/Member")}
        for name in ("MaxIntervalWords", "MinIntervalWords", "StartWords"):
            self.assertEqual(members[name], ("DINT", "2"))
        self.assertEqual(members["MaxIntervalTime"], ("TIME", "0"))
        self.assertEqual(members["StartLint"], ("LINT", "0"))
        source = (self.output / "native_task_intervals.L5X").read_text()
        self.assertIn("MaxInterval,FRK_S12_Probe.MaxIntervalWords[0]", source)
        self.assertNotIn("MaximumInterval", source)

    def test_clock_subtraction_never_narrows_the_native_counter(self):
        self.generate()
        root = ET.parse(self.output / "native_clock_arithmetic.L5X")
        members = {m.get("Name"): m.get("DataType")
                   for m in root.findall("Controller/DataTypes/DataType/Members/Member")}
        for name in ("CstCurrent", "PreviousCst", "DeltaCst", "WallClockCurrent"):
            self.assertEqual(members[name], "LINT")

    def test_seed_and_previous_output_are_never_overwritten(self):
        report = self.generate()
        self.assertEqual(self.seed.read_text(encoding="utf-8"), self.original)
        before = {Path(c["Output"]): Path(c["Output"]).read_bytes() for c in report["Cases"]}
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.generate()
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_one_preexisting_case_prevents_partial_generation(self):
        self.output.mkdir()
        path = self.output / "native_clock_arithmetic.L5X"
        path.write_text("previous evidence", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.generate()
        self.assertEqual(list(self.output.iterdir()), [path])

    def test_wrong_family_or_revision_cannot_be_relabelled(self):
        for original, replacement in (("1756-L81E", "5069-L310ER"),
                                      ('MajorRev="38"', 'MajorRev="33"')):
            with self.subTest(replacement=replacement):
                self.seed.write_text(self.original.replace(original, replacement), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "expected empty"):
                    self.generate()
                self.assertEqual(list(self.output.glob("*.L5X")), [])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

import fraktal_ab_target_binding_compare as subject
from fraktal_ab_l5x_compare import CompareError


def fixture(minor: int, serial: str, value: int = 1) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content ExportDate="volatile">
<Controller MajorRev="33" MinorRev="{minor}" ProjectSN="{serial}"
 ProjectCreationDate="volatile" LastModifiedDate="volatile">
<Modules><Module Name="Local" Major="33" Minor="{minor}"/></Modules>
<Tags><Tag Name="Proof" Value="{value}"/></Tags>
</Controller>
</RSLogix5000Content>'''


class TargetBindingCompareTests(unittest.TestCase):
    def paths(self, directory: str, after_value: int = 1):
        before = Path(directory, "before.L5X")
        after = Path(directory, "after.L5X")
        before.write_text(fixture(11, "16#0000_0000"), encoding="utf-8")
        after.write_text(
            fixture(14, "16#7036_b510", after_value), encoding="utf-8"
        )
        return before, after

    def test_accepts_only_exact_target_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.paths(directory)
            report = subject.compare(
                before,
                after,
                serial="7036B510",
                major_revision=33,
                source_minor=11,
                target_minor=14,
            )
            self.assertTrue(report["EquivalentAfterExactTargetBinding"])
            self.assertEqual(len(report["ExpectedBindingDifferences"]), 3)

    def test_semantic_difference_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.paths(directory, after_value=2)
            report = subject.compare(
                before,
                after,
                serial="7036B510",
                major_revision=33,
                source_minor=11,
                target_minor=14,
            )
            self.assertFalse(report["EquivalentAfterExactTargetBinding"])

    def test_wrong_serial_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.paths(directory)
            with self.assertRaises(CompareError):
                subject.compare(
                    before,
                    after,
                    serial="DEADBEEF",
                    major_revision=33,
                    source_minor=11,
                    target_minor=14,
                )


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

import fraktal_ab_l5x_compare as subject


def fixture(export_date: str, created: str, modified: str,
            tag_value: str = "1") -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="37.00"
 ExportDate="{export_date}" TargetName="Fixture" TargetType="Controller">
 <Controller Name="Fixture" ProcessorType="1769-L24ER-QB1B"
  MajorRev="37" MinorRev="11" ProjectCreationDate="{created}"
  LastModifiedDate="{modified}">
  <Tags><Tag Name="Proof" DataType="DINT" Value="{tag_value}" /></Tags>
 </Controller>
</RSLogix5000Content>'''


class L5xCompareTests(unittest.TestCase):
    def compare(self, first_text: str, second_text: str):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory, "first.L5X")
            second = Path(directory, "second.L5X")
            first.write_text(first_text, encoding="utf-8")
            second.write_text(second_text, encoding="utf-8")
            return subject.compare(first, second)

    def test_only_known_volatile_attributes_are_excluded(self):
        report = self.compare(
            fixture("one", "two", "three"),
            fixture("four", "five", "six"),
        )
        self.assertTrue(report["Equivalent"])
        self.assertEqual(report["ExcludedAttributes"], [
            "Controller/@LastModifiedDate",
            "Controller/@ProjectCreationDate",
            "RSLogix5000Content/@ExportDate",
        ])

    def test_semantic_change_fails(self):
        report = self.compare(
            fixture("one", "two", "three", "1"),
            fixture("four", "five", "six", "2"),
        )
        self.assertFalse(report["Equivalent"])

    def test_canonical_hash_ignores_only_the_volatile_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory, "first.L5X")
            second = Path(directory, "second.L5X")
            changed = Path(directory, "changed.L5X")
            first.write_text(fixture("one", "two", "three"), encoding="utf-8")
            second.write_text(fixture("four", "five", "six"), encoding="utf-8")
            changed.write_text(
                fixture("one", "two", "three", "9"), encoding="utf-8"
            )
            self.assertEqual(
                subject.canonical_sha256(first), subject.canonical_sha256(second)
            )
            self.assertNotEqual(
                subject.canonical_sha256(first), subject.canonical_sha256(changed)
            )

    def test_non_project_xml_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "not-project.L5X")
            path.write_text("<Tag />", encoding="utf-8")
            with self.assertRaises(subject.CompareError):
                subject.canonical_l5x(path)


if __name__ == "__main__":
    unittest.main()

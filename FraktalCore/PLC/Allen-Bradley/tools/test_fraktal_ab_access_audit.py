import tempfile
import unittest
from pathlib import Path

from fraktal_ab_access_audit import AuditError, audit, controller_tags


def project(tags: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content>
<Controller Use="Target" Name="Fixture">
<Tags>
{tags}
</Tags>
</Controller>
</RSLogix5000Content>
"""


def tag(name: str, access: str | None) -> str:
    attribute = "" if access is None else f' ExternalAccess="{access}"'
    return f'<Tag Name="{name}" TagType="Base" DataType="DINT"{attribute}/>'


CONFORMING = project(
    "\n".join(
        [
            tag("FRK_Manifest", "Read Only"),
            tag("FRK_Mailbox", "Read/Write"),
            tag("FRK_Private", "None"),
        ]
    )
)


class AccessAuditTests(unittest.TestCase):
    def read(self, text: str):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "project.L5X"
            path.write_text(text, encoding="utf-8")
            return controller_tags(path)

    def test_a_conforming_project_passes(self):
        report = audit(
            self.read(CONFORMING), {"FRK_Mailbox"}, {"FRK_Manifest"}
        )
        self.assertTrue(report["Conforms"], report["Findings"])
        self.assertEqual(report["WriteSurface"], ["FRK_Mailbox"])

    def test_an_unclassified_readable_tag_is_rejected(self):
        # the benefit of the doubt is exactly what the allow-list removes
        report = audit(self.read(CONFORMING), {"FRK_Mailbox"}, set())
        self.assertFalse(report["Conforms"])
        self.assertTrue(
            any("FRK_Manifest" in item for item in report["Findings"]),
            report["Findings"],
        )

    def test_a_public_tag_that_is_writable_is_rejected(self):
        text = project(
            "\n".join([tag("FRK_Manifest", "Read/Write"), tag("FRK_Private", "None")])
        )
        report = audit(self.read(text), set(), {"FRK_Manifest"})
        self.assertFalse(report["Conforms"])
        self.assertIn("FRK_Manifest", report["WriteSurface"])

    def test_a_mailbox_that_is_read_only_is_rejected(self):
        text = project(
            "\n".join([tag("FRK_Mailbox", "Read Only"), tag("FRK_Private", "None")])
        )
        report = audit(self.read(text), {"FRK_Mailbox"}, set())
        self.assertFalse(report["Conforms"])

    def test_an_omitted_attribute_is_not_treated_as_none(self):
        # Studio writes its default on export, so absent is an unproven write
        # surface rather than a private tag
        text = project(tag("FRK_Unknown", None))
        report = audit(self.read(text), set(), set())
        self.assertFalse(report["Conforms"])

    def test_a_tag_declared_both_classes_is_rejected(self):
        report = audit(
            self.read(CONFORMING), {"FRK_Manifest"}, {"FRK_Manifest"}
        )
        self.assertFalse(report["Conforms"])
        self.assertTrue(
            any("both mailbox and public" in item for item in report["Findings"])
        )

    def test_a_declared_tag_missing_from_the_project_is_reported(self):
        report = audit(
            self.read(CONFORMING), {"FRK_Mailbox"}, {"FRK_Manifest", "FRK_Absent"}
        )
        self.assertFalse(report["Conforms"])
        self.assertTrue(
            any("not present in the project" in item for item in report["Findings"])
        )

    def test_non_project_xml_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.L5X"
            path.write_text("<Tag/>", encoding="utf-8")
            with self.assertRaises(AuditError):
                controller_tags(path)


if __name__ == "__main__":
    unittest.main()

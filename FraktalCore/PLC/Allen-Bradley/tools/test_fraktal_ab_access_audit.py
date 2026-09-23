import tempfile
import unittest
from pathlib import Path

import fraktal_ab_access_audit as audit_module
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


class PlantClassTests(unittest.TestCase):
    """A simulated sensor is writable, but it is not a command surface.

    Calling the plant a mailbox to make the audit pass would put `AirOk` and
    `FaultDoor` in a report's mailbox list, and the next reader would take them
    for ways to command the machine.
    """

    TAGS = {
        "FRK_Press_HmiRequest": "Read/Write",
        "FRK_Press_AirOk": "Read/Write",
        "FRK_Press_Unit": "Read Only",
        "FRK_Press_RunRequest": "None",
    }

    def audit(self, **kwargs):
        return audit_module.audit(
            dict(self.TAGS),
            kwargs.get("mailbox", {"FRK_Press_HmiRequest"}),
            kwargs.get("public", {"FRK_Press_Unit"}),
            kwargs.get("plant", {"FRK_Press_AirOk"}),
        )

    def test_a_declared_plant_input_conforms_when_writable(self):
        report = self.audit()
        self.assertTrue(report["Conforms"], report["Findings"])

    def test_the_plant_is_not_counted_as_a_command_surface(self):
        report = self.audit()
        self.assertEqual(report["CommandSurface"], ["FRK_Press_HmiRequest"])
        self.assertIn("FRK_Press_AirOk", report["WriteSurface"])

    def test_the_plant_is_named_in_the_report(self):
        self.assertEqual(self.audit()["Plant"], ["FRK_Press_AirOk"])

    def test_an_undeclared_writable_tag_still_fails(self):
        # The whole point: the plant class is a declaration, not an amnesty.
        report = self.audit(plant=set())
        self.assertFalse(report["Conforms"])
        self.assertTrue(any("FRK_Press_AirOk" in f for f in report["Findings"]))

    def test_a_plant_tag_that_is_read_only_fails(self):
        tags = dict(self.TAGS, FRK_Press_AirOk="Read Only")
        report = audit_module.audit(tags, {"FRK_Press_HmiRequest"},
                                    {"FRK_Press_Unit"}, {"FRK_Press_AirOk"})
        self.assertFalse(report["Conforms"])

    def test_a_tag_declared_plant_and_public_is_rejected(self):
        report = self.audit(public={"FRK_Press_Unit", "FRK_Press_AirOk"})
        self.assertFalse(report["Conforms"])
        self.assertTrue(any("FRK_Press_AirOk" in f for f in report["Findings"]))

    def test_no_plant_declared_behaves_as_before(self):
        # A real application declares none, and the audit must not require the
        # argument to exist.
        report = audit_module.audit(
            {"FRK_Press_HmiRequest": "Read/Write", "FRK_Press_Unit": "Read Only"},
            {"FRK_Press_HmiRequest"}, {"FRK_Press_Unit"})
        self.assertTrue(report["Conforms"], report["Findings"])
        self.assertEqual(report["Plant"], [])

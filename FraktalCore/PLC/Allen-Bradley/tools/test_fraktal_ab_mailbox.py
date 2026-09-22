"""Tests for the emitted command mailbox.

The mailbox is the first and only writable surface this binding publishes, so
the tests that matter are the ones about what a client can reach: the request
is writable, the response is not, and the handler's own memory is reachable by
nobody. A mailbox whose response a client could write is not a mailbox, it is a
place to forge an acknowledgement.
"""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
from test_fraktal_ab_generate import SEED

APP = demo.application()


def emit():
    """The parsed project and its raw text.

    Both, because CDATA does not survive a reparse: ElementTree hands back the
    text content, so a test that re-serialises cannot tell a quoted Logix string
    from a bare one - which is the exact defect the manifest hit.
    """
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "seed.L5X"
        source.write_text(SEED, encoding="utf-8")
        output = Path(directory) / "app.L5X"
        gen.generate(APP, source, output)
        text = output.read_text(encoding="utf-8")
        return ET.fromstring(text), text


class TypeEmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.text = emit()
        cls.types = {t.get("Name"): t for t in cls.root.iter("DataType")}

    def test_both_contract_records_are_emitted(self):
        self.assertIn(mailbox.request_type_name(APP), self.types)
        self.assertIn(mailbox.response_type_name(APP), self.types)

    def test_a_string_type_exists_for_every_declared_width(self):
        for length in mailbox.string_lengths():
            self.assertIn(mailbox.string_type_name(APP, length), self.types)

    def test_the_widths_are_the_oracle_widths(self):
        self.assertEqual(set(mailbox.string_lengths()), {255, 160, 32})

    def test_every_string_type_is_the_logix_string_layout(self):
        for length in mailbox.string_lengths():
            members = list(self.types[mailbox.string_type_name(APP, length)]
                           .iter("Member"))
            self.assertEqual([m.get("Name") for m in members], ["LEN", "DATA"])
            self.assertEqual(members[0].get("DataType"), "DINT")
            self.assertEqual(members[1].get("DataType"), "SINT")
            self.assertEqual(int(members[1].get("Dimension")), length)

    def test_the_request_carries_every_declared_member_in_order(self):
        members = [m.get("Name") for m in
                   self.types[mailbox.request_type_name(APP)].iter("Member")]
        self.assertEqual(members, [n for n, _, _, _ in mailbox.REQUEST_MEMBERS])

    def test_the_response_carries_every_declared_member_in_order(self):
        members = [m.get("Name") for m in
                   self.types[mailbox.response_type_name(APP)].iter("Member")]
        self.assertEqual(members, [n for n, _, _, _ in mailbox.RESPONSE_MEMBERS])

    def test_no_mailbox_member_is_a_bool(self):
        for type_name in (mailbox.request_type_name(APP),
                          mailbox.response_type_name(APP)):
            kinds = {m.get("DataType")
                     for m in self.types[type_name].iter("Member")}
            self.assertNotIn("BOOL", kinds)

    def test_a_string_member_points_at_a_string_type(self):
        request = self.types[mailbox.request_type_name(APP)]
        by_name = {m.get("Name"): m.get("DataType") for m in request.iter("Member")}
        self.assertEqual(by_name["TargetPath"],
                         mailbox.string_type_name(APP, mailbox.TARGET_PATH_LENGTH))
        self.assertEqual(by_name["User"],
                         mailbox.string_type_name(APP, mailbox.USER_LENGTH))

    def test_the_scalar_members_are_dints(self):
        request = self.types[mailbox.request_type_name(APP)]
        by_name = {m.get("Name"): m.get("DataType") for m in request.iter("Member")}
        for name in ("Kind", "IntValue", "BoolValue", "DurationMs", "Sequence"):
            self.assertEqual(by_name[name], "DINT", name)


class AccessTests(unittest.TestCase):
    """Who can write what. This is the whole security surface of the mailbox."""

    @classmethod
    def setUpClass(cls):
        cls.root, cls.text = emit()
        cls.tags = {t.get("Name"): t for t in cls.root.iter("Tag")}

    def test_the_request_is_the_writable_surface(self):
        self.assertEqual(
            self.tags[mailbox.request_tag_name(APP)].get("ExternalAccess"),
            "Read/Write")

    def test_the_response_cannot_be_written_by_a_client(self):
        # Otherwise a client could write its own AckSequence and manufacture an
        # acknowledgement for a command the machine never saw.
        self.assertEqual(
            self.tags[mailbox.response_tag_name(APP)].get("ExternalAccess"),
            "Read Only")

    def test_the_handlers_last_sequence_is_reachable_by_nobody(self):
        # It is the replay guard. Published, it would be the way around itself.
        self.assertEqual(
            self.tags[f"FRK_{APP.name}_HmiLastSequence"].get("ExternalAccess"),
            "None")

    def test_the_mailbox_is_writable_and_its_answer_is_not(self):
        access = {n: t.get("ExternalAccess") for n, t in self.tags.items()}
        self.assertEqual(access[mailbox.request_tag_name(APP)], "Read/Write")
        self.assertEqual(access[mailbox.response_tag_name(APP)], "Read Only")

    def test_the_mailbox_does_not_yet_have_the_write_surface_to_itself(self):
        """AB §11.2.1 is not met yet, and this records by how much.

        The rule is mailbox Read/Write, public Read Only, everything else None.
        The generator still emits the contract structures and the request tags
        the mailbox routes to as Read/Write, so a CIP client can write
        `FRK_Press_Unit` or `FRK_Press_RunRequest` directly and never meet the
        gateway's Core §14 gate. That is a real bypass, it is owed work, and it
        is asserted here so that closing it breaks this test rather than passing
        unnoticed - and so that nobody reads the mailbox's arrival as having
        closed it.
        """
        controller = self.root.find("./Controller/Tags")
        writable = {t.get("Name") for t in controller.findall("Tag")
                    if t.get("ExternalAccess") == "Read/Write"}
        self.assertIn(mailbox.request_tag_name(APP), writable)
        routed = {f"FRK_{APP.name}_RunRequest", f"FRK_{APP.name}_AbortRequest",
                  f"FRK_{APP.name}_ResetRequest", f"FRK_{APP.name}_ModeRequest",
                  f"FRK_{APP.name}_DecisionAnswer"}
        self.assertTrue(routed <= writable,
                        "the routed request tags stopped being writable - if "
                        "that was deliberate, the bypass is closed and this "
                        "test should be replaced by the §11.2.1 assertion")


class InitialValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.text = emit()
        cls.tags = {t.get("Name"): t for t in cls.root.iter("Tag")}

    def test_the_mailbox_starts_uncommanded(self):
        # Kind 0 and Sequence 0: a freshly downloaded controller has not been
        # commanded, and must not look as though it has.
        request = self.tags[mailbox.request_tag_name(APP)]
        values = {m.get("Name"): int(m.get("Value"))
                  for m in request.iter("DataValueMember")
                  if m.get("Value") is not None}
        self.assertEqual(values["Kind"], mailbox.UNCOMMANDED)
        self.assertEqual(values["Sequence"], 0)

    def test_the_response_starts_unacknowledged(self):
        response = self.tags[mailbox.response_tag_name(APP)]
        values = {m.get("Name"): int(m.get("Value"))
                  for m in response.iter("DataValueMember")
                  if m.get("Value") is not None}
        self.assertEqual(values["AckSequence"], 0)
        self.assertEqual(values["Accepted"], 0)

    def test_every_string_starts_empty_and_quoted(self):
        # Logix stores an ASCII string only when it is quoted; an empty one is
        # still quoted. This is the defect the manifest hit.
        # Checked against the emitted text, not a reparse.
        self.assertIn("<![CDATA['']]>", self.text)
        for tag_name in (mailbox.request_tag_name(APP),
                         mailbox.response_tag_name(APP)):
            start = self.text.index(f'<Tag Name="{tag_name}"')
            end = self.text.index("</Tag>", start)
            body = self.text[start:end]
            self.assertNotIn("<![CDATA[]]>", body)


if __name__ == "__main__":
    unittest.main()

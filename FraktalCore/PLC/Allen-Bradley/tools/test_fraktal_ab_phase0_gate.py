"""Tests for the gate's string read-back stage.

The stage exists because an import can accept every string it is given and store
none of them. That is not a hypothetical: the first manifest build emitted 208
strings, imported with two warnings and zero errors, and read back empty. The
negative tests below are the ones that matter - a stage that cannot fail when
the content is dropped would restate the same silence it was added to break.
"""

import tempfile
import unittest
from pathlib import Path

import fraktal_ab_phase0_gate as gate

NL = chr(10)


def project(*payloads):
    """A minimal L5X-shaped text carrying one ASCII member per payload."""
    parts = ["<RSLogix5000Content>"]
    for payload in payloads:
        parts.append('<DataValueMember Name="DATA" DataType="K" Radix="ASCII">')
        parts.append("<![CDATA[" + payload + "]]>")
        parts.append("</DataValueMember>")
    parts.append("</RSLogix5000Content>")
    return NL.join(parts)


def run(source_text, exported_text):
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "app_fixture.L5X"
        first = Path(directory) / "app_pass1.L5X"
        source.write_text(source_text, encoding="utf-8")
        first.write_text(exported_text, encoding="utf-8")
        return gate.string_readback(source, first)


class StringPayloadTests(unittest.TestCase):
    def test_it_unwraps_the_cdata(self):
        self.assertEqual(gate.string_payloads(project("'a'", "'b'")),
                         ["'a'", "'b'"])

    def test_an_empty_payload_is_reported_as_empty(self):
        self.assertEqual(gate.string_payloads(project("")), [""])

    def test_a_project_with_no_strings_yields_nothing(self):
        self.assertEqual(gate.string_payloads("<RSLogix5000Content/>"), [])

    def test_a_trailing_ascii_member_cannot_read_past_the_end(self):
        text = '<DataValueMember Name="DATA" DataType="K" Radix="ASCII">'
        self.assertEqual(gate.string_payloads(text), [])


class StringReadbackTests(unittest.TestCase):
    def test_it_passes_when_every_string_survives(self):
        text = project("'one'", "'two'")
        stage = run(text, text)
        self.assertTrue(stage.passed)
        self.assertEqual(stage.detail["emittedNonEmpty"], 2)
        self.assertEqual(stage.detail["survivedNonEmpty"], 2)

    def test_it_fails_when_the_import_stored_nothing(self):
        # The exact recorded failure: emitted with content, read back blank.
        stage = run(project("'one'", "'two'"), project("", ""))
        self.assertFalse(stage.passed)
        self.assertEqual(stage.detail["survivedNonEmpty"], 0)
        self.assertEqual(stage.detail["lost"], ["'one'", "'two'"])

    def test_it_fails_when_one_string_is_dropped(self):
        stage = run(project("'one'", "'two'"), project("'one'", ""))
        self.assertFalse(stage.passed)
        self.assertIn("'two'", stage.detail["lost"])

    def test_it_fails_when_a_string_comes_back_changed(self):
        stage = run(project("'one'"), project("'on'"))
        self.assertFalse(stage.passed)
        self.assertEqual(stage.detail["lost"], ["'one'"])

    def test_a_project_with_no_strings_passes_without_claiming_anything(self):
        stage = run("<RSLogix5000Content/>", "<RSLogix5000Content/>")
        self.assertTrue(stage.passed)
        self.assertEqual(stage.detail["emittedNonEmpty"], 0)

    def test_the_stage_is_named_for_the_fixture(self):
        stage = run(project("'one'"), project("'one'"))
        self.assertEqual(stage.name, "app:strings")


if __name__ == "__main__":
    unittest.main()

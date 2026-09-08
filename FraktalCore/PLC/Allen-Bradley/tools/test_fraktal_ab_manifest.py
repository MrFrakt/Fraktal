"""Tests for the controller-resident manifest.

The manifest is the gateway's only discovery surface, so the tests worth having
are the ones that catch it lying. Two failure modes are already recorded, and
both are pinned below:

* A string that *imports* but arrives empty. Bare ASCII text in a decorated
  structure imports with a warning and Logix zeroes the member - the project
  then carries a manifest whose every name is blank. Import success is not
  publication, so the quoted form is tested directly and the bare one rejected.
* A rendition detail reaching a published contract. The declared graph is
  described once, rendition-agnostic; the harness's selector is not operator
  data and must not appear anywhere in the manifest.
"""

import dataclasses
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
from test_fraktal_ab_generate import SEED

OPEN_CDATA = "<![CDATA["
CLOSE_CDATA = "]]>"
NL = chr(10)


def emit_project_text():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "seed.L5X"
        source.write_text(SEED, encoding="utf-8")
        output = Path(directory) / "app.L5X"
        gen.generate(demo.application(), source, output)
        return output.read_text(encoding="utf-8")


def ascii_payloads(text):
    """Every ASCII string payload emitted, in order, unwrapped from its CDATA."""
    lines = text.split(NL)
    found = []
    for index, line in enumerate(lines):
        if 'Radix="ASCII"' in line and "DataValueMember" in line:
            payload = lines[index + 1]
            if payload.startswith(OPEN_CDATA) and payload.endswith(CLOSE_CDATA):
                payload = payload[len(OPEN_CDATA):-len(CLOSE_CDATA)]
            found.append(payload)
    return found


def header_values(app, xml):
    """The manifest header's scalar members, by name."""
    root = ET.fromstring("<Controller>" + xml + "</Controller>")
    for tag in root.iter("Tag"):
        if tag.get("Name") == manifest.header_tag(app):
            return {m.get("Name"): int(m.get("Value"))
                    for m in tag.iter("DataValueMember")
                    if m.get("Value") is not None}
    raise AssertionError("no manifest header tag was emitted")


class AsciiLiteralTests(unittest.TestCase):
    def test_plain_text_is_quoted(self):
        self.assertEqual(manifest.ascii_literal("press"), "'press'")

    def test_empty_text_is_still_quoted(self):
        self.assertEqual(manifest.ascii_literal(""), "''")

    def test_dollar_is_escaped(self):
        self.assertEqual(manifest.ascii_literal("a$b"), "'a$$b'")

    def test_quote_is_escaped(self):
        self.assertEqual(manifest.ascii_literal("it" + chr(39) + "s"), "'it$'s'")

    def test_control_characters_become_hex(self):
        self.assertEqual(manifest.ascii_literal(chr(9)), "'$09'")

    def test_non_latin_characters_do_not_escape_the_quoting(self):
        rendered = manifest.ascii_literal(chr(0x2014))
        self.assertTrue(rendered.startswith("'"))
        self.assertTrue(rendered.endswith("'"))
        self.assertNotIn(chr(0x2014), rendered)


class StringEmissionTests(unittest.TestCase):
    """Logix drops an unquoted string. These pin the form that survives import."""

    def setUp(self):
        self.app = demo.application()
        self.xml = NL.join(manifest.tags(self.app, "1769-L24ER-QB1B/A 33.014"))

    def test_every_payload_is_quoted(self):
        payloads = ascii_payloads(self.xml)
        self.assertTrue(payloads)
        for payload in payloads:
            self.assertTrue(payload.startswith("'"), payload)
            self.assertTrue(payload.endswith("'"), payload)

    def test_bare_text_is_never_emitted(self):
        # The exact regression: the first build published these unquoted. Logix
        # accepted the file, warned twice, and stored nothing.
        self.assertNotIn(OPEN_CDATA + "project.", self.xml)
        self.assertNotIn(OPEN_CDATA + "1769-", self.xml)

    def test_declared_length_counts_characters_not_escapes(self):
        member = manifest._string_member("K", "T", "a$b", 32)
        self.assertIn('Name="LEN" DataType="DINT" Radix="Decimal" Value="3"', member)
        self.assertIn(OPEN_CDATA + "'a$$b'" + CLOSE_CDATA, member)

    def test_a_key_that_does_not_fit_fails_the_build(self):
        # Truncation is how two different paths would come to be published under
        # one name, so it is refused rather than performed quietly.
        with self.assertRaises(ValueError):
            manifest._string_member("K", "T", "x" * 33, 32)


class KeyWidthTests(unittest.TestCase):
    """The published key string is sized to the declaration, not to a constant."""

    def setUp(self):
        self.app = demo.application()
        self.width = manifest.key_string_length(demo.application())

    def test_every_localization_key_fits_the_published_string(self):
        for row in manifest.content(self.app)["Localization"]:
            self.assertLessEqual(len(row["PortableKey"]), self.width,
                                 row["PortableKey"])

    def test_no_two_keys_share_a_published_name(self):
        # The failure a fixed 32 produced: two distinct paths cut to the same
        # text. A client resolving by name would have conflated them.
        published = [row["PortableKey"][:self.width]
                     for row in manifest.content(self.app)["Localization"]]
        self.assertEqual(len(published), len(set(published)))

    def test_the_width_covers_the_longest_declared_key(self):
        longest = max(len(row["PortableKey"])
                      for row in manifest.content(self.app)["Localization"])
        self.assertGreaterEqual(self.width, longest)
        self.assertLess(self.width - longest, manifest.KEY_STRING_GRANULARITY)

    def test_the_width_never_falls_below_the_declared_minimum(self):
        self.assertGreaterEqual(self.width, manifest.KEY_STRING_MINIMUM)

    def test_the_width_is_published_in_the_header(self):
        header = header_values(
            self.app, NL.join(manifest.tags(self.app, "controller")))
        self.assertEqual(header["KeyLength"], self.width)

    def test_the_type_name_carries_the_width(self):
        self.assertTrue(
            manifest.key_string_type(self.app).endswith(str(self.width)))


class HeaderTests(unittest.TestCase):
    def setUp(self):
        self.app = demo.application()
        self.xml = NL.join(manifest.tags(self.app, "controller"))
        self.header = header_values(self.app, self.xml)

    def test_counts_match_the_rows_actually_emitted(self):
        rows = manifest.content(self.app)
        for table in manifest.tables(self.app):
            self.assertEqual(self.header[table.name + "Count"],
                             len(rows[table.name]), table.name)

    def test_capacities_are_published_so_a_reader_never_guesses(self):
        for table in manifest.tables(self.app):
            self.assertEqual(self.header[table.name + "Capacity"],
                             table.capacity, table.name)

    def test_every_table_fits_and_the_manifest_says_so(self):
        for table in manifest.tables(self.app):
            self.assertLessEqual(self.header[table.name + "Count"],
                                 self.header[table.name + "Capacity"], table.name)
        self.assertEqual(self.header["Truncated"], 0)
        self.assertEqual(self.header["Valid"], 1)

    def test_an_overflowing_table_is_declared_invalid(self):
        # The negative test for the flag. A manifest that does not fit has to
        # say so: a client trusting a silently short table is worse off than one
        # that refuses to proceed.
        original = manifest.tables
        squeezed = tuple(
            manifest.Table(t.name, t.symbol, t.row_type, t.members,
                           1 if t.name == "Localization" else t.capacity)
            for t in original(self.app))
        manifest.tables = lambda app: squeezed
        try:
            header = header_values(
                self.app, NL.join(manifest.tags(self.app, "controller")))
        finally:
            manifest.tables = original
        self.assertEqual(header["Truncated"], 1)
        self.assertEqual(header["Valid"], 0)

    def test_schema_and_magic_are_published(self):
        self.assertEqual(self.header["Magic"], manifest.MANIFEST_MAGIC)
        self.assertEqual(self.header["SchemaMajor"], manifest.MANIFEST_SCHEMA_MAJOR)
        self.assertEqual(self.header["SchemaMinor"], manifest.MANIFEST_SCHEMA_MINOR)


class RenditionAgnosticTests(unittest.TestCase):
    """The declared graph is described once, whichever language rendered it."""

    def setUp(self):
        self.app = demo.application()
        self.xml = NL.join(manifest.tags(self.app, "controller"))

    def test_the_harness_selector_is_not_published(self):
        harness = gen.harness_only_tags(self.app)
        self.assertTrue(harness, "the press demo must have harness-only tags")
        for tag in harness:
            self.assertNotIn(tag, self.xml, tag)

    def test_no_rendition_is_named_anywhere_in_the_manifest(self):
        text = repr(manifest.content(self.app))
        for word in ("Rendition", "rendition", "SFC", "Ladder", "RLL"):
            self.assertNotIn(word, text, word)

    def test_content_is_identical_whichever_renditions_are_declared(self):
        # The same declared graph carried in one language and in three must
        # publish the same contract, byte for byte. Anything else means the
        # manifest is describing an emission instead of the declaration.
        chains = tuple(dataclasses.replace(c, renditions=(decl.ST,))
                       for c in self.app.chains)
        single = dataclasses.replace(self.app, chains=chains)
        self.assertEqual(manifest.content_hash(single),
                         manifest.content_hash(self.app))
        self.assertEqual(NL.join(manifest.tags(single, "controller")), self.xml)


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.app = demo.application()
        self.rows = manifest.content(self.app)

    def test_every_declared_module_is_described(self):
        self.assertEqual(len(self.rows["Modules"]), len(self.app.modules) + 1)

    def test_every_declared_reason_is_rationalized(self):
        self.assertEqual(len(self.rows["Rationalization"]), len(self.app.reasons))

    def test_the_root_is_the_only_root(self):
        self.assertEqual(len(self.rows["Roots"]), 1)

    def test_localization_keys_are_unique(self):
        portable = [row["PortableKey"] for row in self.rows["Localization"]]
        self.assertEqual(len(portable), len(set(portable)))

    def test_numeric_keys_are_unique(self):
        numeric = [row["NumericKey"] for row in self.rows["Localization"]]
        self.assertEqual(len(numeric), len(set(numeric)))

    def test_every_field_resolves_to_a_localization_key(self):
        known = {row["NumericKey"] for row in self.rows["Localization"]}
        for row in self.rows["Fields"]:
            self.assertIn(row["PathKey"], known)

    def test_every_operation_is_gated_or_declared_ungated(self):
        for row in self.rows["Operations"]:
            self.assertIn(row["GatedAction"], (0, 1))


class HashTests(unittest.TestCase):
    def test_the_content_hash_is_stable(self):
        self.assertEqual(manifest.content_hash(demo.application()),
                         manifest.content_hash(demo.application()))

    def test_the_content_hash_moves_when_the_declaration_moves(self):
        app = demo.application()
        changed = dataclasses.replace(
            app, reasons=dict(app.reasons, EXTRA_REASON=6199))
        self.assertNotEqual(manifest.content_hash(changed),
                            manifest.content_hash(app))

    def test_the_config_revision_moves_with_the_content(self):
        app = demo.application()
        changed = dataclasses.replace(
            app, reasons=dict(app.reasons, EXTRA_REASON=6199))
        self.assertNotEqual(manifest.config_revision(changed),
                            manifest.config_revision(app))

    def test_the_config_revision_is_not_ordered(self):
        # It is derived from the content hash, so a later revision can be
        # numerically smaller. A client that caches "the highest revision seen"
        # would silently miss a change; this pins the fact so nobody writes one.
        app = demo.application()
        base = manifest.config_revision(app)
        smaller = [
            manifest.config_revision(
                dataclasses.replace(app, reasons=dict(app.reasons,
                                                      **{f"EXTRA_{n}": 6200 + n})))
            for n in range(12)
        ]
        self.assertTrue(any(value < base for value in smaller),
                        "no smaller revision found; the claim needs rechecking")


class KeyIdentityTests(unittest.TestCase):
    """The portable string is the identity; the number is a per-revision index."""

    def numeric_keys(self, app):
        return {row["PortableKey"]: row["NumericKey"]
                for row in manifest.content(app)["Localization"]}

    def test_the_same_declaration_assigns_the_same_numbers(self):
        self.assertEqual(self.numeric_keys(demo.application()),
                         self.numeric_keys(demo.application()))

    def test_a_changed_declaration_may_renumber_an_unchanged_name(self):
        # Keys are assigned in first-encounter order, so inserting a module
        # renumbers everything discovered after it. A client must resolve names
        # through the Localization table it read with the tables it is reading.
        app = demo.application()
        moved = dataclasses.replace(app, modules=tuple(reversed(app.modules)))
        before, after = self.numeric_keys(app), self.numeric_keys(moved)
        shared = set(before) & set(after)
        self.assertTrue(shared)
        self.assertTrue(any(before[name] != after[name] for name in shared),
                        "reordering the declaration renumbered nothing")

    def test_every_numeric_key_resolves_to_exactly_one_name(self):
        keys = self.numeric_keys(demo.application())
        self.assertEqual(len(set(keys.values())), len(keys))


class ProjectEmissionTests(unittest.TestCase):
    """The manifest has to survive the generator, not only its own module."""

    @classmethod
    def setUpClass(cls):
        cls.text = emit_project_text()
        cls.root = ET.fromstring(cls.text)

    def test_the_manifest_tags_are_in_the_project(self):
        app = demo.application()
        names = {t.get("Name") for t in self.root.iter("Tag")}
        self.assertIn(manifest.header_tag(app), names)
        for table in manifest.tables(app):
            self.assertIn(manifest.manifest_tag(app, table), names)

    def test_the_manifest_types_are_in_the_project(self):
        app = demo.application()
        names = {t.get("Name") for t in self.root.iter("DataType")}
        self.assertIn(manifest.header_type(app), names)
        self.assertIn(manifest.key_string_type(app), names)

    def test_the_key_string_type_is_a_logix_string(self):
        app = demo.application()
        for data_type in self.root.iter("DataType"):
            if data_type.get("Name") == manifest.key_string_type(app):
                self.assertEqual(data_type.get("Family"), "StringFamily")
                members = {m.get("Name"): m for m in data_type.iter("Member")}
                self.assertEqual(members["DATA"].get("DataType"), "SINT")
                self.assertEqual(int(members["DATA"].get("Dimension")),
                                 manifest.key_string_length(app))
                return
        raise AssertionError("the key string type was not emitted")

    def test_the_manifest_is_read_only_to_a_client(self):
        app = demo.application()
        published = {manifest.header_tag(app)}
        for table in manifest.tables(app):
            published.add(manifest.manifest_tag(app, table))
        for tag in self.root.iter("Tag"):
            if tag.get("Name") in published:
                self.assertEqual(tag.get("ExternalAccess"), "Read Only",
                                 tag.get("Name"))

    def test_every_emitted_string_in_the_project_is_quoted(self):
        payloads = ascii_payloads(self.text)
        self.assertTrue(payloads)
        for payload in payloads:
            self.assertTrue(payload.startswith("'"), payload)
            self.assertTrue(payload.endswith("'"), payload)

    def test_the_evidence_reports_what_was_emitted(self):
        app = demo.application()
        evidence = manifest.evidence(app)
        rows = manifest.content(app)
        self.assertFalse(evidence["Truncated"])
        self.assertEqual(evidence["ContentHash"], manifest.content_hash(app))
        for table in manifest.tables(app):
            self.assertEqual(evidence["Tables"][table.name]["rows"],
                             len(rows[table.name]))


if __name__ == "__main__":
    unittest.main()

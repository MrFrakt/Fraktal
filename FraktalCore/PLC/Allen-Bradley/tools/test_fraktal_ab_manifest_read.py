"""Tests for the controller-side manifest read.

The decoder is checked against a byte image built independently here, the way
Logix lays a structure out - DINT members little-endian, a string member as LEN
followed by a fixed DATA array - rather than against the decoder's own idea of
the layout. Checking a parser with its own packer proves only that it is
self-consistent.

The comparison tests are the ones that carry weight on the bench: a read that
cannot report a difference would turn a wrong manifest into a passing run.
"""

import struct
import unittest

import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as mr


def pack_string(text, width):
    raw = text.encode("ascii")
    return struct.pack("<i", len(raw)) + raw + bytes(width - len(raw))


def pack_row(table, row, width):
    out = b""
    for name, logical_type in table.members:
        if logical_type == manifest.KEY32:
            out += pack_string(str(row.get(name, "")), width)
        else:
            out += struct.pack("<i", int(row.get(name, 0)))
    return out


def pack_table(table, rows, width):
    out = b""
    for index in range(table.capacity):
        row = rows[index] if index < len(rows) else {}
        out += pack_row(table, row, width)
    return out


def pack_header(app, width, identity, overrides=None):
    values = {
        "Magic": manifest.MANIFEST_MAGIC,
        "SchemaMajor": manifest.MANIFEST_SCHEMA_MAJOR,
        "SchemaMinor": manifest.MANIFEST_SCHEMA_MINOR,
        "CoreVersion": manifest.CORE_VERSION,
        "BindingVersion": manifest.BINDING_VERSION,
        "FrameworkVersion": manifest.FRAMEWORK_VERSION,
        "ConfigRevision": manifest.config_revision(app),
        "Valid": 1,
        "Truncated": 0,
        "KeyLength": width,
        "ContentHash": manifest.content_hash(app),
        "ControllerIdentity": identity,
    }
    rows = manifest.content(app)
    for table in manifest.tables(app):
        values[f"{table.name}Count"] = len(rows[table.name])
        values[f"{table.name}Capacity"] = table.capacity
    values.update(overrides or {})

    out = b""
    for name, logical_type in mr.header_layout():
        if logical_type == manifest.KEY32:
            out += pack_string(str(values[name]), width)
        else:
            out += struct.pack("<i", int(values[name]))
    return out


class LayoutTests(unittest.TestCase):
    def test_a_dint_member_is_four_bytes(self):
        self.assertEqual(mr.member_bytes("DINT"), 4)

    def test_a_string_member_is_a_length_plus_its_data(self):
        self.assertEqual(mr.member_bytes(manifest.KEY32), 4 + mr.WIDTH)

    def test_the_header_size_matches_what_the_emitter_declares(self):
        expected = sum(
            mr.member_bytes(dt) for _, dt in mr.header_layout())
        self.assertEqual(mr.header_bytes(), expected)

    def test_every_table_row_size_matches_the_emitted_estimate(self):
        total = mr.header_bytes()
        for table in manifest.tables(mr.APP):
            total += mr.row_bytes(table) * table.capacity
        self.assertEqual(total, manifest.estimated_bytes(mr.APP))


class DecodeTests(unittest.TestCase):
    def test_it_decodes_a_string_member(self):
        payload = pack_string("project.module.press", mr.WIDTH)
        self.assertEqual(mr.decode_string(payload, 0), "project.module.press")

    def test_it_decodes_the_empty_string(self):
        self.assertEqual(mr.decode_string(pack_string("", mr.WIDTH), 0), "")

    def test_it_decodes_a_string_at_full_width(self):
        text = "x" * mr.WIDTH
        self.assertEqual(mr.decode_string(pack_string(text, mr.WIDTH), 0), text)

    def test_a_length_beyond_the_data_cannot_read_past_it(self):
        # A corrupt or stale LEN must not turn into a buffer overrun dressed up
        # as a name.
        payload = struct.pack("<i", 9999) + bytes(mr.WIDTH)
        self.assertEqual(len(mr.decode_string(payload, 0)), mr.WIDTH)

    def test_a_negative_length_decodes_as_empty(self):
        payload = struct.pack("<i", -5) + bytes(mr.WIDTH)
        self.assertEqual(mr.decode_string(payload, 0), "")

    def test_it_decodes_every_declared_row_of_every_table(self):
        rows = manifest.content(mr.APP)
        for table in manifest.tables(mr.APP):
            payload = pack_table(table, rows[table.name], mr.WIDTH)
            width = mr.row_bytes(table)
            got = [mr.decode_row(table, payload, i * width)
                   for i in range(len(rows[table.name]))]
            self.assertEqual(got, rows[table.name], table.name)

    def test_it_decodes_the_header(self):
        header = mr.decode_header(
            pack_header(mr.APP, mr.WIDTH, mr.CONTROLLER_IDENTITY))
        self.assertEqual(header["Magic"], manifest.MANIFEST_MAGIC)
        self.assertEqual(header["ContentHash"], manifest.content_hash(mr.APP))
        self.assertEqual(header["ControllerIdentity"], mr.CONTROLLER_IDENTITY)
        self.assertEqual(header["KeyLength"], mr.WIDTH)
        self.assertEqual(header["LocalizationCount"],
                         len(manifest.content(mr.APP)["Localization"]))


def full_tables():
    rows = manifest.content(mr.APP)
    return {t.name: {"rows": [
        mr.decode_row(t, pack_table(t, rows[t.name], mr.WIDTH), i * mr.row_bytes(t))
        for i in range(t.capacity)]}
        for t in manifest.tables(mr.APP)}


class ComparisonTests(unittest.TestCase):
    """A read that cannot report a difference is not a check."""

    def setUp(self):
        self.header = mr.decode_header(
            pack_header(mr.APP, mr.WIDTH, mr.CONTROLLER_IDENTITY))
        self.tables = full_tables()

    def test_a_faithful_manifest_compares_equal(self):
        result = mr.compare(self.header, self.tables)
        self.assertTrue(result["equal"], result["findings"])

    def test_unused_capacity_is_not_required_to_match(self):
        # The slots past a table's count are capacity, not content.
        result = mr.compare(self.header, self.tables)
        localization = result["tables"]["Localization"]
        self.assertGreater(localization["rowsRead"], localization["declaredRows"])
        self.assertTrue(localization["rowsMatch"])

    def test_a_wrong_content_hash_is_reported(self):
        header = dict(self.header, ContentHash="0000000000000000")
        result = mr.compare(header, self.tables)
        self.assertFalse(result["equal"])
        self.assertTrue(any("ContentHash" in f for f in result["findings"]))

    def test_a_wrong_controller_identity_is_reported(self):
        header = dict(self.header, ControllerIdentity="1756-L85E 36.011")
        self.assertFalse(mr.compare(header, self.tables)["equal"])

    def test_an_invalid_manifest_is_reported(self):
        header = dict(self.header, Valid=0)
        result = mr.compare(header, self.tables)
        self.assertFalse(result["equal"])
        self.assertIn("Valid is not 1", result["findings"])

    def test_a_truncated_manifest_is_reported(self):
        self.assertFalse(mr.compare(dict(self.header, Truncated=1),
                                    self.tables)["equal"])

    def test_a_count_that_disagrees_with_the_declaration_is_reported(self):
        header = dict(self.header, LocalizationCount=3)
        result = mr.compare(header, self.tables)
        self.assertFalse(result["equal"])
        self.assertTrue(any("LocalizationCount" in f for f in result["findings"]))

    def test_a_single_changed_row_is_reported(self):
        tables = {name: {"rows": list(detail["rows"])}
                  for name, detail in self.tables.items()}
        row = dict(tables["Localization"]["rows"][4])
        row["PortableKey"] = "something.else"
        tables["Localization"]["rows"][4] = row
        result = mr.compare(self.header, tables)
        self.assertFalse(result["equal"])
        self.assertTrue(any("Localization[4]" in f for f in result["findings"]))

    def test_a_table_that_read_short_is_reported(self):
        tables = dict(self.tables)
        tables["Modules"] = {"rows": []}
        self.assertFalse(mr.compare(self.header, tables)["equal"])

    def test_a_wrong_key_width_is_reported(self):
        self.assertFalse(mr.compare(dict(self.header, KeyLength=32),
                                    self.tables)["equal"])


if __name__ == "__main__":
    unittest.main()

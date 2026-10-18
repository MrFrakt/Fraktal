"""Phase 6 room: grow the declaration without truncating discovery.

The pressure declarations cross the old 512-row bounds on both the press and
the new-station template. Capacity changes must leave executable content and
the published contract's identity alone, while readers refuse an old capacity
even when that identity still matches.
"""

import dataclasses
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_press_demo as press
import fraktal_ab_station_template as template
from test_fraktal_ab_generate import SEED, emit
from test_fraktal_ab_manifest import header_values


def with_extra_fields(app, count):
    """Synthetic published data, using the same declaration path as a station."""
    record = decl.Record("RoomProbe", tuple(
        decl.scalar(f"Value{n}") for n in range(count)))
    return dataclasses.replace(app, records=app.records + (record,))


def with_label(app, length):
    records = list(app.records)
    for index, record in enumerate(records):
        for offset, member in enumerate(record.members):
            if member.editable:
                members = list(record.members)
                prefix = "project.phase6."
                members[offset] = dataclasses.replace(
                    member, label_key=prefix + "x" * (length - len(prefix)))
                records[index] = dataclasses.replace(record, members=tuple(members))
                return dataclasses.replace(app, records=tuple(records))
    raise AssertionError("the station has no editable value")


def old_tables(app):
    return tuple(dataclasses.replace(t, capacity=512)
                 if t.name in ("Fields", "Localization") else t
                 for t in manifest.tables(app))


class CapacityTests(unittest.TestCase):
    def test_the_press_has_room_beyond_both_old_bounds(self):
        self.assert_room(self.fill_remaining_room(press.application()))

    def test_the_template_has_room_beyond_both_old_bounds(self):
        self.assert_room(self.fill_remaining_room(template.application()))

    def fill_remaining_room(self, app):
        tables = manifest.evidence(app)['Tables']
        count = max(1, *(513 - tables[name]['rows'] for name in ('Fields', 'Localization')))
        self.assertGreater(count, 0)
        return with_extra_fields(app, count)

    def assert_room(self, app):
        self.assertEqual(decl.validate(app), [])
        evidence = manifest.evidence(app)
        for name in ("Fields", "Localization"):
            table = evidence["Tables"][name]
            self.assertGreater(table["rows"], 512, name)
            self.assertLessEqual(table["rows"], table["capacity"], name)
        self.assertFalse(evidence["Truncated"])
        self.assertLessEqual(evidence["EstimatedBytes"], manifest.MANIFEST_BUDGET_BYTES)
        root, _, _ = emit(app)
        header = next(t for t in root.iter("Tag")
                      if t.get("Name") == manifest.header_tag(app))
        values = {m.get("Name"): m.get("Value")
                  for m in header.iter("DataValueMember")}
        self.assertEqual(values["Valid"], "1")
        self.assertEqual(values["Truncated"], "0")

    def test_phase6_keys_can_grow_to_eighty_characters(self):
        for app in (press.application(), template.application()):
            with self.subTest(station=app.name):
                longer = with_label(app, 79)
                self.assertEqual(manifest.key_string_length(longer), 80)
                _, _, evidence = emit(longer)
                self.assertLessEqual(evidence["Manifest"]["EstimatedBytes"],
                                     manifest.MANIFEST_BUDGET_BYTES)

    def test_a_station_beyond_the_byte_budget_still_fails_closed(self):
        too_wide = with_label(press.application(), 127)
        self.assertGreater(manifest.estimated_bytes(too_wide),
                           manifest.MANIFEST_BUDGET_BYTES)
        self.assert_refused_without_output(too_wide, "manifest.*budget")

    def assert_refused_without_output(self, app, reason):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "seed.L5X", Path(directory) / "app.L5X"
            source.write_text(SEED, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, reason):
                gen.generate(app, source, output)
            self.assertFalse(output.exists(), "a refused station left a downloadable file")

    def test_overflow_of_any_table_is_refused_before_writing_a_project(self):
        app = press.application()
        content = manifest.content(app)
        for name in content:
            with self.subTest(table=name):
                squeezed = tuple(dataclasses.replace(t, capacity=len(content[name]) - 1)
                                 if t.name == name else t for t in manifest.tables(app))
                with mock.patch.object(manifest, "tables", return_value=squeezed):
                    self.assert_refused_without_output(app, "manifest.*" + name)

    def test_the_byte_budget_is_inclusive_and_checked_to_the_byte(self):
        app = press.application()
        required = manifest.estimated_bytes(app)
        with mock.patch.object(manifest, "MANIFEST_BUDGET_BYTES", required):
            emit(app)
        with mock.patch.object(manifest, "MANIFEST_BUDGET_BYTES", required - 1):
            self.assert_refused_without_output(app, "manifest.*budget")

    def test_capacity_does_not_change_the_content_or_its_identity(self):
        app = press.application()
        rows, digest, revision = (manifest.content(app), manifest.content_hash(app),
                                  manifest.config_revision(app))
        previous = old_tables(app)
        with mock.patch.object(manifest, "tables", return_value=previous):
            self.assertEqual(manifest.content(app), rows)
            self.assertEqual(manifest.content_hash(app), digest)
            self.assertEqual(manifest.config_revision(app), revision)

    def test_surface_reserve_is_bounded_and_rounds_at_growth_block_edges(self):
        self.assertEqual(manifest.SURFACE_ROW_CEILING, 768)
        for rows, capacity in ((0, 8), (1, 16), (8, 16), (9, 24), (64, 72),
                               (565, 576), (570, 584), (616, 624), (652, 664),
                               (760, 768), (761, 768), (769, 768)):
            self.assertEqual(manifest.surface_capacity(rows), capacity, rows)

    def test_each_station_allocates_its_own_surface_and_can_grow_to_the_ceiling(self):
        for app in (press.application(), template.application()):
            content = manifest.content(app)
            for table in manifest.tables(app):
                if table.name not in ('Fields', 'Localization'):
                    continue
                self.assertLess(table.capacity, manifest.SURFACE_ROW_CEILING)
                self.assertGreaterEqual(table.capacity - len(content[table.name]), manifest.SURFACE_ROW_HEADROOM)
            bigger = with_extra_fields(app, 64)
            before = {t.name: t.capacity for t in manifest.tables(app)}
            after = {t.name: t.capacity for t in manifest.tables(bigger)}
            for name in ('Fields', 'Localization'):
                self.assertEqual(after[name], before[name] + 64)

    def test_static_table_reserves_scale_with_rows_and_share_the_module_bound(self):
        for app in (press.application(), template.application()):
            content = manifest.content(app)
            capacities = {t.name: t.capacity for t in manifest.tables(app)}
            self.assertEqual(capacities['Modules'], capacities['Nameplates'])
            for name, ceiling, block in (('Roots', 4, 1), ('Modules', 16, 4),
                    ('Operations', 32, 4), ('Rationalization', 32, 4),
                    ('OptionalProfiles', 8, 2), ('WriteCapabilities', 64, 4)):
                count, capacity = len(content[name]), capacities[name]
                with self.subTest(station=app.name, table=name):
                    self.assertGreater(capacity, count)
                    self.assertLess(capacity, ceiling)
                    self.assertLessEqual(capacity - count, block)
                    self.assertEqual(capacity % block, 0)
        for count, ceiling, block, expected in ((0, 4, 1, 1), (3, 4, 1, 4),
                (4, 4, 1, 4), (5, 4, 1, 4), (4, 32, 4, 8), (32, 32, 4, 32)):
            self.assertEqual(manifest.bounded_capacity(count, ceiling, block), expected)

    def test_only_the_header_and_two_array_tags_change_in_the_project(self):
        for app in (press.application(), template.application()):
            # The sets contract already exceeds the historical 512-row bound.
            # Isolate the capacity-only comparison on the pre-set feature set.
            records = tuple(dataclasses.replace(record, members=tuple(
                dataclasses.replace(member, class_id='', min_read_level=0, min_write_level=0)
                for member in record.members)) for record in app.records if not record.line_cfg)
            app = dataclasses.replace(app, config_sets=False, config_medium=None, model_capacity=0,
                                      access_users=None, data_classes=(), records=records, line=None)
            with self.subTest(station=app.name):
                previous = old_tables(app)
                new, _, _ = emit(app)
                with mock.patch.object(manifest, "tables", return_value=previous):
                    old, _, _ = emit(app)
                changed = {manifest.header_tag(app)} | {
                    manifest.manifest_tag(app, t) for t in manifest.tables(app)
                    if t.name in ("Fields", "Localization")}
                for project in (old, new):
                    tags = project.find("Controller/Tags")
                    removed = 0
                    for tag in list(tags):
                        if tag.get("Name") in changed:
                            tags.remove(tag)
                            removed += 1
                    self.assertEqual(removed, 3)
                self.assertEqual(ET.tostring(old), ET.tostring(new))

    def test_every_declared_slot_is_emitted_in_all_arrays(self):
        app = press.application()
        project, _, _ = emit(app)
        for table in manifest.tables(app):
            tag = next(t for t in project.iter("Tag")
                       if t.get("Name") == manifest.manifest_tag(app, table))
            self.assertEqual(int(tag.get("Dimensions")), table.capacity)
            array = tag.find("Data/Array")
            self.assertEqual(len(array.findall("Element")), table.capacity)
            self.assertEqual(array.findall("Element")[-1].get("Index"),
                             f"[{table.capacity - 1}]")

    def test_the_old_controller_capacity_is_refused_despite_a_matching_hash(self):
        app = press.application()
        header = header_values(app, "\n".join(manifest.tags(app, "controller")))
        header.update(ContentHash=manifest.content_hash(app),
                      ControllerIdentity=reader.CONTROLLER_IDENTITY)
        content = manifest.content(app)
        tables = {t.name: {"rows": content[t.name] + [{}] *
                          (t.capacity - len(content[t.name]))}
                  for t in manifest.tables(app)}
        self.assertTrue(reader.compare(header, tables)["equal"])
        for name in content:
            with self.subTest(table=name):
                capacity = header[name + 'Capacity'] + 1
                stale = dict(header, **{name + "Capacity": capacity})
                result = reader.compare(stale, tables)
                self.assertFalse(result["equal"])
                self.assertTrue(any(name + f"Capacity {capacity} !=" in f
                                    for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()

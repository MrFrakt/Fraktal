import dataclasses
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_nameplate as plate
import fraktal_ab_press_demo as press
import fraktal_ab_press_echo38 as echo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st


PLATE = decl.Nameplate('Example Maker', 'Offline equipment', 'TEST-001',
    'urn:example:equipment:TEST-001', '2026', '1.2', '38.011', '0.1.0',
    'ORDER-7', 'https://example.invalid/manual')


class Nameplates(unittest.TestCase):
    def test_versioned_plate_flows_through_the_shared_snapshot_projection(self):
        app = dataclasses.replace(echo.application(), nameplate=PLATE)
        rows = manifest.content(app)
        header = dict(Magic=manifest.MANIFEST_MAGIC, SchemaMajor=5,
                      Valid=1, Truncated=0, ContentHash=manifest.content_hash(app),
                      ConfigRevision=manifest.config_revision(app))
        for table in manifest.tables(app):
            header[table.name + 'Capacity'] = table.capacity
            header[table.name + 'Count'] = len(rows[table.name])
        contexts = {m.name: st.structure(gen.module_members(m)) for m in app.modules}
        with patch.object(projection, 'APP', app):
            doc = projection.project(header, rows, st.structure(gen.unit_context_members(app)), contexts)
            self.assertEqual(doc['values']['Press/Nameplate/ManufacturerName'], PLATE.manufacturer)
            self.assertEqual(doc['values']['Press/Nameplate/FirmwareVersion'], PLATE.firmware_version)
            self.assertNotIn('Nameplate/*', [r['path'] for r in doc['absent']])
            with self.assertRaises(projection.ProjectionRefused):
                projection.validate(dict(header, SchemaMajor=4))
    def test_legacy_manifest_and_shape_stay_v4(self):
        app = press.application()
        self.assertEqual(manifest.schema_major(app), 4)
        self.assertEqual(len(next(t for t in manifest.tables(app) if t.name == 'Nameplates').members), 9)
        self.assertEqual(manifest.content(app)['Nameplates'], [])

    def test_full_identity_is_read_from_the_native_manifest(self):
        base = echo.application()
        app = dataclasses.replace(base, nameplate=PLATE,
            modules=(dataclasses.replace(base.modules[0], nameplate=dataclasses.replace(PLATE, serial='CM-001')),
                     *base.modules[1:]))
        self.assertEqual(decl.validate(app), [])
        rows = manifest.content(app)
        self.assertEqual(manifest.schema_major(app), 5)
        self.assertEqual(len(rows['Nameplates']), 2)
        projected = plate.project(rows, 1)
        for member, _, leaf in plate.FIELDS:
            self.assertEqual(projected[f'Nameplate/{leaf}'], getattr(PLATE, member))
        self.assertEqual(plate.project(rows, 2)['Nameplate/SerialNumber'], 'CM-001')
        self.assertEqual(plate.project(rows, 3), {})
        table = next(t for t in manifest.tables(app) if t.name == 'Nameplates')
        self.assertEqual(reader.row_bytes(table), 60)
        self.assertNotEqual(manifest.content_hash(base), manifest.content_hash(app))

    def test_header_versions_and_rows_are_emitted_with_text(self):
        app = dataclasses.replace(echo.application(), nameplate=PLATE)
        root = ET.fromstring(gen.controller_tags(app))
        header = root.find(f".//Tag[@Name='{manifest.header_tag(app)}']")
        self.assertIsNotNone(header)
        self.assertEqual(header.find(".//DataValueMember[@Name='SchemaMajor']").get('Value'), '5')
        self.assertIn('38.011', gen.controller_tags(app))
        self.assertIn('HardwareVersionKey', gen.data_types(app))

    def test_optional_fields_are_empty_without_invented_asset_facts(self):
        app = dataclasses.replace(press.application(), nameplate=decl.Nameplate('Maker', 'Asset', '123'))
        values = plate.project(manifest.content(app), 1)
        self.assertEqual(values['Nameplate/FirmwareVersion'], '')
        self.assertEqual(values['Nameplate/DocumentationUrl'], '')

    def test_corrupt_key_or_duplicate_plate_is_refused(self):
        rows = manifest.content(dataclasses.replace(press.application(), nameplate=PLATE))
        rows['Nameplates'][0]['SerialKey'] = 999999
        with self.assertRaises(ValueError):
            plate.project(rows, 1)
        rows['Nameplates'].append(rows['Nameplates'][0])
        with self.assertRaises(ValueError):
            plate.project(rows, 1)

    def test_bad_nameplates_are_refused_before_emission(self):
        for changes in [dict(serial=''), dict(manufacturer='\nMaker'), dict(product='x'*241),
                        dict(product='m\u00e1quina'), dict(year='202A'),
                        dict(documentation_url='javascript:alert(1)'),
                        dict(documentation_url='https://user:secret@example.invalid/manual')]:
            with self.subTest(changes=changes):
                app = dataclasses.replace(press.application(), nameplate=dataclasses.replace(PLATE, **changes))
                self.assertTrue(decl.validate(app))

    def test_ascii_xml_and_logix_escapes_preserve_asset_text(self):
        app = dataclasses.replace(press.application(), nameplate=dataclasses.replace(PLATE, product="Maker's $tool ]]> spec"))
        xml = gen.controller_tags(app)
        ET.fromstring(xml)
        text = ''.join(ET.fromstring(xml).itertext())
        self.assertIn("Maker$'s $$tool ]]$3E spec", text)


class EchoDerivation(unittest.TestCase):
    def test_variant_differences_are_deployment_properties_only(self):
        base, variant = press.application(), echo.application()
        differences = {f.name for f in dataclasses.fields(base) if getattr(base, f.name) != getattr(variant, f.name)}
        self.assertEqual(differences, {'controller', 'major_revision', 'comment', 'io_modules',
                                     'access_users', 'controller_identity', 'simulation_mailbox_rw'})
        self.assertEqual(variant.access_users[:-1], base.access_users)
        self.assertFalse(base.simulation_mailbox_rw)
        self.assertEqual(variant.io_modules, ())

    def test_shared_declaration_changes_flow_to_the_variant(self):
        changed = dataclasses.replace(press.application(), stall_time_ms=12340)
        with patch.object(press, 'application', return_value=changed):
            self.assertEqual(echo.application().stall_time_ms, 12340)


if __name__ == '__main__':
    unittest.main()

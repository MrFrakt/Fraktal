"""Tests for WP6.6 Increment C6: private Unit/Chart tags and V5 table retirement."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fraktal_ab_collapse as collapse
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s6_collapse_demo as genealogy_s6
import fraktal_ab_genealogy_s6_host_demo as genealogy_host
import fraktal_ab_manifest as manifest
import fraktal_ab_press_canonical_echo38 as press_canonical
import fraktal_ab_press_s6_collapse_echo38 as press_s6
import fraktal_ab_press_s6_shelving_echo38 as press_shelving


V5_RETIRED_TABLES = (
    "Roots",
    "Modules",
    "Nameplates",
    "Fields",
    "Operations",
    "Rationalization",
    "OptionalProfiles",
)
KEPT_TABLES = ("Localization", "WriteCapabilities")


class CollapseC6TableAccessTests(unittest.TestCase):
    def test_collapsed_profiles_retire_unit_chart_and_v5_tables_to_none(self):
        for decl, name in (
            (press_s6, "press_s6_collapse"),
            (press_shelving, "press_s6_shelving"),
            (genealogy_s6, "genealogy_s6_collapse"),
        ):
            with self.subTest(profile=name):
                app = decl.application()
                self.assertTrue(collapse.enabled(app))

                # Check controller tag definitions generated for Unit and Chart
                tags_xml = gen.controller_tags(app)
                root = ET.fromstring(tags_xml)
                tag_map = {t.get("Name"): t for t in root.iter("Tag")}

                unit_tag = tag_map.get(f"FRK_{app.name}_Unit")
                self.assertIsNotNone(unit_tag)
                self.assertEqual(unit_tag.get("ExternalAccess"), "None")

                chart_tag = tag_map.get(f"FRK_{app.name}_Chart")
                self.assertIsNotNone(chart_tag)
                self.assertEqual(chart_tag.get("ExternalAccess"), "None")

                header_tag = tag_map.get(f"FRK_{app.name}_MfHeader")
                self.assertIsNotNone(header_tag)
                self.assertEqual(header_tag.get("ExternalAccess"), "None")

                for table_name in V5_RETIRED_TABLES:
                    tag = tag_map.get(f"FRK_{app.name}_Mf{table_name}")
                    self.assertIsNotNone(tag, f"Expected tag FRK_{app.name}_Mf{table_name} to exist")
                    self.assertEqual(
                        tag.get("ExternalAccess"),
                        "None",
                        f"Expected FRK_{app.name}_Mf{table_name} to have ExternalAccess='None'",
                    )

                for table_name in KEPT_TABLES:
                    tag = tag_map.get(f"FRK_{app.name}_Mf{table_name}")
                    self.assertIsNotNone(tag, f"Expected tag FRK_{app.name}_Mf{table_name} to exist")
                    self.assertEqual(
                        tag.get("ExternalAccess"),
                        "Read Only",
                        f"Expected FRK_{app.name}_Mf{table_name} to have ExternalAccess='Read Only'",
                    )

    def test_legacy_uncollapsed_profiles_retain_read_only_access(self):
        for decl, name in (
            (press_canonical, "press_canonical"),
            (genealogy_host, "genealogy_host"),
        ):
            with self.subTest(profile=name):
                app = decl.application()
                self.assertFalse(collapse.enabled(app))

                tags_xml = gen.controller_tags(app)
                root = ET.fromstring(tags_xml)
                tag_map = {t.get("Name"): t for t in root.iter("Tag")}

                unit_tag = tag_map.get(f"FRK_{app.name}_Unit")
                self.assertIsNotNone(unit_tag)
                self.assertEqual(unit_tag.get("ExternalAccess"), "Read Only")

                chart_tag = tag_map.get(f"FRK_{app.name}_Chart")
                self.assertIsNotNone(chart_tag)
                self.assertEqual(chart_tag.get("ExternalAccess"), "Read Only")

                header_tag = tag_map.get(f"FRK_{app.name}_MfHeader")
                self.assertIsNotNone(header_tag)
                self.assertEqual(header_tag.get("ExternalAccess"), "Read Only")

                for table_name in V5_RETIRED_TABLES + KEPT_TABLES:
                    tag = tag_map.get(f"FRK_{app.name}_Mf{table_name}")
                    self.assertIsNotNone(tag)
                    self.assertEqual(
                        tag.get("ExternalAccess"),
                        "Read Only",
                        f"Expected FRK_{app.name}_Mf{table_name} to remain 'Read Only' in uncollapsed profile",
                    )


if __name__ == "__main__":
    unittest.main()

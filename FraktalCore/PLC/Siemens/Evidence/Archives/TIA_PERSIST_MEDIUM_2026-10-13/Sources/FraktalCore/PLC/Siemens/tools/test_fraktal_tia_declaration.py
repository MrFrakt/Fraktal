"""Containment and source-derived identity checks for the reference declaration."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

import fraktal_tia_declaration as DECL

FIXTURE = Path(__file__).resolve().parents[1] / "Tests/Declaration/two_root_forest.json"


class DeclarationTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(FIXTURE.read_text(encoding="ascii"))
        self.core = DECL.CoreFacts.read()

    def rejected(self, rule):
        with self.assertRaises(DECL.DeclarationError) as raised:
            DECL.validate(self.value, self.core)
        self.assertEqual(raised.exception.rule, rule)

    def test_two_roots_reuse_types_and_preserve_parent_first_order(self):
        model = DECL.validate(self.value, self.core)
        self.assertEqual([item.path for item in model.instances],
                         ["StationA", "StationA.Cell", "StationA.Cell.Clamp", "StationA.Cell.Gate",
                          "StationB", "StationB.Cell", "StationB.Cell.Clamp", "StationB.Cell.Gate"])
        self.assertEqual([item.parent_index for item in model.instances], [0, 1, 2, 2, 0, 5, 6, 6])
        self.assertEqual([item.index for item in model.instances], list(range(1, 9)))
        self.assertEqual([item["module_type"] for item in model.inventory()["instances"]],
                         [1, 2, 3, 3, 1, 2, 3, 3])
        self.assertEqual(model.inventory(), DECL.read(FIXTURE).inventory())

    def test_equipment_module_cannot_contain_unit(self):
        self.value["types"][1]["children"][0]["type"] = "FB_DeclarationUnit"
        self.rejected("T-TIER")

    def test_control_module_is_a_leaf(self):
        self.value["types"][2]["children"] = [{"name": "Nested", "type": "FB_DeclarationCylinder"}]
        self.rejected("T-TIER")

    def test_each_root_is_a_unit(self):
        self.value["roots"][0]["type"] = "FB_DeclarationCell"
        self.rejected("T-TIER")

    def test_recursive_type_cycle_is_rejected(self):
        self.value["types"][0]["children"].append({"name": "Nested", "type": "FB_DeclarationUnit"})
        self.rejected("T-TIER")

    def test_unknown_type_is_not_silently_ignored(self):
        self.value["types"][1]["children"][0]["type"] = "FB_Absent"
        self.rejected("T-TIER")

    def test_sibling_case_collision_and_frame_member_collision(self):
        for name in ("clamp", "Status", "CORE"):
            with self.subTest(name=name):
                self.value["types"][1]["children"][1]["name"] = name
                self.rejected("T-COLLIDE")

    def test_type_and_root_names_are_case_insensitive(self):
        self.value["types"].append(copy.deepcopy(self.value["types"][2]))
        self.value["types"][-1]["name"] = "FB_declarationCylinder"
        self.rejected("T-COLLIDE")
        self.value = json.loads(FIXTURE.read_text())
        self.value["roots"][1]["name"] = "stationa"
        self.rejected("T-COLLIDE")

    def test_local_name_cannot_contain_path_separator_or_unicode(self):
        for name in ("Root.Child", "\u03a9", "dt"):
            self.value["roots"][0]["name"] = name
            self.rejected("T-COLLIDE")

    def test_qualified_path_and_type_key_use_core_widths(self):
        self.value["roots"][0]["name"] = "R" * self.core.name_width
        self.rejected("T-WIDTH")
        self.value = json.loads(FIXTURE.read_text())
        self.value["types"][0]["type_key"] = "K" * (self.core.key_width + 1)
        self.rejected("T-WIDTH")

    def test_registry_capacity_excludes_row_zero(self):
        self.value["registry_capacity"] = 8
        self.assertEqual(len(DECL.validate(self.value, self.core).instances), 8)
        for capacity in (7, 0, True):
            self.value["registry_capacity"] = capacity
            self.rejected("T-GEN")

    def test_no_unconsumed_type_or_unrecognized_field(self):
        self.value["types"].append({"name": "FB_Unused", "tier": "CONTROL_MODULE", "children": []})
        self.rejected("T-GEN")
        self.value = json.loads(FIXTURE.read_text())
        self.value["types"][0]["future_flag"] = True
        self.rejected("T-GEN")

    def test_1200_profile_and_unknown_version_are_not_claimed(self):
        self.value["target_family"] = "S7-1200"
        self.rejected("T-GEN")
        self.value = json.loads(FIXTURE.read_text())
        for version in (2, True):
            self.value["schema_version"] = version
            self.rejected("T-GEN")

    def test_empty_forest_and_none_tier_are_rejected(self):
        self.value["roots"] = []
        self.rejected("T-TIER")
        self.value = json.loads(FIXTURE.read_text())
        self.value["types"][0]["tier"] = "NONE"
        self.rejected("T-TIER")

    def test_nested_units_are_allowed_without_a_super_root(self):
        self.value["types"].insert(0, {"name": "FB_OuterUnit", "tier": "UNIT", "children": [
            {"name": "Inner", "type": "FB_DeclarationUnit"}]})
        self.value["roots"][0]["type"] = "FB_OuterUnit"
        model = DECL.validate(self.value, self.core)
        self.assertEqual(model.instances[1].path, "StationA.Inner")
        self.assertEqual(model.instances[1].parent_index, 1)
        self.assertEqual(model.instances[5].parent_index, 0)

    def test_duplicate_json_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_bytes(b'{"schema_version":1,"schema_version":2}')
            with self.assertRaises(DECL.DeclarationError):
                DECL.read(path)

    def test_inventory_derives_ordinals_from_authoritative_core(self):
        changed = replace(self.core, tiers={"UNIT": 21, "EQUIPMENT_MODULE": 22, "CONTROL_MODULE": 23})
        model = DECL.validate(self.value, changed)
        self.assertEqual([item["module_type"] for item in model.inventory()["instances"]],
                         [21, 22, 23, 23, 21, 22, 23, 23])

    def test_root_instance_db_cannot_share_a_function_block_name(self):
        self.value["roots"][0]["name"] = "FB_DeclarationUnit"
        self.rejected("T-COLLIDE")


if __name__ == "__main__":
    unittest.main()

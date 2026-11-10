"""Tests for Phase P9: FB_ClampEM, FB_ConfigurableCylinderCM, FB_SeparatorCM.

Validates declaration, generation, contract interfaces, child HAL rollup,
API blocks, sim block, and tia_lint compliance for the core reusable modules.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import tempfile
import unittest

from fraktal_tia_binding import Catalog
import fraktal_tia_declaration as DECL
import fraktal_tia_examples as EX
import fraktal_tia_generate as GEN
import tia_lint

ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = ROOT / "Framework/Modules"
CYLINDER_DIR = MODULES_ROOT / "ControlModules/Cylinder"
CONFIG_CYLINDER_DIR = MODULES_ROOT / "ControlModules/ConfigurableCylinder"
SEPARATOR_DIR = MODULES_ROOT / "ControlModules/Separator"
CLAMP_DIR = MODULES_ROOT / "EquipmentModules/Clamp"


def bind_template(text: str, catalog: Catalog, extra: dict | None = None) -> str:
    for enum, members in catalog.enums.items():
        for name, value in members.items():
            text = text.replace("@" + enum + "." + name + "@", str(value))
    for name, value in (extra or {}).items():
        text = text.replace("@" + name + "@", str(value))
    assert not re.search(r"@[A-Z_a-z][\w.]*@", text), "Unbound template token: " + text
    return text


def load_module_logic(dir_path: Path, stem: str, catalog: Catalog, command_ids: dict) -> dict[str, str]:
    path = dir_path / f"{stem}_logic.scl.in"
    text = bind_template(path.read_text("ascii"), catalog, command_ids)
    pieces = re.split(r"@REGION:(\w+)@\n", text)[1:]
    return dict(zip(pieces[::2], pieces[1::2]))


class ReusableModulesTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog.read()
        self.cylinder_def = json.loads((CYLINDER_DIR / "cylinder.json").read_bytes())
        self.clamp_def = json.loads((CLAMP_DIR / "clamp.json").read_bytes())
        self.config_cyl_def = json.loads((CONFIG_CYLINDER_DIR / "configurable_cylinder.json").read_bytes())
        self.separator_def = json.loads((SEPARATOR_DIR / "separator.json").read_bytes())

    def make_declaration(self) -> dict:
        records: dict[str, str] = {
            "ST_SequenceCommandLease": (
                "STRUCT OwnerIndex : DINT; ChainIndex : DINT; BranchIndex : DINT; "
                "Step : DINT; Raised : BOOL; AbortIssued : BOOL; ReleasedScan : UDINT; END_STRUCT"
            ),
            "ST_BenchUnitParCfg": "STRUCT SchemaVersion : UINT := 1; Timeout : TIME := T#10s; END_STRUCT",
            "ST_BenchUnitParCmd": "STRUCT Reserved : BOOL; END_STRUCT",
            "ST_BenchUnitOutCmd": "STRUCT Done : BOOL; END_STRUCT",
            "ST_BenchUnitOutImm": "STRUCT Ready : BOOL; END_STRUCT",
        }

        # Cylinder CM
        records.update(self.cylinder_def["records"])
        cyl_cmd_ids = {c["label"]: c["id"] for c in self.cylinder_def["commands"]}
        cyl_type = {k: v for k, v in self.cylinder_def.items() if k != "records"}
        cyl_type["logic"] = load_module_logic(CYLINDER_DIR, "cylinder", self.catalog, cyl_cmd_ids)
        cyl_type["children"] = []

        # Configurable Cylinder CM
        records.update(self.config_cyl_def["records"])
        cfg_cmd_ids = {c["label"]: c["id"] for c in self.config_cyl_def["commands"]}
        cfg_cmd_ids.update({
            "CYL_CFG_INVALID": 10115,
            "CYL_HOME_NOT_REACHED": 10111,
            "CYL_WORK_NOT_REACHED": 10112,
            "CYL_POS_IMPLAUSIBLE": 10113,
            "CYL_DISCREPANCY": 10116,
            "CYL_SENSOR_LOST": 10114,
        })
        cfg_type = {k: v for k, v in self.config_cyl_def.items() if k != "records"}
        cfg_type["logic"] = load_module_logic(CONFIG_CYLINDER_DIR, "configurable_cylinder", self.catalog, cfg_cmd_ids)
        cfg_type["children"] = []

        # Separator CM
        records.update(self.separator_def["records"])
        sep_cmd_ids = {c["label"]: c["id"] for c in self.separator_def["commands"]}
        sep_cmd_ids.update({
            "SEP_NO_CARRIER_AT": 10001,
            "SEP_CARRIER_NOT_CLEARED": 10002,
            "SEP_CARRIER_NOT_ARRIVED": 10003,
            "SEP_NOT_OPENED_FB": 10004,
            "SEP_SON_NOT_CLEARED": 10005,
        })
        sep_type = {k: v for k, v in self.separator_def.items() if k != "records"}
        sep_type["logic"] = load_module_logic(SEPARATOR_DIR, "separator", self.catalog, sep_cmd_ids)
        sep_type["children"] = []

        # Clamp EM (Equipment Module)
        records.update(self.clamp_def["records"])
        clamp_cmd_ids = {c["label"]: c["id"] for c in self.clamp_def["commands"]}
        clamp_cmd_ids.update({"CLAMP_NOT_CONFIRMED": 11001})
        clamp_type = {k: v for k, v in self.clamp_def.items() if k != "records"}
        clamp_type["logic"] = load_module_logic(CLAMP_DIR, "clamp", self.catalog, clamp_cmd_ids)

        # Root Unit containing ClampEM, ConfigurableCylinderCM, and SeparatorCM
        unit_type = {
            "name": "FB_BenchUnit",
            "tier": "UNIT",
            "type_key": "bench.reusableModulesUnit",
            "children": [
                {"name": "Clamp", "type": "FB_ClampEM"},
                {"name": "ConfigCyl", "type": "FB_ConfigurableCylinderCM"},
                {"name": "Separator", "type": "FB_SeparatorCM"},
            ],
            "contract": {
                "ParCfg": "ST_BenchUnitParCfg",
                "ParCmd": "ST_BenchUnitParCmd",
                "OutCmd": "ST_BenchUnitOutCmd",
                "OutImm": "ST_BenchUnitOutImm",
            },
            "commands": [{"id": 1, "label": "Run"}],
            "timeout": "Timeout",
            "unit": {
                "modes": ["AUTO", "MANUAL"],
                "initial": "MANUAL",
                "run_command": 1,
            },
            "logic": {
                "cyclic": "    #OutImm.Ready := TRUE;",
            },
        }

        return {
            "schema_version": 1,
            "target_family": "S7-1500",
            "registry_capacity": 16,
            "types": [unit_type, clamp_type, cfg_type, sep_type, cyl_type],
            "roots": [{"name": "BenchUnit", "type": "FB_BenchUnit"}],
            "records": records,
        }

    def test_declaration_validation_passes(self):
        decl = self.make_declaration()
        validated = DECL.validate(decl)
        self.assertEqual(len(validated.types), 5)
        self.assertEqual(validated.types[1].name, "FB_ClampEM")
        self.assertEqual(validated.types[1].tier, "EQUIPMENT_MODULE")
        self.assertEqual(validated.types[2].name, "FB_ConfigurableCylinderCM")
        self.assertEqual(validated.types[2].tier, "CONTROL_MODULE")
        self.assertEqual(validated.types[3].name, "FB_SeparatorCM")
        self.assertEqual(validated.types[3].tier, "CONTROL_MODULE")

    def test_generation_and_lint_pass_with_zero_findings(self):
        decl = self.make_declaration()
        validated = DECL.validate(decl)

        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "sources"
            GEN.generate(validated, out, shared_runtime=True)

            # Generate API blocks
            clamp_cmd_ids = {c["label"]: c["id"] for c in self.clamp_def["commands"]}
            (out / "22_ClampApi.scl").write_text(
                bind_template((CLAMP_DIR / "clamp_api.scl.in").read_text("ascii"), self.catalog, clamp_cmd_ids),
                encoding="ascii",
            )

            cfg_cmd_ids = {c["label"]: c["id"] for c in self.config_cyl_def["commands"]}
            (out / "22_ConfigurableCylinderApi.scl").write_text(
                bind_template(
                    (CONFIG_CYLINDER_DIR / "configurable_cylinder_api.scl.in").read_text("ascii"),
                    self.catalog,
                    cfg_cmd_ids,
                ),
                encoding="ascii",
            )
            (out / "38_ConfigurableCylinderSim.scl").write_text(
                (CONFIG_CYLINDER_DIR / "configurable_cylinder_sim.scl.in").read_text("ascii"),
                encoding="ascii",
            )

            sep_cmd_ids = {c["label"]: c["id"] for c in self.separator_def["commands"]}
            (out / "22_SeparatorApi.scl").write_text(
                bind_template((SEPARATOR_DIR / "separator_api.scl.in").read_text("ascii"), self.catalog, sep_cmd_ids),
                encoding="ascii",
            )

            findings = tia_lint.lint([out])
            # Only ignore T-GEN manifest verification finding caused by adding API files after GEN.generate
            non_gen_findings = [f for f in findings if f.rule != "T-GEN"]
            self.assertEqual(non_gen_findings, [])

            # Check FB_ClampEM block structure
            blocks = [b for p in out.glob("*.scl") for b in tia_lint.parse_blocks(p.read_text())]
            clamp_fb = next(b for b in blocks if b.name == "FB_ClampEM")
            roles = {d.name: d.section for d in clamp_fb.decls}
            self.assertEqual(roles["ParCfg"], "VAR_INPUT")
            self.assertEqual(roles["ParCmd"], "VAR_INPUT")
            self.assertEqual(roles["OutCmd"], "VAR_OUTPUT")
            self.assertEqual(roles["OutImm"], "VAR_OUTPUT")
            self.assertEqual(roles["Hal"], "VAR_IN_OUT")
            self.assertEqual(roles["CylA"], "VAR")
            self.assertEqual(roles["CylB"], "VAR")

            # Check FB_ConfigurableCylinderCM block structure
            cfg_fb = next(b for b in blocks if b.name == "FB_ConfigurableCylinderCM")
            cfg_roles = {d.name: d.section for d in cfg_fb.decls}
            self.assertEqual(cfg_roles["ParCfg"], "VAR_INPUT")
            self.assertEqual(cfg_roles["Hal"], "VAR_IN_OUT")

            # Check FB_SeparatorCM block structure
            sep_fb = next(b for b in blocks if b.name == "FB_SeparatorCM")
            sep_roles = {d.name: d.section for d in sep_fb.decls}
            self.assertEqual(sep_roles["ParCfg"], "VAR_INPUT")
            self.assertEqual(sep_roles["Hal"], "VAR_IN_OUT")

    def test_derived_clamp_hal_bundle_includes_both_child_cylinders(self):
        decl = self.make_declaration()
        _, manifest = GEN.build(DECL.validate(decl), shared_runtime=True)
        clamp_hal = manifest["types"]["ST_ClampEMHal"]
        members = [(f["member"], f["native_type"]) for f in clamp_hal]
        self.assertEqual(members, [("CylA", '"ST_CylinderHal"'), ("CylB", '"ST_CylinderHal"')])


if __name__ == "__main__":
    unittest.main()

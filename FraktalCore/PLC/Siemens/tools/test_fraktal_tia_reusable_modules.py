"""Tests for Phase P9: FB_ClampEM, FB_ConfigurableCylinderCM, FB_SeparatorCM.

Validates declaration, generation, contract interfaces, child HAL rollup,
API blocks, sim block, and tia_lint compliance for the core reusable modules.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from fraktal_tia_binding import Catalog
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import tia_lint

ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = ROOT / "Framework/Modules"
CYLINDER_DIR = MODULES_ROOT / "ControlModules/Cylinder"
CONFIG_CYLINDER_DIR = MODULES_ROOT / "ControlModules/ConfigurableCylinder"
SEPARATOR_DIR = MODULES_ROOT / "ControlModules/Separator"
CLAMP_DIR = MODULES_ROOT / "EquipmentModules/Clamp"


def _fixture():
    spec = importlib.util.spec_from_file_location("reusable_modules_fixture", ROOT / "Tests/ReusableModules/make_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _fixture()


class ReusableModulesTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog.read()
        self.cylinder_def = json.loads((CYLINDER_DIR / "cylinder.json").read_bytes())
        self.clamp_def = json.loads((CLAMP_DIR / "clamp.json").read_bytes())
        self.config_cyl_def = json.loads((CONFIG_CYLINDER_DIR / "configurable_cylinder.json").read_bytes())
        self.separator_def = json.loads((SEPARATOR_DIR / "separator.json").read_bytes())

    def make_declaration(self) -> dict:
        # One source: the native compile fixture's declaration, whose band
        # reasons bind from the TC3 module reason list rather than literals.
        return FIXTURE.declaration(self.catalog)

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
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "sources"
            out.mkdir()
            sources, _ = FIXTURE.build()
            for name, text in sources.items():
                (out / name).write_bytes(text.encode("ascii"))
            self.assertEqual(tia_lint.lint([out]), [])

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

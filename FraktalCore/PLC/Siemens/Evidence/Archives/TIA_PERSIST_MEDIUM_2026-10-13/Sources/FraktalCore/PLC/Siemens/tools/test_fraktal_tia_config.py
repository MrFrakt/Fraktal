"""Config authority, typed schema bounds and generated transaction boundaries."""
import copy
import importlib.util
import unittest
import os
import subprocess
import sys

from fraktal_tia_binding import Catalog, REPO
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN

spec = importlib.util.spec_from_file_location('config_fixture', REPO / 'FraktalCore/PLC/Siemens/Tests/Config/make_fixture.py')
FIX = importlib.util.module_from_spec(spec); spec.loader.exec_module(FIX)


class ConfigTests(unittest.TestCase):
    def test_generation_is_independent_of_python_hash_seed(self):
        script = "import importlib.util,hashlib,json;import fraktal_tia_generate as g;from fraktal_tia_binding import REPO;s=importlib.util.spec_from_file_location('fixture',REPO/'FraktalCore/PLC/Siemens/Tests/Config/make_fixture.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);v,_=g.build(g.DECL.validate(m.declaration()),True);print(json.dumps({k:hashlib.sha256(b.encode('ascii')).hexdigest() for k,b in v.items()},sort_keys=True))"
        outputs = []
        for seed in ('1', '2'):
            environment = dict(os.environ, PYTHONHASHSEED=seed)
            outputs.append(subprocess.check_output([sys.executable, '-c', script], cwd=REPO/'FraktalCore/PLC/Siemens/tools', env=environment))
        self.assertEqual(outputs[0], outputs[1])
    def build(self, value=None):
        return GEN.build(DECL.validate(value or FIX.declaration()), True)

    def test_model_records_must_be_complete_before_the_provider_is_offered(self):
        value = FIX.declaration(); value['types'][0]['config'].pop(0)
        with self.assertRaises(DECL.DeclarationError): self.build(value)

    def test_schema_targets_and_duplicate_keys_cannot_register(self):
        for change in ('schema', 'duplicate', 'zero_revision', 'wrong_member'):
            value = FIX.declaration(); field = value['types'][0]['config'][0]
            if change == 'schema': field['member'] = 'ParCfg.SchemaVersion'
            elif change == 'duplicate': value['types'][0]['config'].append(copy.deepcopy(field))
            elif change == 'zero_revision': field['revision'] = 0
            else: field['member'] = 'StationData.Missing'
            with self.subTest(change=change), self.assertRaises(DECL.DeclarationError): self.build(value)

    def test_native_storage_bounds_and_lossless_record_width_are_enforced(self):
        for change in ('integer_range', 'text_width', 'schema_order', 'unsupported_float'):
            value = FIX.declaration()
            if change == 'integer_range': value['types'][0]['config'][1]['maximum'] = 4294967296
            elif change == 'text_width': value['records']['ST_UnitProbeStationCfg'] = value['records']['ST_UnitProbeStationCfg'].replace('STRING(80)', 'STRING(81)')
            elif change == 'schema_order': value['records']['ST_DeclarationParCfg'] = 'STRUCT Timeout : TIME; SchemaVersion : UINT := 4; Preset : DINT; END_STRUCT'
            else: value['records']['ST_DeclarationParCfg'] = value['records']['ST_DeclarationParCfg'].replace('Preset : DINT', 'Preset : LREAL')
            with self.subTest(change=change), self.assertRaises(DECL.DeclarationError): self.build(value)

    def test_project_code_cannot_write_config_or_invoke_its_assembly(self):
        for body in ('#ParCfg.Preset := 1;', '#StationCfg.Enabled := TRUE;', '#ConfigStageParCfg.Preset := 1;',
                     '#ModelId.ModelCode := \'fake\';', '"FRK_CfgRecipe_DeclarationUnit"(Phase := 2);'):
            value = FIX.declaration(); value['types'][0]['logic']['Cyclic'] = body
            with self.subTest(body=body), self.assertRaises(DECL.DeclarationError): self.build(value)

    def test_editable_par_cfg_is_owned_static_and_restore_precedes_init(self):
        sources, manifest = self.build()
        root = next(v for k,v in sources.items() if k.endswith('FB_DeclarationUnit.scl'))
        block = next(b for b in __import__('tia_lint').parse_blocks(root) if b.kind == 'FUNCTION_BLOCK')
        par_cfg = next(d for d in block.decls if d.name == 'ParCfg')
        self.assertEqual(par_cfg.section, 'VAR')
        self.assertLess(root.index('"FRK_CfgRestore_DeclarationUnit"('), root.index('"FRK_Begin"('))
        self.assertNotIn('#THIS', root)
        self.assertIn('VAR RETAIN', sources['05_FRK_ConfigStore.db'])
        self.assertIn('"ST_ConfigRecord"', sources['02_FRK_ConfigSlot.udt'])
        self.assertIn('Framework/Core/config_services.scl.in', '\n'.join(manifest['runtime']['authority_inputs']))

    def test_station_and_model_restore_are_separate_and_commit_does_no_io(self):
        sources, _ = self.build()
        root = next(v for k,v in sources.items() if k.endswith('FB_DeclarationUnit.scl'))
        restore = root[root.index('FUNCTION "FRK_CfgRestore_DeclarationUnit"'):root.index('FUNCTION "FRK_Config_DeclarationUnit"')]
        self.assertEqual(restore.count('#Ok := TRUE;'), 2)
        recipe = root[root.index('FUNCTION "FRK_CfgRecipe_DeclarationUnit"'):root.index('FUNCTION "FRK_CfgOperation_DeclarationUnit"')]
        commit = recipe[recipe.index('ELSIF #Phase = 2 THEN'):recipe.index('ELSE #ConfigStaged')]
        self.assertIn('#ParCfg := #ConfigStageParCfg;', commit)
        self.assertNotIn('ConfigGet', commit)
        self.assertNotIn('ConfigDecode', commit)
        self.assertNotIn('StationCfg :=', recipe)


if __name__ == '__main__': unittest.main()

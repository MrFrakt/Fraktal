"""Declaration replay, interface authority and frame boundaries before TIA."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from fraktal_tia_binding import Catalog, literal
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import tia_lint

FIXTURE = Path(__file__).resolve().parents[1] / 'Tests/Declaration/two_root_forest.json'


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(FIXTURE.read_text())

    def build(self):
        return GEN.build(DECL.validate(self.value))

    def test_repeat_generation_and_authoritative_widths_initializers(self):
        first, manifest = self.build()
        self.assertEqual(first, self.build()[0])
        status = manifest['types']['ST_ModuleStatus']
        self.assertEqual(next(f['native_type'] for f in status if f['member'] == 'TypeKey'), 'String[160]')
        self.assertEqual(next(f['initial'] for f in status if f['member'] == 'TileEnable'), 'TRUE')
        self.assertEqual(next(f['native_type'] for f in manifest['types']['ST_Diagnostic'] if f['member'] == 'Since'), 'LDT')
        self.assertEqual(next(f['native_type'] for f in manifest['types']['ST_Diagnostic'] if f['member'] == 'SourcePath'), 'WString[255]')

    def test_derived_hal_bundles_follow_reused_child_types(self):
        _, manifest = self.build()
        fields = manifest['types']['ST_DeclarationCellHal']
        self.assertEqual([(f['member'], f['native_type']) for f in fields],
                         [('Clamp', '"ST_DeclarationLeafHal"'), ('Gate', '"ST_DeclarationLeafHal"')])
        self.assertEqual(len(manifest['inventory']['instances']), 8)

    def test_generated_contract_classes_children_and_cyclic_guard_pass_lint(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'sources'
            GEN.generate(DECL.validate(self.value), out)
            self.assertEqual(tia_lint.lint([out]), [])
            blocks = [b for p in out.glob('*.scl') for b in tia_lint.parse_blocks(p.read_text())]
            cm = next(b for b in blocks if b.name == 'FB_DeclarationCylinder')
            roles = {d.name: d.section for d in cm.decls}
            for name in ('ParCfg', 'ParCmd'): self.assertEqual(roles[name], 'VAR_INPUT')
            for name in ('OutCmd', 'OutImm', 'Held', 'Timing'): self.assertEqual(roles[name], 'VAR_OUTPUT')
            self.assertEqual(roles['Hal'], 'VAR_IN_OUT')
            self.assertEqual(roles['Status'], 'VAR')
            self.assertEqual(roles['Core'], 'VAR')

    def test_mutated_source_is_rejected_even_if_manifest_hash_is_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'sources'
            manifest = GEN.generate(DECL.validate(self.value), out)
            path = next(out.glob('*FB_DeclarationCell.scl'))
            payload = path.read_bytes().replace(b'#Gate(', b'#Clamp(')
            path.write_bytes(payload)
            manifest['generated'][path.name] = hashlib.sha256(payload).hexdigest()
            (out / 'manifest.json').write_bytes(json.dumps(manifest).encode('ascii'))
            with self.assertRaises(DECL.DeclarationError): GEN.verify(out)
            self.assertIn('T-GEN', {f.rule for f in tia_lint.lint([out])})

    def test_deleted_and_extra_generated_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'sources'
            GEN.generate(DECL.validate(self.value), out)
            path = next(out.glob('*.db')); data = path.read_bytes(); path.unlink()
            with self.assertRaises(DECL.DeclarationError): GEN.verify(out)
            path.write_bytes(data); (out / 'extra.db').write_bytes(data)
            with self.assertRaises(DECL.DeclarationError): GEN.verify(out)

    def test_schema_version_is_first_uint(self):
        self.value['records']['ST_DeclarationParCfg'] = 'STRUCT Value : DINT; SchemaVersion : UINT; END_STRUCT'
        with self.assertRaises(DECL.DeclarationError): self.build()

    def test_missing_contract_hal_and_unresolved_record_fail_before_output(self):
        for field in ('contract', 'hal'):
            value = copy.deepcopy(self.value); value['types'][2].pop(field)
            with tempfile.TemporaryDirectory() as directory:
                out = Path(directory) / 'sources'
                with self.assertRaises(DECL.DeclarationError): GEN.generate(DECL.validate(value), out)
                self.assertFalse(out.exists())
        self.value['types'][2]['hal'] = 'ST_Absent'
        with self.assertRaises(ValueError): self.build()

    def test_application_cannot_replace_core_or_derived_bundle(self):
        for name in ('ST_ModuleStatus', 'ST_DeclarationCellHal', 'ST_FraktalHal'):
            value = copy.deepcopy(self.value); value['records'][name] = 'STRUCT Value : DINT; END_STRUCT'
            with self.assertRaises(ValueError): GEN.build(DECL.validate(value))

    def test_raw_io_early_return_and_lifecycle_write_are_refused(self):
        for body in ('#OutImm.Sample := %ID0;', 'RETURN;', '#Core.Exec := 3;',
                     '#Core := #Core;', '#Cell.Core.Exec := 3;', '// ---- GENERATED: escape\n#Core.Exec := 3;'):
            self.value['types'][2]['logic']['cyclic'] = body
            with self.assertRaises(DECL.DeclarationError): self.build()

    def test_composite_hal_and_mode_hooks_are_tier_checked(self):
        self.value['types'][0]['hal'] = 'ST_DeclarationLeafHal'
        with self.assertRaises(DECL.DeclarationError): DECL.validate(self.value)
        self.value = json.loads(FIXTURE.read_text())
        self.value['types'][2]['logic']['ModeExit'] = '#Core.HookResult := 1;'
        with self.assertRaises(DECL.DeclarationError): DECL.validate(self.value)

    def test_string_escaping_preserves_dollar_and_apostrophe(self):
        self.assertEqual(literal("A$'B"), "'A$$$'B'")

    def test_entrypoint_is_owned_and_empty_optional_regions_are_omitted(self):
        self.value['types'][2]['logic']['dispatch'] = '// TODO'
        self.value['types'][2]['logic']['CommandStart'] = ''
        sources,_ = self.build()
        self.assertIn('"GDB_FraktalMain"(Startup := #Initial_Call);',sources['40_Main.scl'])
        cm=next(value for name,value in sources.items() if 'FB_DeclarationCylinder.scl' in name)
        self.assertNotIn('IF #Core.Dispatch',cm)
        self.assertNotIn('// ---- AUTHORED: CommandStart',cm)
        self.assertIn('#LatchedParCmd := #ParCmd;',cm)

    def test_kernel_assembly_cannot_be_reentered_or_command_storage_changed(self):
        for body in ('"FRK_RouteAbort"(Core := #Core, Abort := FALSE);',
                     '#LatchedParCmd.Value := 2;', '#Core.TimeoutMs := 99;'):
            self.value['types'][2]['logic']['dispatch'] = body
            with self.assertRaises(DECL.DeclarationError): self.build()

    def test_command_catalog_and_timeout_are_validated(self):
        cm = self.value['types'][2]
        cm['commands'] = [{'id': 3, 'label': 'Move'}]
        cm['timeout'] = 'Timeout'
        with self.assertRaises(DECL.DeclarationError): self.build()
        self.value['records']['ST_DeclarationParCfg'] = 'STRUCT SchemaVersion : UINT := 1; Timeout : TIME := T#1s; END_STRUCT'
        sources, _ = self.build()
        text = next(v for k,v in sources.items() if k.endswith('FB_DeclarationCylinder.scl'))
        self.assertIn('3: "FRK_Start"', text)
        cm['commands'].append({'id': 3, 'label': 'Duplicate'})
        with self.assertRaises(DECL.DeclarationError): self.build()

    def test_management_hook_runs_before_abort_and_prevents_idle_skip(self):
        self.value['types'][2]['logic']['Cyclic'] = '#OutImm.Sample := #Hal.Sample;'
        sources, _ = self.build()
        text = next(v for k,v in sources.items() if k.endswith('FB_DeclarationCylinder.scl'))
        self.assertNotIn(tia_lint.QUIET_GUARD, text)
        self.assertLess(text.index('// ---- AUTHORED: cyclic management'),text.index('"FRK_RouteAbort"'))

    def test_value_type_cycle_and_reversed_array_are_refused(self):
        for text in ('STRUCT Sample : ST_DeclarationLeafHal; END_STRUCT', 'STRUCT Sample : ARRAY[2..1] OF DINT; END_STRUCT'):
            self.value['records']['ST_DeclarationLeafHal'] = text
            with self.assertRaises(ValueError): self.build()


if __name__ == '__main__':
    unittest.main()

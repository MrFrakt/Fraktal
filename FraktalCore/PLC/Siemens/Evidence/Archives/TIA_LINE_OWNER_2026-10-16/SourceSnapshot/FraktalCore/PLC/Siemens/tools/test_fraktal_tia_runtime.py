"""Kernel ownership and dependency replay; behavioral proof runs inside the PLC."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import fraktal_tia_runtime as RUNTIME

spec = importlib.util.spec_from_file_location('lifecycle_fixture', Path(__file__).resolve().parents[1] / 'Tests/Lifecycle/make_fixture.py')
FIXTURE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FIXTURE)


class RuntimeTests(unittest.TestCase):
    def test_compile_gate_checks_software_and_hardware_instead_of_last_result(self):
        path = Path(__file__).resolve().parents[1] / 'Spikes/S12_TypeMap/run_plan.py'
        spec = importlib.util.spec_from_file_location('runtime_plan', path)
        plan = importlib.util.module_from_spec(spec); spec.loader.exec_module(plan)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'compile.jsonl'
            warning = {'event': 'compile', 'errors': 0, 'warnings': 9}
            success = {'event': 'compile', 'errors': 0, 'warnings': 0}
            log.write_bytes((json.dumps(warning)+'\n'+json.dumps(success)+'\n').encode('ascii'))
            with self.assertRaises(ValueError): plan.require_clean_compile(log)
            log.write_bytes((json.dumps(success)+'\n'+json.dumps(success)+'\n').encode('ascii'))
            self.assertEqual(plan.require_clean_compile(log), 2)
            log.write_bytes(b'{"event":"plan-complete"}\n')
            with self.assertRaises(ValueError): plan.require_clean_compile(log)

    def test_kernel_uses_core_enum_capacity_and_rationalization_authorities(self):
        sources, metadata = RUNTIME.build()
        self.assertNotIn('@', sources['12_CommandKernel.scl'])
        self.assertIn('Specification/reason_rationalization.json', metadata['authority_inputs'])
        self.assertEqual(sources, RUNTIME.build()[0])

    def test_runtime_frame_replay_rejects_changed_kernel_even_with_rehashed_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'sources'
            manifest = GEN.generate(DECL.validate(FIXTURE.declaration()), out, shared_runtime=True)
            self.assertEqual(GEN.verify(out), len(manifest['generated']))
            path = out / '12_CommandKernel.scl'
            data = path.read_bytes().replace(b'#Core.Armed := FALSE;', b'#Core.Armed := TRUE;', 1)
            path.write_bytes(data)
            manifest['generated'][path.name] = hashlib.sha256(data).hexdigest()
            (out / 'manifest.json').write_bytes(json.dumps(manifest).encode('ascii'))
            with self.assertRaises(DECL.DeclarationError): GEN.verify(out)

    def test_runtime_generation_requires_timeout_and_catalog_for_every_type(self):
        value = FIXTURE.declaration()
        value['types'][0].pop('commands'); value['types'][0].pop('timeout')
        with self.assertRaises(DECL.DeclarationError): GEN.build(DECL.validate(value), shared_runtime=True)

    def test_passive_control_module_rejects_every_request(self):
        value = FIXTURE.declaration()
        cm = next(t for t in value['types'] if t['tier'] == 'CONTROL_MODULE')
        cm.pop('commands'); cm.pop('timeout')
        cm['logic'] = {k: v for k, v in cm.get('logic', {}).items() if k in ('cyclic', 'Cyclic')}
        sources, _ = GEN.build(DECL.validate(value), shared_runtime=True)
        frame = next(t for n, t in sources.items() if 'FUNCTION_BLOCK "%s"' % cm['name'] in t)
        start = frame.index('IF #Core.EvCommandStart THEN')
        block = frame[start:frame.index('END_IF;', start)]
        self.assertIn('"FRK_Start"(Core := #Core, Status := #Status, Supported := FALSE', block)
        self.assertNotIn('CASE #Core.Command OF', block)

    def test_root_idb_cannot_collide_with_shared_clock_storage(self):
        value = FIXTURE.declaration()
        value['roots'][0]['name'] = 'FRK_Clock'
        with self.assertRaises(DECL.DeclarationError): GEN.build(DECL.validate(value), shared_runtime=True)

    def test_private_device_state_does_not_read_published_outputs(self):
        sources, _ = GEN.build(DECL.validate(FIXTURE.declaration()), shared_runtime=True)
        frame = next(v for k,v in sources.items() if k.endswith('FB_DeclarationCylinder.scl'))
        self.assertIn('Device {ExternalAccessible', frame)
        self.assertIn('#OutImm := #Device;', frame)
        self.assertNotIn(':= #OutImm', frame)
        value = FIXTURE.declaration(); value['types'][2]['storage'] = 'ST_Missing'
        with self.assertRaises(ValueError): GEN.build(DECL.validate(value), shared_runtime=True)
        value = FIXTURE.declaration(); value['types'][2]['logic']['Cyclic'] = '#OutImm.InitCount := #OutImm.InitCount + 1;'
        with self.assertRaises(DECL.DeclarationError): GEN.build(DECL.validate(value), shared_runtime=True)

    def test_test_package_contains_actual_kernel_and_bounded_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            FIXTURE.prepare(root / 'test', root / 'frames')
            self.assertEqual(GEN.verify(root / 'frames'), 27)
            self.assertEqual((root / 'frames/12_CommandKernel.scl').read_bytes(), (root / 'test/12_CommandKernel.scl').read_bytes())
            manifest = json.loads((root / 'test/test_manifest.json').read_text())
            self.assertGreater(manifest['checks'], 200)
            self.assertEqual(manifest['cases'], 55)


if __name__ == '__main__': unittest.main()

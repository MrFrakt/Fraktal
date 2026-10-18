import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_native_alarm_probe as probe
import fraktal_ab_native_alarm_gate as gate
from test_fraktal_ab_generate import SEED_38


class NativeAlarmProbes(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.seed = self.root/'seed.L5X'
        self.seed.write_text(SEED_38,encoding='utf-8')
        self.output = self.root/'probes'

    def test_exact_target_inert_inputs_and_native_object_access_are_explicit(self):
        result = probe.generate_all(self.seed,self.output)
        self.assertFalse(result['RuntimeAccepted'])
        self.assertFalse(result['ProductionAlarmOwnerChanged'])
        self.assertEqual(result['SourceSha256'],probe.sha256(self.seed))
        for case in result['Cases']:
            root = ET.parse(case['Output'])
            controller = root.find('Controller')
            self.assertEqual(controller.get('ProcessorType'),'1756-L81E')
            task = root.find('Controller/Tasks/Task')
            self.assertEqual(task.get('DisableUpdateOutputs'),'true')
            self.assertEqual(task.get('Rate'),'10')
            for tag in controller.findall('Tags/Tag'):
                self.assertEqual(tag.get('ExternalAccess'),
                                 'Read/Write' if tag.get('Name') == probe.ALMD else 'Read Only')
            source = '\n'.join(n.text or '' for n in root.findall('.//STContent/Line'))
            self.assertNotIn('TRUE',source)
            self.assertNotIn('FALSE',source)
            self.assertNotIn('SSV(',source)
            self.assertNotIn('Local:',source)

    def test_positive_and_real_compiler_negative_are_both_generated(self):
        result = probe.generate_all(self.seed,self.output)
        self.assertEqual({r['Case']:r['ExpectedBuild'] for r in result['Cases']},
                         {'almd_st':'pass','invalid_alarm_attribute':'fail'})
        self.assertIn('ALMD(', (self.output/'almd_st.L5X').read_text())
        self.assertIn('FRK_NotAnAttribute',(self.output/'invalid_alarm_attribute.L5X').read_text())

    def test_existing_evidence_and_seed_are_never_modified(self):
        original = self.seed.read_bytes()
        result = probe.generate_all(self.seed,self.output)
        snapshots = {Path(r['Output']):Path(r['Output']).read_bytes() for r in result['Cases']}
        with self.assertRaisesRegex(ValueError,'new'):
            probe.generate_all(self.seed,self.output)
        self.assertEqual(self.seed.read_bytes(),original)
        self.assertTrue(all(path.read_bytes()==value for path,value in snapshots.items()))

    def test_invalid_target_cannot_leave_a_partially_generated_directory(self):
        self.seed.write_text(SEED_38.replace('1756-L81E','5069-L310ER'),encoding='utf-8')
        with self.assertRaises(ValueError):
            probe.generate_all(self.seed,self.output)
        self.assertFalse(self.output.exists())

    def test_alarm_gate_reuses_shared_validation_and_cannot_report_a_failed_run_as_success(self):
        report = probe.generate_all(self.seed,self.output)
        generation = self.output/'generation.json'
        for accepted in (True,False):
            with patch.object(gate,'compile_cases',return_value={'ConformsToExpectations':accepted}) as call:
                self.assertEqual(gate.main([str(generation),str(self.root/'compiled')]),0 if accepted else 1)
                self.assertEqual(call.call_args.args[0],report)
                self.assertEqual(call.call_args.kwargs,dict(expected_schema=probe.SCHEMA,
                                                            expected_profile=probe.PROFILE.key))


if __name__ == '__main__':
    unittest.main()

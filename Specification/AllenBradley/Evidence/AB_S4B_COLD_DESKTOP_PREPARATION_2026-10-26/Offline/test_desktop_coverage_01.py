from pathlib import Path
from copy import deepcopy
import importlib.util
import json
import unittest

W=Path(__file__).parent
spec=importlib.util.spec_from_file_location('desktop_coverage',W/'desktop_coverage_template.py')
coverage=importlib.util.module_from_spec(spec);spec.loader.exec_module(coverage)
EXPECTED=json.loads(Path('C:/work/fraktal-ab-s4b-20261025/desktop_fixture_06/result.json').read_bytes())
POSITIVE=json.loads((W.parent/'desktop_diagnostic_fixture_02/result.json').read_bytes())
BAD=json.loads(Path('C:/work/fraktal-ab-s4b-20261025/desktop_scan_continue_01/desktop_live/result.json').read_bytes())

class CoverageTests(unittest.TestCase):
    def test_actual_empty_native_success_flag_is_refused(self):
        with self.assertRaises(ValueError):coverage.validate_coverage(BAD,EXPECTED,require_live=True)
    def test_complete_fixture_is_explicitly_fixture_only(self):
        self.assertTrue(coverage.validate_coverage(POSITIVE,EXPECTED,require_live=False))
        with self.assertRaises(ValueError):coverage.validate_coverage(POSITIVE,EXPECTED,require_live=True)
    def test_complete_live_context_and_coverage_is_accepted(self):
        value=dict(POSITIVE,live=True,capturedFixtureOnly=False)
        self.assertTrue(coverage.validate_coverage(value,EXPECTED,require_live=True))
    def test_one_stale_frame_is_refused(self):
        value=deepcopy(POSITIVE);value['shots'][0]['link']='stale'
        with self.assertRaises(ValueError):coverage.validate_coverage(value,EXPECTED,require_live=False)
    def test_missing_module_is_refused(self):
        value=deepcopy(POSITIVE);value['modules'].pop()
        with self.assertRaises(ValueError):coverage.validate_coverage(value,EXPECTED,require_live=False)
    def test_skipped_refusal_loop_is_refused(self):
        value=dict(POSITIVE,refusedActions=0)
        with self.assertRaises(ValueError):coverage.validate_coverage(value,EXPECTED,require_live=False)

if __name__=='__main__':unittest.main()

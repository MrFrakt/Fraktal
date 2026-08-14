import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("fraktal_ab_sdk_log_gate.py")
SPEC = importlib.util.spec_from_file_location("fraktal_ab_sdk_log_gate", MODULE_PATH)
assert SPEC and SPEC.loader
SUBJECT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUBJECT
SPEC.loader.exec_module(SUBJECT)


class SdkLogGateTests(unittest.TestCase):
    def test_clean_import_and_required_operation_pass(self):
        log = """[time][INFO][project] ImportLog <Summary Warnings="0" Errors="0"/>
[time][INFO][project] BuildAsync succeeded
"""
        report = SUBJECT.audit_log(log, ("BuildAsync",), True)
        self.assertTrue(report["Clean"])

    def test_import_warning_fails_even_when_operation_succeeds(self):
        log = """[time][INFO][project] ImportLog <Summary Warnings="1" Errors="0"/>
[time][INFO][project] SaveAsAsync succeeded
"""
        report = SUBJECT.audit_log(log, ("SaveAsAsync",), True)
        self.assertFalse(report["Clean"])
        self.assertTrue(any("non-clean import" in item
                            for item in report["Findings"]))

    def test_sdk_error_and_missing_operation_fail(self):
        log = "[time][ERROR][project] BuildAsync threw\n"
        report = SUBJECT.audit_log(log, ("BuildAsync",), False)
        self.assertFalse(report["Clean"])
        self.assertEqual(report["SdkErrorEventCount"], 1)
        self.assertEqual(report["MissingOperations"], ["BuildAsync"])


if __name__ == "__main__":
    unittest.main()

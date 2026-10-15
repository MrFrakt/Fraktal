import json
import unittest

import plcsim_results as results


def log(values):
    return "\n".join(json.dumps(dict(event="tag", name="SpkResults.T." + key, value=value)) for key, value in values.items())


class ResultValidation(unittest.TestCase):
    def setUp(self):
        self.values = {"Magic": results.RESULT_MAGIC, "Done": True, "RowCount": 1, "Passed": 1, "Failed": 0,
                       "Rows[1].CaseId": 26, "Rows[1].Pass": True, "Rows[1].Expected": 0, "Rows[1].Actual": 0}

    def test_exact_case_set_and_complete_table(self):
        self.assertEqual(results.validate(log(self.values), {26}), [(26, True, 0, 0)])

    def test_unfinished_wrong_runner_corrupt_counters_and_missing_leaf_fail(self):
        for changed in ({"Done": False}, {"Magic": 0}, {"Passed": 0}, {"Rows[1].CaseId": 1}, {"Rows[1].Pass": "true"}):
            with self.assertRaises(ValueError):
                results.validate(log(self.values | changed), {26})
        del self.values["Rows[1].Actual"]
        with self.assertRaises(ValueError):
            results.validate(log(self.values), {26})

    def test_failed_row_is_a_failed_junit(self):
        self.values.update(Passed=0, Failed=1)
        self.values["Rows[1].Pass"] = False
        rows = results.validate(log(self.values), {26})
        self.assertIn(b'failures="1"', results.junit(rows))
        self.assertIn(b"<failure", results.junit(rows))

    def test_case_ranges_are_bounded_and_unique(self):
        self.assertEqual(results.case_set("1-17,29,30"), set(range(1, 18)) | {29, 30})
        for invalid in ("0", "1-999999999", "2-1", "1-3,2"):
            with self.assertRaises(ValueError):
                results.case_set(invalid)

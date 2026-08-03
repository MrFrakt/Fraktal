import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.tcunit_to_junit import parse_runners, parse_summary, write_junit


SAMPLE = """
| Test class name=PRG_TcUnitRunner.BaseTests
| Successful tests: 84
| Duration: 2.722424e-1
| Test suites: 26
| Failed tests: 0
| Tests: 84
"""


class TcUnitSummaryTests(unittest.TestCase):
    def test_parses_summary_independent_of_line_order(self):
        self.assertEqual(
            parse_summary(SAMPLE),
            {
                "successful": 84,
                "failed": 0,
                "tests": 84,
                "suites": 26,
                "duration": 0.2722424,
            },
        )

    def test_missing_summary_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing TcUnit summary"):
            parse_summary("Tests: 8")

    def test_two_summaries_fail_closed_instead_of_taking_the_first(self):
        # A capture window that caught a green run and a later red re-run must
        # not be graded on the green one. Fields are matched independently, so
        # first-hit parsing would report 8 successful / 0 failed and pass.
        green_then_red = SAMPLE + """
| Test class name=PRG_TcUnitRunner.BaseTests
| Successful tests: 82
| Duration: 2.5e-1
| Test suites: 26
| Failed tests: 2
| Tests: 84
"""
        with self.assertRaisesRegex(ValueError, "ambiguous log"):
            parse_summary(green_then_red)

    def test_parses_runner_identity(self):
        self.assertEqual(parse_runners(SAMPLE), {"PRG_TcUnitRunner"})

    def test_missing_runner_identity_is_empty(self):
        self.assertEqual(parse_runners("| Successful tests: 8"), set())

    def test_control_characters_do_not_break_the_junit_artifact(self):
        # XAE event text is raw controller output. ElementTree writes XML-illegal
        # control characters through without complaint, producing a report the CI
        # consumer cannot parse - a gate result that silently says nothing.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.xml"
            write_junit(
                output,
                "Press",
                {"tests": 8, "successful": 8, "failed": 0, "suites": 2, "duration": 0.01},
                [],
                "TcUnit output\x00with NUL\x08and BS\x1fand US\ttab kept\n",
            )
            root = ET.parse(output).getroot()  # must not raise
            system_out = root.find("testcase/system-out").text
            self.assertNotIn("\x00", system_out)
            self.assertNotIn("\x08", system_out)
            self.assertIn("\t", system_out)

    def test_writes_failure_junit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.xml"
            write_junit(output, "Press", None, ["missing result"], "raw")
            root = ET.parse(output).getroot()
            self.assertEqual(root.attrib["failures"], "1")
            self.assertEqual(root.find("testcase/failure").attrib["message"], "missing result")


if __name__ == "__main__":
    unittest.main()

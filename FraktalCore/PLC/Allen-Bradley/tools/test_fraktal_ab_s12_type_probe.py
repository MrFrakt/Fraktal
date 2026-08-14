import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fraktal_ab_s12_type_probe import (
    CANDIDATES,
    MODES,
    TAG,
    generate_all,
    generate_case,
)


SEED = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetType="Controller" TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33">
<DataTypes/>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


def seed(temporary: str) -> Path:
    path = Path(temporary) / "seed.L5X"
    path.write_text(SEED, encoding="utf-8")
    return path


class S12TypeProbeTests(unittest.TestCase):
    def test_every_candidate_emits_both_modes(self):
        with tempfile.TemporaryDirectory() as temporary:
            results = generate_all(seed(temporary), Path(temporary) / "out")
            self.assertEqual(len(results), len(CANDIDATES) * len(MODES))
            cases = {result["Case"] for result in results}
            for candidate in CANDIDATES:
                for mode in MODES:
                    self.assertIn(f"{candidate.key}-{mode}", cases)

    def test_cases_are_well_formed_and_declare_one_probe_tag(self):
        with tempfile.TemporaryDirectory() as temporary:
            generate_all(seed(temporary), Path(temporary) / "out")
            for path in sorted((Path(temporary) / "out").glob("*.L5X")):
                root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
                probes = [
                    tag for tag in root.iter("Tag") if tag.get("Name") == TAG
                ]
                self.assertEqual(len(probes), 1, path.name)

    def test_declare_mode_carries_no_use_statement(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = seed(temporary)
            for candidate in CANDIDATES:
                output = Path(temporary) / f"{candidate.key}_declare.L5X"
                generate_case(source, output, candidate, "declare")
                text = output.read_text(encoding="utf-8")
                # the separation is the whole experiment: a declare case that
                # smuggled in the operation could not distinguish an unknown
                # type from an uncompilable expression
                self.assertNotIn(candidate.use_statement, text)

    def test_use_mode_adds_exactly_the_declared_operation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = seed(temporary)
            for candidate in CANDIDATES:
                output = Path(temporary) / f"{candidate.key}_use.L5X"
                generate_case(source, output, candidate, "use")
                text = output.read_text(encoding="utf-8")
                self.assertIn(candidate.use_statement, text)

    def test_array_candidate_declares_its_dimension(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = seed(temporary)
            candidate = next(item for item in CANDIDATES if item.key == "array")
            output = Path(temporary) / "array.L5X"
            generate_case(source, output, candidate, "declare")
            self.assertIn('Dimensions="10"', output.read_text(encoding="utf-8"))

    def test_user_type_candidate_emits_its_data_type(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = seed(temporary)
            candidate = next(item for item in CANDIDATES if item.key == "udt")
            output = Path(temporary) / "udt.L5X"
            generate_case(source, output, candidate, "declare")
            text = output.read_text(encoding="utf-8")
            self.assertIn('<DataType Name="FRK_T_S12Layout"', text)
            self.assertIn('DataType="FRK_T_S12Layout"', text)

    def test_candidate_keys_are_unique(self):
        keys = [candidate.key for candidate in CANDIDATES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_refuses_overwrite_and_an_unexpected_seed(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = seed(temporary)
            candidate = CANDIDATES[0]
            output = Path(temporary) / "case.L5X"
            generate_case(source, output, candidate, "declare")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                generate_case(source, output, candidate, "declare")

            wrong = Path(temporary) / "wrong.L5X"
            wrong.write_text(SEED.replace("<Tasks/>", ""), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not the expected empty"):
                generate_case(wrong, Path(temporary) / "other.L5X", candidate, "declare")

    def test_unknown_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "mode must be"):
                generate_case(
                    seed(temporary),
                    Path(temporary) / "case.L5X",
                    CANDIDATES[0],
                    "execute",
                )


if __name__ == "__main__":
    unittest.main()

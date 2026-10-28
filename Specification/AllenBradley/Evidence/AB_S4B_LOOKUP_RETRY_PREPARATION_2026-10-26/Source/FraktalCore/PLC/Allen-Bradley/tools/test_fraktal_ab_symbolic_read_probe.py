import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("fraktal_ab_symbolic_read_probe.py")
SPEC = importlib.util.spec_from_file_location("fraktal_ab_symbolic_read_probe", MODULE_PATH)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class SymbolicReadProbeTests(unittest.TestCase):
    def test_scalar_case(self):
        self.assertEqual(
            PROBE._parse_case("scalar=ControllerTag"),
            PROBE.ReadCase("scalar", "ControllerTag"),
        )

    def test_array_case(self):
        self.assertEqual(
            PROBE._parse_case("array=Program:Main.Tag[0],25", array=True),
            PROBE.ReadCase("array", "Program:Main.Tag[0]", 25),
        )

    def test_value_shape_never_contains_value(self):
        self.assertEqual(PROBE._shape([1, 2, 3]), {"kind": "list", "size": 3})
        self.assertEqual(PROBE._shape("secret"), {"kind": "str", "size": 6})


if __name__ == "__main__":
    unittest.main()

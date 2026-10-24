"""S0 canonical-publication probe: generation shape and the generic decoder."""
import re
import struct
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_s0_canonical_measure as measure
import fraktal_ab_s0_canonical_probe as probe


class Generation(unittest.TestCase):
    def test_every_family_is_one_split_case_and_combines(self):
        keys = [family.key for family in probe.FAMILIES]
        self.assertEqual(len(keys), len(set(keys)))
        user_types, statements = probe.case_text(probe.FAMILIES)
        root = ET.fromstring(f"<DataTypes>{user_types}</DataTypes>")
        names = [t.get("Name") for t in root]
        self.assertEqual(names[-1], probe.RECORD, "the record is emitted after its dependencies")
        self.assertEqual(len(names), len(set(names)), "a shared dependency is emitted once")
        members = [m.get("Name") for m in root[-1].iter("Member")]
        self.assertEqual(len(members), len(set(members)))
        self.assertTrue(statements)

    def test_the_probe_is_read_only(self):
        user_types, _ = probe.case_text(probe.FAMILIES)
        record = ET.fromstring(f"<DataTypes>{user_types}</DataTypes>")[-1]
        self.assertEqual({m.get("ExternalAccess") for m in record.iter("Member")}, {"Read Only"})

    def test_string_widths_cover_every_core_width_class(self):
        # TC3 Core widths reach 255, keys 160, set lines 480 (design note D4).
        self.assertTrue({2, 160, 255, 480} <= set(probe.STRING_WIDTHS))

    def test_expected_timestamps_are_the_declared_instant(self):
        self.assertEqual(probe.STAMP_US * 1000 + 789, probe.STAMP_NS)

    def test_lint_stimulus_preserves_signed_64_bit_values(self):
        # Execute the emitted arithmetic independently of its word decomposition.
        # The microsecond vector has bit 31 set in its low word, unlike the ns one.
        for expected in (0, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF,
                         probe.STAMP_US, probe.STAMP_NS, -1, -(1 << 63), (1 << 63) - 1):
            with self.subTest(expected=expected):
                family = probe._from_lint("test", "Stamp", "DT", expected)
                operand = f"{probe.P}.StampRaw"
                value = 0
                for statement in family.statements[:-1]:
                    target, expression = statement.rstrip(";").split(" := ")
                    self.assertEqual(target, operand)
                    expression = expression.replace(operand, "value")
                    self.assertRegex(expression, r"^(?:value|[0-9+* -])+$")
                    for literal in re.findall(r"-?\d+", expression):
                        self.assertTrue(-(1 << 31) <= int(literal) < (1 << 31))
                    value = eval(expression, {"__builtins__": {}}, {"value": value})
                    self.assertTrue(-(1 << 63) <= value < (1 << 63))
                self.assertEqual(value, expected)
                self.assertEqual(family.expected["StampRaw"], expected)


def field(name, info, code, offset, data_type="", struct_handle=None):
    return SimpleNamespace(TagName=name, DataType=data_type,
                           Bytes=struct.pack("<HHI", info, code, offset))


class GenericDecoder(unittest.TestCase):
    """The decoder sees only template rows and raw bytes, as a CIP client would."""

    def test_atomics_bools_arrays_and_unknown_types(self):
        udt = SimpleNamespace(Fields=[
            field("ZZZZZZZZZZB0", 0, 0xC2, 0),          # hidden BOOL host
            field("B0", 0, 0xC1, 0), field("B1", 1, 0xC1, 0), field("B2", 2, 0xC1, 0),
            field("After", 0, 0xC4, 4),
            field("Words", 3, 0xC4 | 0x2000, 8),
            field("Big", 0, 0xC5, 24),
            field("Wide", 0, 0xCB, 32),
            field("Flags", 64, 0xC1 | 0x2000, 40),
            field("Mystery", 0, 0xC0, 48),
        ])
        raw = bytearray(56)
        raw[0] = 0b101
        struct.pack_into("<i", raw, 4, 123456789)
        struct.pack_into("<3i", raw, 8, 10, 0, 14)
        struct.pack_into("<q", raw, 24, 0x0102030405060708)
        struct.pack_into("<d", raw, 32, 3.5)
        struct.pack_into("<2I", raw, 40, 1 | 1 << 5, 1 << 31)
        struct.pack_into("<q", raw, 48, 1_500_000)
        out = measure.decode(bytes(raw), 0, measure.member_table(udt), {}, len(raw))
        self.assertEqual((out["B0"], out["B1"], out["B2"]), (True, False, True))
        self.assertNotIn("ZZZZZZZZZZB0", out)
        self.assertEqual(out["After"], 123456789)
        self.assertEqual(out["Words"], [10, 0, 14])
        self.assertEqual(out["Big"], 0x0102030405060708)
        self.assertEqual(out["Wide"], 3.5)
        self.assertEqual(out["Flags"], [0, 5, 63])
        self.assertEqual(out["Mystery"]["unknownTypeCode"], "0xc0",
                         "an unknown type is reported, never guessed")
        self.assertEqual(out["Mystery"]["asSignedLE"], 1_500_000)

    def test_string_family_is_recognised_by_shape(self):
        text = SimpleNamespace(Type=0x0123, Fields=[field("LEN", 0, 0xC4, 0),
                                                    field("DATA", 8, 0xC2 | 0x2000, 4)])
        record = SimpleNamespace(Fields=[field("Name", 0, 0x8000 | 0x0123, 0)])
        raw = bytearray(12)
        struct.pack_into("<i", raw, 0, 3)
        raw[4:7] = b"A\xc3\xa9"
        out = measure.decode(bytes(raw), 0, measure.member_table(record), {0x0123: text}, len(raw))
        self.assertEqual(out["Name"]["LEN"], 3)
        self.assertEqual(bytes.fromhex(out["Name"]["bytes"]).decode("utf-8"), "Aé")

    def test_a_non_string_structure_decodes_recursively(self):
        child = SimpleNamespace(Type=0x0200, Fields=[
            field("ZZZZZZZZZZFlag", 0, 0xC2, 0), field("Flag", 0, 0xC1, 0),
            field("Value", 0, 0xC4, 4)])
        record = SimpleNamespace(Fields=[field("Kids", 2, 0x8000 | 0x2000 | 0x0200, 0)])
        raw = bytearray(16)
        raw[0] = 1
        struct.pack_into("<i", raw, 4, 7)
        struct.pack_into("<i", raw, 12, -9)
        out = measure.decode(bytes(raw), 0, measure.member_table(record), {0x0200: child}, len(raw))
        self.assertEqual(out["Kids"], [{"Flag": True, "Value": 7}, {"Flag": False, "Value": -9}])


if __name__ == "__main__":
    unittest.main()

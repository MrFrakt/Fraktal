import struct
import unittest

from fraktal_ab_s12_execute import (
    LAYOUT_BYTE_CAPACITY,
    PAIR_BYTE_CAPACITY,
    _arguments,
    _normalize_serial,
    discover_layout,
    discover_stride,
)


class Reply:
    def __init__(self, status: str = "Success", value=None):
        self.Status = status
        self.Value = value


class LayoutController:
    """A controller whose UDT layout is known, so discovery can be checked.

    Members are packed at the offsets given, exactly as a real controller would
    expose them through the copied byte image.
    """

    def __init__(self, layout: dict[str, tuple[int, int, str]], stride: int = 32):
        self.layout = layout
        self.stride = stride
        self.members: dict[str, float | int] = {name: 0 for name in layout}
        self.pair: dict[int, int] = {0: 0, 1: 0}
        self.writes: list[tuple[str, object]] = []

    def _image(self) -> list[int]:
        image = [0] * LAYOUT_BYTE_CAPACITY
        for name, (offset, width, kind) in self.layout.items():
            value = self.members[name]
            if kind == "f":
                raw = struct.pack("<f", float(value))
            elif kind == "d":
                raw = struct.pack("<d", float(value))
            else:
                raw = int(value).to_bytes(width, "little", signed=True)
            for index, byte in enumerate(raw[:width]):
                image[offset + index] = byte
        return image

    def _pair_image(self) -> list[int]:
        image = [0] * PAIR_BYTE_CAPACITY
        count_offset = self.layout["Count"][0]
        for instance, value in self.pair.items():
            base = instance * self.stride + count_offset
            for index, byte in enumerate(int(value).to_bytes(4, "little")):
                image[base + index] = byte
        return image

    def Write(self, tag: str, value):
        self.writes.append((tag, value))
        if tag.startswith("FRK_S12_Layout."):
            self.members[tag.split(".", 1)[1]] = value
        elif tag.startswith("FRK_S12_LayoutPair["):
            index = int(tag.split("[", 1)[1].split("]", 1)[0])
            self.pair[index] = value
        return Reply()

    def Read(self, tag: str, count: int | None = None):
        # a structured read returns the raw CIP payload, which is what the
        # probe measures and what the gateway will decode
        if tag == "FRK_S12_Layout":
            return Reply(value=bytes(self._image()))
        if tag == "FRK_S12_LayoutPair":
            return Reply(value=bytes(self._pair_image()))
        return Reply(status="Path segment error")


# Offsets deliberately include padding before the 8-byte member and a gap
# before Ratio: dense packing is the assumption a generator would get wrong.
# LREAL is absent because the pinned v33 target rejects it outright.
LAYOUT = {
    "Flag": (0, 1, "i"),
    "Small": (1, 1, "i"),
    "Medium": (2, 2, "i"),
    "Count": (4, 4, "i"),
    "Wide": (8, 8, "i"),
    "Ratio": (20, 4, "f"),
}


class S12ExecutionArgumentTests(unittest.TestCase):
    def test_serial_is_normalized(self):
        self.assertEqual(_normalize_serial("0x7036b510"), "7036B510")

    def test_arm_flag_is_required(self):
        with self.assertRaises(SystemExit):
            _arguments(["192.0.2.1", "--expect-serial", "7036B510"])

    def test_no_arbitrary_tag_or_value_arguments(self):
        with self.assertRaises(SystemExit):
            _arguments([
                "192.0.2.1", "--expect-serial", "7036B510",
                "--execute-fixture", "--tag", "Arbitrary",
            ])


class S12LayoutDiscoveryTests(unittest.TestCase):
    def test_every_member_is_located_at_its_true_offset(self):
        controller = LayoutController(LAYOUT)
        result = discover_layout(controller, settle=0.0)
        self.assertTrue(result["measured"])
        for name, (offset, _width, _kind) in LAYOUT.items():
            with self.subTest(member=name):
                self.assertTrue(result["members"][name]["located"])
                self.assertEqual(result["members"][name]["offset"], offset)

    def test_a_one_byte_member_is_not_confused_with_a_colliding_byte(self):
        # Flag=1 and Wide=0x..08..01 both contain byte 0x01, which is exactly
        # what defeats a pattern search; the differential method must not care
        controller = LayoutController(LAYOUT)
        result = discover_layout(controller, settle=0.0)
        self.assertEqual(result["members"]["Flag"]["offset"], 0)
        self.assertEqual(result["members"]["Flag"]["width"], 1)

    def test_discovery_leaves_every_member_zeroed(self):
        controller = LayoutController(LAYOUT)
        discover_layout(controller, settle=0.0)
        self.assertEqual(set(controller.members.values()), {0, 0.0})

    def test_padded_stride_is_measured_from_two_instances(self):
        controller = LayoutController(LAYOUT, stride=32)
        result = discover_stride(controller, settle=0.0)
        self.assertTrue(result["measured"])
        self.assertEqual(result["strideBytes"], 32)

    def test_stride_measurement_restores_both_instances(self):
        controller = LayoutController(LAYOUT, stride=32)
        discover_stride(controller, settle=0.0)
        self.assertEqual(controller.pair, {0: 0, 1: 0})

    def test_unreadable_image_is_reported_not_guessed(self):
        class Blind(LayoutController):
            def Read(self, tag, count=None):
                return Reply(status="Path segment error")

        result = discover_layout(Blind(LAYOUT), settle=0.0)
        self.assertFalse(result["measured"])
        self.assertIn("unreadable", result["reason"])


if __name__ == "__main__":
    unittest.main()

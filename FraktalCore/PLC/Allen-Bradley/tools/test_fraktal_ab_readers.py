"""What the gateway and the harnesses read is laid out as the controller lays it.

Every structure is read in ONE request and unpacked against its declared
members. A reader that knows only member NAMES assumes every member is one
DINT. When Phase 5f gave the cylinder its first arrays (command timing), that
reader shifted every member after them - on the bench the gateway refused the
station rather than publish the shifted values. No test had packed a context
the way Logix does and read it back through the real reader, so these do,
for every structure the projection reads.
"""

import struct
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
from fraktal_ab_press_execute import APP


class Reply:
    def __init__(self, value):
        self.Status, self.Value = "Success", value


class Controller:
    """Answers a whole-tag read with the bytes Logix would send: each member
    in declaration order, every DINT little-endian, arrays inline."""

    def __init__(self, layouts):
        self.layouts, self.values = layouts, {}
        for tag, layout in layouts.items():
            counter = iter(range(1, 1 << 20))
            self.values[tag] = {m.name: ([next(counter) * 7 for _ in range(m.dimension)]
                                         if m.dimension else next(counter) * 7)
                                for m in layout}

    def Read(self, tag):
        flat = []
        for member in self.layouts[tag]:
            value = self.values[tag][member.name]
            flat.extend(value if member.dimension else [value])
        return Reply(struct.pack(f"<{len(flat)}i", *flat))


def layouts():
    out = {px.UNIT: gen.unit_context_members(APP)}
    for module in APP.modules:
        out[gen.ctx_tag_for(APP, module.name)] = gen.module_members(module)
    return out


class EveryStructureReadsBackAsItIsLaidOut(unittest.TestCase):
    def test_the_unit(self):
        c = Controller(layouts())
        self.assertEqual(px.read_unit(c), c.values[px.UNIT])

    def test_every_module_including_its_arrays(self):
        c = Controller(layouts())
        for module in APP.modules:
            with self.subTest(module.name):
                self.assertEqual(px.read_module(c, module.name),
                                 c.values[gen.ctx_tag_for(APP, module.name)])

    def test_a_member_after_an_array_is_its_own_value(self):
        """The defect itself: AreaSafe sits after the timing arrays."""
        c = Controller(layouts())
        tag = gen.ctx_tag_for(APP, "Door")
        self.assertEqual(px.read_module(c, "Door")["AreaSafe"],
                         c.values[tag]["AreaSafe"])

    def test_the_layout_structures(self):
        tags = {gen.oee_tag(APP): gen.oee_members(),
                gen.profiler_tag(APP): gen.profiler_members(APP),
                gen.alarm_active_tag(APP): gen.alarm_active_members(),
                gen.alarm_ring_tag(APP): gen.alarm_ring_members(),
                px.CHART: gen.chart_members(APP)}
        c = Controller(tags)
        for tag, layout in tags.items():
            with self.subTest(tag):
                self.assertEqual(px.read_layout(c, tag, layout), c.values[tag])


class AFlatReadIsOnlyForScalars(unittest.TestCase):
    def test_what_is_still_read_flat_has_no_arrays(self):
        """The records, the durability record and each model's stored values
        go through read_flat; a member array there would shift like the
        cylinder's did."""
        flat = [*(r.members for r in APP.records), gen.config_persist_members(),
                gen.model_cfg_members(APP)]
        for layout in flat:
            for member in layout:
                with self.subTest(member.name):
                    self.assertEqual(member.dimension, 0)

    def test_the_projection_reads_records_through_it(self):
        c = Controller({f"{r.name}Tag": r.members for r in APP.records})
        out = projection.read_records(c)
        for record in APP.records:
            self.assertEqual(out[record.name], c.values[f"{record.name}Tag"])


if __name__ == "__main__":
    unittest.main()

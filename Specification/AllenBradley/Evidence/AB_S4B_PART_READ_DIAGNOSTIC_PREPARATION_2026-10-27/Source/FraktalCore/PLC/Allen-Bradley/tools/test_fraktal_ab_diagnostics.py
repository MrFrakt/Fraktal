"""Core §6.9(a)/§2.7 on the Allen-Bradley binding: what a diagnostic names.

TC3's cylinder names the end sensor that did not report, with its electrical
tag and terminal, and stamps when the fault began. Logix v33 ST cannot hold
that tag (S12), so the work is split along the seam the binding already uses
for text: the library AOI publishes WHICH of its type's I/O roles it
implicates, as bits, and the gateway joins role to the channel this
declaration binds it to. These tests run the AOI's generated ST on the ST
model, then hold the join to the electrical mapping the TC3 press uses.
"""

import dataclasses
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st


APP = demo.application()
NOT_EXTENDED = library.CYLINDER.reasons["CYL_NOT_EXTENDED"]
NOT_RETRACTED = library.CYLINDER.reasons["CYL_NOT_RETRACTED"]
EXTENDED = 1 << library.CYLINDER.io_roles.index("extendedFb")
RETRACTED = 1 << library.CYLINDER.io_roles.index("retractedFb")


class Cylinder:
    """The cylinder AOI's body, run against one context."""

    def __init__(self, **ctx):
        context = st.structure(gen.module_context_members(library.CYLINDER))
        context.update(Par_TaskPeriodMs=10, **ctx)
        self.plc = st.Controller({"Ctx": context, "Scan": 0})
        self.logic = st.parse("\n".join(gen.type_logic(library.CYLINDER)))

    @property
    def ctx(self):
        return self.plc.tags["Ctx"]

    def scan(self, **inputs):
        self.ctx.update(inputs)
        self.plc.tags["Scan"] += 1
        self.plc.run(self.logic)

    def command(self, target, scans, **inputs):
        self.scan(ParCmd_Target=target, Execute=1, **inputs)
        for _ in range(scans):
            self.scan()


class TheTypeNamesTheSensor(unittest.TestCase):
    def test_a_timeout_extending_implicates_the_extended_sensor(self):
        cyl = Cylinder(Par_Speed=1, Par_TimeoutMs=50, OutImm_Pos=0)
        cyl.command(100, 10)
        self.assertEqual(cyl.ctx["OutImm_Reason"], NOT_EXTENDED)
        self.assertEqual(cyl.ctx["ErrorID"], NOT_EXTENDED)
        self.assertEqual(cyl.ctx["OutImm_IoRoles"], EXTENDED)

    def test_a_timeout_retracting_implicates_the_retracted_sensor(self):
        cyl = Cylinder(Par_Speed=1, Par_TimeoutMs=50, OutImm_Pos=100)
        cyl.command(0, 10)
        self.assertEqual(cyl.ctx["OutImm_Reason"], NOT_RETRACTED)
        self.assertEqual(cyl.ctx["OutImm_IoRoles"], RETRACTED)

    def test_a_device_fault_is_a_cylinder_that_does_not_move(self):
        """Found the way a real stuck cylinder is: nothing happens until the
        timeout, which then names the end that never reported."""
        cyl = Cylinder(Par_Speed=25, Par_TimeoutMs=500, OutImm_Pos=0)
        cyl.command(100, 10, FaultRequest=1)
        self.assertEqual((cyl.ctx["Error"], cyl.ctx["OutImm_Pos"]), (0, 0))
        cyl.command(100, 0)
        for _ in range(50):
            cyl.scan()
        self.assertEqual(cyl.ctx["OutImm_Reason"], NOT_EXTENDED)
        self.assertEqual(cyl.ctx["OutImm_IoRoles"], EXTENDED)
        self.assertEqual(cyl.ctx["OutImm_Pos"], 0)
        self.assertGreater(cyl.ctx["FaultScans"], 0)

    def test_the_timeout_is_rated_as_the_registry_rates_it(self):
        """MED, as TC3's F_RationalizeDiagnostic rates CYL_NOT_EXTENDED."""
        cyl = Cylinder(Par_Speed=1, Par_TimeoutMs=50, OutImm_Pos=0)
        cyl.command(100, 10)
        self.assertEqual(cyl.ctx["OutImm_Severity"], 1)

    def test_held_implicates_no_sensor(self):
        cyl = Cylinder(Par_Speed=1, Par_TimeoutMs=500)
        cyl.command(100, 2, HoldRequest=1)
        self.assertEqual(cyl.ctx["OutImm_Held"], 1)
        self.assertEqual(cyl.ctx["OutImm_Reason"],
                         library.CYLINDER.reasons["INTERLOCK_DROPPED"])
        self.assertEqual(cyl.ctx["OutImm_IoRoles"], 0)

    def test_the_execute_drop_clears_it_with_the_reason(self):
        cyl = Cylinder(Par_Speed=1, Par_TimeoutMs=50, OutImm_Pos=0)
        cyl.command(100, 10)
        cyl.scan(Execute=0)
        self.assertEqual((cyl.ctx["OutImm_Reason"], cyl.ctx["OutImm_IoRoles"]), (0, 0))


class TheJoin(unittest.TestCase):
    def test_roles_follow_the_electrical_mapping_not_the_word(self):
        """The slide's logical EXTENDED end is 'inside', where the feeder is
        RETRACTED: _101B301A (CX2030_PRESS_IO_MAPPING, TC3 FB_PressIoCatalog).
        Reading the channel description instead would name the wrong sensor."""
        self.assertEqual(projection.io_join(APP, "PartSlide", EXTENDED)[0], "_101B301A")
        self.assertEqual(projection.io_join(APP, "PartSlide", RETRACTED)[0], "_101B301B")
        self.assertEqual(projection.io_join(APP, "Door", EXTENDED)[0], "_101B201A")
        self.assertEqual(projection.io_join(APP, "PressRam", EXTENDED)[0], "_101B202A")

    def test_the_address_is_the_logix_channel_address(self):
        """channel_address is also what the fieldbus view publishes, so an
        alarm and the channel it cross-links to name the same terminal."""
        self.assertEqual(projection.io_join(APP, "PressRam", RETRACTED),
                         ("_101B202B", "Local:1:I.5"))

    def test_both_roles_join_the_way_tc3_joins_them(self):
        tag, address = projection.io_join(APP, "Door", EXTENDED | RETRACTED)
        self.assertEqual(tag, "_101B201A / _101B201B")
        self.assertEqual(address, "Local:1:I.2 / Local:1:I.3")

    def test_nothing_implicated_names_nothing(self):
        self.assertEqual(projection.io_join(APP, "Door", 0), ("", ""))
        self.assertEqual(projection.io_join(APP, "NoSuchModule", EXTENDED), ("", ""))


class ThePublishedDiagnostic(unittest.TestCase):
    def module(self, **ctx):
        context = st.structure(gen.module_context_members(library.CYLINDER))
        context.update(ctx)
        return projection.module_status(context, APP, "PressRam")

    def test_a_faulted_module_says_what_where_and_since_when(self):
        out = self.module(Error=1, OutImm_Reason=NOT_EXTENDED, OutImm_IoRoles=EXTENDED,
                          DiagStamped=NOT_EXTENDED, DiagSinceDate=20260930,
                          DiagSinceTime=81502250)
        self.assertEqual(out["Status/Diagnostic/Description"], f"std.reason.{NOT_EXTENDED}")
        self.assertEqual(out["Status/Diagnostic/IoTag"], "_101B202A")
        self.assertEqual(out["Status/Diagnostic/Since"], "2026-09-30T08:15:02.250Z")
        self.assertFalse(out["Status/Diagnostic/TimeSynchronized"])

    def test_a_stamp_for_another_reason_is_not_this_ones_onset(self):
        out = self.module(OutImm_Reason=NOT_EXTENDED, DiagStamped=NOT_RETRACTED,
                          DiagSinceDate=20260930, DiagSinceTime=81502250)
        self.assertEqual(out["Status/Diagnostic/Since"], 0)

    def test_no_diagnostic_no_onset(self):
        out = self.module(DiagSinceDate=20260930, DiagSinceTime=81502250)
        self.assertEqual(out["Status/Diagnostic/Since"], 0)
        self.assertEqual(out["Status/Diagnostic/Description"], "")

    def test_the_unit_publishes_the_adopted_childs_sensor(self):
        unit = dict(st.structure(gen.unit_context_members(APP)),
                    Error=1, ErrorID=NOT_EXTENDED, ErrorSource=gen.module_source(APP, "Door"),
                    DiagReason=NOT_EXTENDED, DiagStamped=NOT_EXTENDED, DiagIoRoles=RETRACTED,
                    DiagSinceDate=20260930, DiagSinceTime=1000)
        out = projection.unit_status(unit, None)
        self.assertEqual(out["Status/Diagnostic/ReasonCode"], NOT_EXTENDED)
        self.assertEqual(out["Status/Diagnostic/IoTag"], "_101B201B")

    def test_a_held_child_named_by_the_unit_names_no_sensor(self):
        """A rolled-up hold is the Unit's diagnostic but not a fault, so the
        Unit implicates no I/O for it."""
        held = demo.REASONS["INTERLOCK_DROPPED"]
        unit = dict(st.structure(gen.unit_context_members(APP)),
                    Running=1, DiagReason=held, DiagStamped=held, DiagIoRoles=0)
        out = projection.unit_status(unit, None)
        self.assertEqual(out["Status/Diagnostic/ReasonCode"], held)
        self.assertEqual(out["Status/Diagnostic/IoTag"], "")


class RoleRules(unittest.TestCase):
    def with_channel(self, **changes):
        io = APP.io_modules[0]
        channels = tuple(dataclasses.replace(c, **changes) if c.name == "_101B202A"
                         else c for c in io.channels)
        return dataclasses.replace(APP, io_modules=(
            dataclasses.replace(io, channels=channels),) + APP.io_modules[1:])

    def test_the_press_is_clean(self):
        self.assertEqual(library.validate(APP), [])

    def test_a_role_the_type_does_not_have_is_refused(self):
        found = library.validate(self.with_channel(role="clampedFb"))
        self.assertTrue(any("cannot" in f or "not one" in f for f in found), found)

    def test_a_role_bound_twice_is_refused(self):
        found = library.validate(self.with_channel(role="retractedFb"))
        self.assertTrue(any("already binds" in f for f in found), found)

    def test_a_role_on_an_unowned_channel_is_refused(self):
        found = library.validate(self.with_channel(module_path="", role="extendedFb"))
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()

"""The Fraktal/AB module library: a type is one definition, whoever embeds it.

Logix links nothing at run time, so the only thing that makes these AOIs a
library is that two applications embed the SAME BYTES for the same type. That
is tested here the way it is defined: generate two applications that differ in
every way an application can - name, task period, reason table - and require
the embedded type AOI to be identical.

Before this, the cylinder was generated once per INSTANCE and read the context
UDT's name, the task period and its own reason codes from the application. It
was a copy that happened to agree with its siblings, not a type.
"""

import dataclasses
import re
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_press_demo as demo


APP = demo.application()


def _other_application():
    """Unrelated in everything an application can be."""
    return dataclasses.replace(
        APP, name="Stamp", task_period_ms=20,
        # its own project code, in a band of its own (Core §8.8)
        reasons={**APP.reasons, "SOMETHING_ELSE": 17000})


def _embedded(app, mtype) -> str:
    block = re.search(
        rf'<AddOnInstructionDefinition Name="{gen.type_aoi_name(mtype)}".*?'
        r"</AddOnInstructionDefinition>",
        gen.aoi_definitions(app), re.S)
    assert block, f"{gen.type_aoi_name(mtype)} not embedded in {app.name}"
    return block.group(0)


class OneDefinitionEverywhere(unittest.TestCase):
    def test_two_applications_embed_the_same_bytes(self):
        """The library property itself."""
        self.assertEqual(_embedded(APP, library.CYLINDER),
                         _embedded(_other_application(), library.CYLINDER))

    def test_the_embedded_aoi_is_the_library_aoi(self):
        """An application embeds the type's definition, not its own rendering
        of it."""
        self.assertEqual(_embedded(APP, library.CYLINDER),
                         gen.type_aoi(library.CYLINDER))

    def test_instances_share_their_types_one_definition(self):
        text = gen.aoi_definitions(APP)
        for mtype in library.types_used(APP):
            self.assertEqual(text.count(
                f'<AddOnInstructionDefinition Name="{gen.type_aoi_name(mtype)}"'), 1)
        for module in APP.modules:
            self.assertEqual(gen.module_aoi_name(APP, module),
                             gen.type_aoi_name(library.type_of(module)))
        self.assertEqual(len([m for m in APP.modules
                              if library.type_of(m) is library.CYLINDER]), 3)


class NothingOfTheApplicationLeaks(unittest.TestCase):
    """Each of the three things the per-instance AOI used to read."""

    def setUp(self):
        self.aoi = gen.type_aoi(library.CYLINDER)

    def test_no_application_name(self):
        for app in (APP, _other_application()):
            self.assertNotIn(app.name, self.aoi)

    def test_no_literal_task_period(self):
        """The period arrives through the instance context."""
        self.assertIn("Ctx.Par_TaskPeriodMs", self.aoi)
        self.assertNotRegex(self.aoi, r"ElapsedMs \+ \d")
        self.assertNotRegex(self.aoi, r"Par_TimeoutMs / \d")

    def test_reason_codes_are_the_types(self):
        for code in library.CYLINDER.reasons.values():
            self.assertIn(str(code), self.aoi)

    def test_the_revision_note_describes_the_type_not_an_instance(self):
        for module in APP.modules:
            self.assertNotIn(module.comment, self.aoi)
        self.assertIn(library.CYLINDER.type_key, self.aoi)

    def test_the_context_type_names_no_application(self):
        self.assertEqual(gen.module_context_name(library.CYLINDER), "FRK_T_CylinderCtx")


class ThePeriodIsPerInstance(unittest.TestCase):
    def test_each_instance_context_carries_its_applications_period(self):
        for app in (APP, _other_application()):
            tags = gen.controller_tags(app)
            for module in app.modules:
                if library.type_of(module) is not library.CYLINDER:
                    continue      # only a type that times something has a period
                block = tags.split(f'<Tag Name="{gen.ctx_tag_for(app, module.name)}"')[1]
                block = block.split("</Tag>")[0]
                self.assertIn(
                    f'Name="Par_TaskPeriodMs" DataType="DINT" Radix="Decimal" '
                    f'Value="{app.task_period_ms}"', block)

    def test_a_zero_period_faults_rather_than_hangs(self):
        """No period, no timing - so the module must not run a command it
        cannot time out. It faults on its first busy scan (O10), with TC3's
        code for a cylinder that cannot time a move."""
        import fraktal_ab_st_model as st

        ctx = st.structure(gen.module_context_members(library.CYLINDER))
        ctx.update(Par_TaskPeriodMs=0, ParCmd_Target=100, Execute=1)
        plc = st.Controller({"Ctx": ctx, "Scan": 1})
        plc.run("\n".join(gen.type_logic(library.CYLINDER)))
        self.assertEqual(ctx["Error"], 1)
        self.assertEqual(ctx["ErrorID"], library.CYLINDER.reasons["CYL_CFG_INVALID"])

    def test_the_division_by_the_period_is_guarded(self):
        """A value now, not a constant, and a divide by zero faults the
        controller."""
        aoi = gen.type_aoi(library.CYLINDER)
        guard = aoi.index("IF Ctx.Par_TaskPeriodMs > 0 THEN")
        divide = aoi.index("Ctx.Par_TimeoutMs / Ctx.Par_TaskPeriodMs")
        self.assertLess(guard, divide)


class Validation(unittest.TestCase):
    def test_the_press_is_valid(self):
        self.assertEqual(library.validate(APP), [])

    def test_an_unknown_type_is_refused(self):
        stray = dataclasses.replace(APP.modules[0], type_key="std.moduleType.gizmo")
        app = dataclasses.replace(APP, modules=(stray,) + APP.modules[1:])
        self.assertTrue(any("not a library type" in f
                            for f in library.validate(app)))

    def test_a_registration_that_disagrees_with_its_type_is_refused(self):
        """The type raises the code, so the type is the source."""
        app = dataclasses.replace(
            APP, reasons={**APP.reasons, "CYL_NOT_EXTENDED": 19999})
        self.assertTrue(any("raises 10101" in f for f in library.validate(app)))

    def test_generation_refuses_an_invalid_library_use(self):
        import pathlib
        import tempfile

        stray = dataclasses.replace(APP.modules[0], type_key="std.moduleType.gizmo")
        app = dataclasses.replace(APP, modules=(stray,) + APP.modules[1:])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(decl.DeclarationError):
                gen.generate(app, pathlib.Path(tmp) / "in.L5X",
                             pathlib.Path(tmp) / "out.L5X")

    def test_the_press_registers_its_cylinder_codes_from_the_type(self):
        """Declared once: the press's table is built from the type, so the two
        cannot drift."""
        for name, code in library.CYLINDER.reasons.items():
            self.assertEqual(demo.REASONS[name], code)


if __name__ == "__main__":
    unittest.main()

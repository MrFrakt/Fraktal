"""The second library type: TC3's FB_DigitalInputCM, and the path it proves.

A passive monitor. It publishes its input's Value and Quality as its source
presents them, refuses any command with UNSUPPORTED_COMMAND, and is fed by the
routine from the source the application declares - TC3's HAL. The press's
N100 now waits on `PartPresentSensor` Value AND Quality, as TC3's press does,
instead of on a bare tag.

What makes it a path rather than one module: the type has its own context
(common base + its own members), its own AOI, the same bytes in any
application, and no simulation injections it has no use for.
"""

import dataclasses
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_st_model as st


APP = demo.application()
N = APP.name
SENSOR = next(m for m in APP.modules if m.name == "PartPresentSensor")
SENSOR_CTX = gen.ctx_tag_for(APP, SENSOR.name)
AUTO = next(c for c in APP.chains if c.name == "AUTO")
REFUSED = library.DIGITAL_INPUT.reasons["UNSUPPORTED_COMMAND"]


def run_passive_modules(app, tags, scan=1):
    """The routine's module layer for passive inputs, as generated: its feed
    lines, then the type's AOI body against each instance's context."""
    import re

    feed = [line for line in gen.routine_logic(app)
            if re.search(r"\.Raw\w+ := ", line)]
    st.Controller(tags).run("\n".join(feed))
    for module in app.modules:
        mtype = library.type_of(module)
        if mtype.passive:
            st.Controller({"Ctx": tags[gen.ctx_tag_for(app, module.name)],
                           "Scan": scan}).run("\n".join(gen.type_logic(mtype)))


class Input:
    def __init__(self, **ctx):
        self.ctx = st.structure(gen.module_context_members(library.DIGITAL_INPUT))
        self.ctx.update(ctx)
        self.plc = st.Controller({"Ctx": self.ctx, "Scan": 0})
        self.logic = st.parse("\n".join(gen.type_logic(library.DIGITAL_INPUT)))

    def scan(self, **inputs):
        self.ctx.update(inputs)
        self.plc.tags["Scan"] += 1
        self.plc.run(self.logic)


class TheType(unittest.TestCase):
    def test_value_and_quality_follow_the_source(self):
        di = Input()
        di.scan(RawValue=1, RawQuality=1)
        self.assertEqual((di.ctx["OutImm_Value"], di.ctx["OutImm_Quality"]), (1, 1))
        di.scan(RawValue=0, RawQuality=0)
        self.assertEqual((di.ctx["OutImm_Value"], di.ctx["OutImm_Quality"]), (0, 0))

    def test_published_values_are_booleans(self):
        di = Input()
        di.scan(RawValue=7, RawQuality=-1)
        self.assertEqual((di.ctx["OutImm_Value"], di.ctx["OutImm_Quality"]), (1, 1))

    def test_a_command_is_refused_as_tc3_refuses_it(self):
        di = Input()
        di.scan(Execute=1)
        self.assertEqual((di.ctx["Error"], di.ctx["ErrorID"]), (1, REFUSED))
        self.assertEqual(di.ctx["OutImm_ExecState"], gen.STATE_ERROR)
        self.assertEqual(di.ctx["OutImm_Severity"], 0)   # the registry: LOW
        di.scan(Execute=0)
        self.assertEqual((di.ctx["Error"], di.ctx["OutImm_Reason"]), (0, 0))

    def test_it_marks_its_scan_for_the_ordering_check(self):
        di = Input()
        di.scan()
        self.assertEqual(di.ctx["ModuleScan"], 1)

    def test_its_context_is_the_common_base_plus_its_own(self):
        names = [m.name for m in gen.module_context_members(library.DIGITAL_INPUT)]
        common = [m.name for m in gen.common_context_members()]
        self.assertEqual(names[:len(common)], common)
        self.assertEqual(names[len(common):],
                         ["RawValue", "RawQuality", "OutImm_Value", "OutImm_Quality"])
        self.assertEqual(gen.module_context_name(library.DIGITAL_INPUT),
                         "FRK_T_DigitalInputCtx")

    def test_it_takes_no_simulation_injections(self):
        self.assertEqual(library.DIGITAL_INPUT.injections, ())
        stimulus = gen.stimulus_inputs(APP)
        self.assertNotIn(f"FRK_{N}_Fault{SENSOR.name}", stimulus)
        self.assertNotIn(f"FRK_{N}_Hold{SENSOR.name}", stimulus)


class TheRoutineFeedsIt(unittest.TestCase):
    def test_from_its_declared_source_before_it_runs(self):
        routine = list(gen.routine_logic(APP))
        feed = routine.index(f"{SENSOR_CTX}.RawValue := {SENSOR.input};")
        call = next(i for i, line in enumerate(routine)
                    if line.startswith(f"{gen.type_aoi_name(library.DIGITAL_INPUT)}("))
        unit = next(i for i, line in enumerate(routine)
                    if line.startswith(f"{gen.unit_aoi_name(APP)}("))
        self.assertLess(feed, call)
        self.assertLess(call, unit)

    def test_the_press_harness_still_drives_it_through_the_same_tag(self):
        import fraktal_ab_press_execute as px

        self.assertEqual(SENSOR.input, px.PART_PRESENT)
        self.assertIn(px.PART_PRESENT, px.WRITABLE)


class N100WaitsOnTheSensor(unittest.TestCase):
    def test_every_rendition_reads_the_sensor_not_the_tag(self):
        names = gen.Names(APP, in_aoi=False)
        n100 = next(s for s in AUTO.steps if s.number == 100)
        index = gen.ordered_steps(APP).index(100)
        texts = {
            "ST": "\n".join(gen.chain_st_logic(APP, AUTO)),
            "SFC transition": gen.sfc_condition(APP, n100, "A", names),
            "SFC action": "\n".join(gen.sfc_action_logic(APP, AUTO, n100, index, names)),
            "LD": gen.ld_step_rung(APP, AUTO, n100, index, names),
        }
        for rendition, text in texts.items():
            self.assertIn(f"{SENSOR_CTX}.OutImm_Value", text, rendition)
            self.assertIn(f"{SENSOR_CTX}.OutImm_Quality", text, rendition)

    def test_a_part_with_bad_quality_is_not_a_part(self):
        """TC3's condition is Value AND Quality: a value the source does not
        vouch for does not start a cycle."""
        tags = {
            f"FRK_{N}_Unit": st.structure(gen.unit_context_members(APP)),
            f"FRK_{N}_Chart": st.structure(gen.chart_members(APP)),
            **{f"{r.name}Tag": st.structure(r.members) for r in APP.records},
            f"FRK_{N}_ScanCount": 1,
        }
        for module in APP.modules:
            tags[gen.ctx_tag_for(APP, module.name)] = st.structure(
                gen.module_members(module))
        for tag in APP.sim_inputs:
            tags[tag] = 1
        tags[f"FRK_{N}_Unit"].update(Step=100, PrevStep=-1)
        run_passive_modules(APP, tags)
        tags[SENSOR_CTX]["OutImm_Quality"] = 0
        st.Controller(tags, routines={gen.step_mark_routine_name(APP): gen.step_mark_logic(APP)}).run(
            "\n".join(gen.chain_st_logic(APP, AUTO)))
        self.assertEqual(tags[f"FRK_{N}_Unit"]["Step"], 100)
        self.assertEqual(tags[f"FRK_{N}_Chart"]["CondOk"][0], 0)


class ItIsALibraryType(unittest.TestCase):
    def test_one_definition_the_same_in_any_application(self):
        other = dataclasses.replace(APP, name="Stamp", task_period_ms=20)
        self.assertEqual(gen.type_aoi(library.DIGITAL_INPUT),
                         [a for a in gen.module_aois(other)
                          if gen.type_aoi_name(library.DIGITAL_INPUT) in a][0])

    def test_the_manifest_describes_it_with_its_own_layout(self):
        content = manifest.content(APP)
        keys = {r["NumericKey"]: r["PortableKey"] for r in content["Localization"]}
        row = next(r for r in content["Modules"]
                   if keys[r["CanonicalPathKey"]] == f"{N}.{SENSOR.name}")
        fields = {keys[f["PathKey"]] for f in content["Fields"]
                  if f["ModuleId"] == row["ModuleId"]}
        self.assertEqual(fields, {m.name for m in gen.module_members(SENSOR)})

    def test_a_passive_input_with_commands_is_refused(self):
        bad = dataclasses.replace(SENSOR, commands=(decl.Command("READ", 1, 0, ""),))
        app = dataclasses.replace(APP, modules=tuple(
            bad if m.name == SENSOR.name else m for m in APP.modules))
        self.assertTrue(any("passive" in f for f in library.validate(app)))

    def test_a_passive_input_needs_a_declared_source(self):
        bad = dataclasses.replace(SENSOR, input="FRK_Press_Nowhere")
        app = dataclasses.replace(APP, modules=tuple(
            bad if m.name == SENSOR.name else m for m in APP.modules))
        self.assertTrue(any("not a declared source" in f for f in library.validate(app)))

    def test_its_channel_is_bound_to_its_input_role(self):
        channel = next(c for io in APP.io_modules for c in io.channels
                       if c.name == "_101B601")
        self.assertEqual((channel.module_path, channel.role),
                         (SENSOR.name, "input"))


if __name__ == "__main__":
    unittest.main()

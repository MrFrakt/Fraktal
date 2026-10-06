"""The fourth library type: TC3's FB_AirPressureMonitorCM, and air as an
interlock.

Two pressure switches. Pressure is OK when the operating switch is on, the low
switch is off and the reading is trusted. Both on is implausible, but only once
it has persisted for the station's ConflictTime, because the switches overlap
while air fills. It is then a fault naming both switches, latched until an
operator reset.

TC3's press makes air each cylinder's own interlock (SetAreaSafe): lost
mid-stroke, the cylinder HOLDS, with no fault and no timeout, and resumes by
itself. N100 and the start latch wait on PressureOk.
"""

import unittest

import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st


APP = demo.application()
N = APP.name
MONITOR = next(m for m in APP.modules if m.name == "AirPressureMonitor")
CONFLICT = library.AIR_PRESSURE.reasons["AIR_SWITCH_CONFLICT"]
INTERLOCK = library.CYLINDER.reasons["INTERLOCK_DROPPED"]
BOTH = 3


class Monitor:
    def __init__(self, conflict_ms=500):
        self.ctx = st.structure(gen.module_context_members(library.AIR_PRESSURE))
        self.ctx.update(Par_TaskPeriodMs=10, Par_ConflictTimeMs=conflict_ms, RawQuality=1)
        self.plc = st.Controller({"Ctx": self.ctx, "Scan": 0})
        self.logic = st.parse("\n".join(gen.type_logic(library.AIR_PRESSURE)))

    def scan(self, low=None, operating=None, **raw):
        if low is not None:
            raw["RawLow"] = low
        if operating is not None:
            raw["RawOperating"] = operating
        raw.setdefault("ResetRequest", 0)
        self.ctx.update(raw)
        self.plc.tags["Scan"] += 1
        self.plc.run(self.logic)
        return self.ctx


class PressureOk(unittest.TestCase):
    def test_operating_not_low_and_trusted(self):
        m = Monitor()
        self.assertEqual(m.scan(low=0, operating=1)["OutImm_PressureOk"], 1)
        self.assertEqual(m.scan(low=1, operating=0)["OutImm_PressureOk"], 0)
        self.assertEqual(m.scan(low=0, operating=0)["OutImm_PressureOk"], 0)
        self.assertEqual(m.scan(low=0, operating=1, RawQuality=0)["OutImm_PressureOk"], 0)


class TheConflict(unittest.TestCase):
    def test_a_brief_overlap_while_filling_is_not_a_fault(self):
        m = Monitor(conflict_ms=500)
        for _ in range(49):
            ctx = m.scan(low=1, operating=1)
        self.assertEqual((ctx["OutImm_Contradictory"], ctx["Error"]), (0, 0))
        self.assertEqual(ctx["OutImm_PressureOk"], 0)   # not OK either way

    def test_a_persistent_one_faults_naming_both_switches(self):
        m = Monitor(conflict_ms=500)
        for _ in range(50):
            ctx = m.scan(low=1, operating=1)
        self.assertEqual((ctx["OutImm_Contradictory"], ctx["Error"], ctx["ErrorID"]),
                         (1, 1, CONFLICT))
        self.assertEqual(ctx["OutImm_IoRoles"], BOTH)
        self.assertEqual(ctx["OutImm_Severity"], 1)       # the registry: MED
        self.assertEqual(projection.io_join(APP, MONITOR.name, BOTH),
                         ("_000MB085A_2 / _000MB085A_4", "Local:1:I.9 / Local:1:I.10"))

    def test_it_latches_until_an_operator_reset(self):
        m = Monitor(conflict_ms=0)
        m.scan(low=1, operating=1)
        ctx = m.scan(low=0, operating=1)                 # the switches agree again
        self.assertEqual(ctx["Error"], 1)                 # still latched
        ctx = m.scan(low=0, operating=1, ResetRequest=1)
        self.assertEqual((ctx["Error"], ctx["ErrorID"], ctx["OutImm_Reason"]), (0, 0, 0))

    def test_a_reset_while_it_persists_does_not_clear_it(self):
        m = Monitor(conflict_ms=0)
        m.scan(low=1, operating=1)
        ctx = m.scan(low=1, operating=1, ResetRequest=1)
        self.assertEqual(ctx["Error"], 1)

    def test_a_refused_command_clears_on_its_drop_and_the_latch_survives_idle(self):
        """The passive handshake resets on the DROP of Execute; a level reset
        would clear the latched conflict on every idle scan."""
        m = Monitor(conflict_ms=0)
        m.scan(low=0, operating=1, Execute=1)
        self.assertEqual(m.ctx["ErrorID"], library.AIR_PRESSURE.reasons["UNSUPPORTED_COMMAND"])
        ctx = m.scan(low=0, operating=1, Execute=0)
        self.assertEqual(ctx["Error"], 0)
        m.scan(low=1, operating=1)
        for _ in range(5):
            ctx = m.scan(low=1, operating=1)       # idle, Execute low throughout
        self.assertEqual((ctx["Error"], ctx["ErrorID"]), (1, CONFLICT))


class TheStationValue(unittest.TestCase):
    def test_conflict_time_is_station_data_under_tc3s_keys(self):
        record = next(r for r in APP.records if r.station_cfg)
        member = next(m for m in record.members if m.name == "AirConflictTimeMs")
        self.assertEqual((member.write_key, member.label_key, member.initial),
                         ("airPressure.conflictTime", "std.config.airPressure.conflictTime", 500))
        self.assertEqual((member.minimum, member.maximum), (0, 10000))
        self.assertGreaterEqual(record.schema_version, 2)   # joined the layout at 2

    def test_the_routine_carries_it_into_the_monitor_each_scan(self):
        routine = list(gen.routine_logic(APP))
        ctx = gen.ctx_tag_for(APP, MONITOR.name)
        line = f"{ctx}.Par_ConflictTimeMs := FRK_T_PressStationCfgTag.AirConflictTimeMs;"
        call = next(i for i, l in enumerate(routine)
                    if l.startswith(f"{gen.type_aoi_name(library.AIR_PRESSURE)}("))
        self.assertLess(routine.index(line), call)

    def test_it_is_a_published_write_capability(self):
        content = manifest.content(APP)
        keys = {r["NumericKey"]: r["PortableKey"] for r in content["Localization"]}
        writes = {keys[r["WriteKeyKey"]] for r in content["WriteCapabilities"]}
        self.assertIn("airPressure.conflictTime", writes)


class AirIsEachCylindersInterlock(unittest.TestCase):
    def cylinder(self, **ctx):
        state = st.structure(gen.module_context_members(library.CYLINDER))
        state.update(Par_TaskPeriodMs=10, Par_Speed=1, Par_TimeoutMs=500, **ctx)
        return state, st.Controller({"Ctx": state, "Scan": 0}), st.parse(
            "\n".join(gen.type_logic(library.CYLINDER)))

    def test_air_lost_mid_stroke_holds_without_a_fault_and_resumes(self):
        ctx, plc, logic = self.cylinder()

        def scan(**inputs):
            ctx.update(inputs)
            plc.tags["Scan"] += 1
            plc.run(logic)

        scan(ParCmd_Target=100, Execute=1)
        for _ in range(10):
            scan()
        moved = ctx["OutImm_Pos"]
        for _ in range(100):                  # far past the 500 ms timeout
            scan(AreaSafe=0)
        self.assertEqual((ctx["OutImm_Held"], ctx["OutImm_Reason"], ctx["Error"]),
                         (1, INTERLOCK, 0))
        self.assertEqual(ctx["OutImm_Pos"], moved)
        for _ in range(3):
            scan(AreaSafe=1)
        self.assertEqual((ctx["OutImm_Held"], ctx["Error"]), (0, 0))
        self.assertGreater(ctx["OutImm_Pos"], moved)

    def test_every_cylinder_is_bound_to_pressure_ok_and_the_monitor_runs_first(self):
        routine = list(gen.routine_logic(APP))
        monitor_call = next(i for i, l in enumerate(routine)
                            if l.startswith(f"{gen.type_aoi_name(library.AIR_PRESSURE)}("))
        ok = f"{gen.ctx_tag_for(APP, MONITOR.name)}.OutImm_PressureOk"
        for module in APP.modules:
            if library.type_of(module) is not library.CYLINDER:
                continue
            ctx = gen.ctx_tag_for(APP, module.name)
            line = f"IF ({ok} <> 0) THEN {ctx}.AreaSafe := 1; ELSE {ctx}.AreaSafe := 0; END_IF;"
            self.assertIn(line, routine, module.name)
            self.assertLess(monitor_call, routine.index(line), module.name)


class N100AndTheLatchReadTheMonitor(unittest.TestCase):
    def test_n100_and_the_latch_wait_on_pressure_ok(self):
        ok = f"{gen.ctx_tag_for(APP, MONITOR.name)}.OutImm_PressureOk"
        auto = next(c for c in APP.chains if c.name == "AUTO")
        self.assertIn(ok, "\n".join(gen.chain_st_logic(APP, auto)))
        self.assertIn("CtxAirPressureMonitor.OutImm_PressureOk",
                      "\n".join(gen.start_latch_logic(APP)))

    def test_its_switches_are_bound_to_their_channels(self):
        roles = {c.name: c.role for io in APP.io_modules for c in io.channels
                 if c.module_path == MONITOR.name}
        self.assertEqual(roles, {"_000MB085A_2": "low", "_000MB085A_4": "operating"})


if __name__ == "__main__":
    unittest.main()

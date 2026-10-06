"""Core §3.13 on the Allen-Bradley binding: the flow chart, row by row.

TC3's FB_UnitBase discovers a row the first time a step is entered in a mode,
numbers rows in that order, keeps each row's last visit duration and any
§6.9(e) message the step left, and starts over when the mode changes. The AB
controller keeps the same record (RowEpoch/RowOf/LastMs/WarnReason) and the
gateway joins it to the declaration's static half of each row.

The first class walks the generated AUTO chain on the ST model against a
plant that answers every command at once, so the rows are checked against the
order the chain really entered its steps - not against a list written here.
"""

import dataclasses
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_library as library
import fraktal_ab_st_model as st
from test_fraktal_ab_digital_input import run_passive_modules


APP = demo.application()
N = APP.name
AUTO = next(c for c in APP.chains if c.name == "AUTO")
ORDER = gen.ordered_steps(APP)
UNIT, CHART = f"FRK_{N}_Unit", f"FRK_{N}_Chart"
# the reason the plant emulation raises for a module it holds faulted
DEVICE_FAULT = demo.REASONS["CYL_NOT_EXTENDED"]


class Press:
    """The AUTO chain's ST rendition over a plant that answers at once."""

    def __init__(self, faults=()):
        tags = {
            UNIT: st.structure(gen.unit_context_members(APP)),
            CHART: st.structure(gen.chart_members(APP)),
            **{f"{r.name}Tag": st.structure(r.members) for r in APP.records},
            f"FRK_{N}_ScanCount": 0,
        }
        for module in APP.modules:
            tags[gen.ctx_tag_for(APP, module.name)] = st.structure(
                gen.module_members(module))
        for tag in APP.sim_inputs:
            tags[tag] = 1
        self.tags = tags
        self.faults = set(faults)
        self.plc = st.Controller(tags, routines={gen.step_mark_routine_name(APP): gen.step_mark_logic(APP)})
        self.chain = st.parse("\n".join(gen.chain_st_logic(APP, AUTO)))
        mode_change = _block(gen.unit_logic(APP), "IF Ctx.ModeRequest <> Ctx.Mode THEN")
        self.mode_change = st.parse("\n".join(mode_change))
        # The Unit AOI's start latch, as generated, run against the same
        # contexts under the names the AOI gives them.
        self.latch = st.parse("\n".join(gen.start_latch_logic(APP)))
        self.two_hand = APP.start_control.pulse.module
        self.operator = True      # releases and presses the two-hand at N100
        self.entered: list[int] = []
        self.unit.update(Mode=AUTO.mode_ordinal, ModeRequest=AUTO.mode_ordinal,
                         Running=1, PrevStep=-1)

    @property
    def unit(self):
        return self.tags[UNIT]

    @property
    def chart(self):
        return self.tags[CHART]

    def _plant(self):
        run_passive_modules(APP, self.tags, self.tags[f"FRK_{N}_ScanCount"])
        for module in APP.modules:
            if library.type_of(module).passive:
                continue          # fed, never commanded
            ctx = self.tags[gen.ctx_tag_for(APP, module.name)]
            if not ctx["Execute"]:
                ctx.update(Done=0, Error=0, ErrorID=0, OutImm_Reason=0)
            elif not ctx["Done"] and not ctx["Error"]:
                if module.name in self.faults:
                    ctx.update(Error=1, ErrorID=DEVICE_FAULT, OutImm_Reason=DEVICE_FAULT)
                else:
                    ctx["Done"] = 1

    def _operator(self):
        """At N100 with no start latched, release the two-hand, then press it:
        TC3's module arms only on a release between starts."""
        two_hand = next(m.input for m in APP.modules if m.name == self.two_hand)
        waiting = self.unit["Step"] == 100 and self.unit["PrevStep"] == 100
        if self.operator and waiting and not self.unit["StartLatched"]:
            self.tags[two_hand] = 0 if self.tags[two_hand] else 1

    def _unit_latch(self):
        aoi = {"Ctx": self.unit, "Chart": self.chart}
        for module in APP.modules:
            aoi[gen._module_ref(APP, module.name)] = \
                self.tags[gen.ctx_tag_for(APP, module.name)]
        for tag in APP.sim_inputs:
            aoi[gen.sim_param(APP, tag)] = self.tags[tag]
        st.Controller(aoi).run(self.latch)

    def scan(self):
        self.tags[f"FRK_{N}_ScanCount"] += 1
        self._operator()
        self._plant()
        self._unit_latch()
        before = self.unit["Step"]
        self.plc.run(self.chain)
        if self.unit["PrevStep"] == before and (not self.entered
                                                or self.entered[-1] != before):
            self.entered.append(before)

    def run_until(self, predicate, limit=2000):
        for _ in range(limit):
            self.scan()
            if predicate(self):
                return True
        return False

    def change_mode(self, ordinal):
        self.unit["ModeRequest"] = ordinal
        # The mode owner's own names for what it touches (it also releases
        # any manual command when the mode changes).
        self.plc.tags.update({"Ctx": self.unit, "Chart": self.chart})
        self.plc.tags.update({f"Ctx{m.name}": self.tags[gen.ctx_tag_for(APP, m.name)]
                              for m in APP.modules})
        self.plc.run(self.mode_change)

    def rows(self):
        """(row, step) pairs of this mode session, in row order."""
        chart = self.chart
        found = sorted(
            (chart["RowOf"][i], number) for i, number in enumerate(ORDER)
            if chart["RowEpochOf"][i] == chart["RowEpoch"]
            and 1 <= chart["RowOf"][i] <= chart["RowCount"])
        return found


def _block(lines, opener):
    """The IF block that starts at `opener`, through its matching END_IF."""
    lines = list(lines)
    start = lines.index(opener)
    depth = 0
    for end in range(start, len(lines)):
        line = lines[end].strip()
        if line.startswith("IF ") and not line.endswith("END_IF;"):
            depth += 1
        elif line.startswith("END_IF"):
            depth -= 1
            if depth == 0:
                return lines[start:end + 1]
    raise AssertionError(f"no END_IF for {opener}")


def one_cycle(press):
    """Run until the chain is back at its start step after a full cycle."""
    start = press.unit["CycleCount"]
    assert press.run_until(lambda p: p.unit["CycleCount"] > start), "no cycle"
    assert press.run_until(lambda p: p.unit["Step"] == 100)


class RowsAreDiscoveredByVisit(unittest.TestCase):
    def test_rows_are_numbered_in_the_order_the_chain_entered_them(self):
        press = Press()
        one_cycle(press)
        rows = [step for _, step in press.rows()]
        first_visits = list(dict.fromkeys(press.entered))
        self.assertEqual(rows, first_visits)
        self.assertEqual([row for row, _ in press.rows()],
                         list(range(1, len(rows) + 1)))

    def test_a_second_cycle_adds_no_rows(self):
        press = Press()
        one_cycle(press)
        before = press.rows()
        one_cycle(press)
        self.assertEqual(press.rows(), before)

    def test_a_row_keeps_its_last_visit_duration(self):
        """The settle delay is a declared number of scans; the row says so
        even though no poll could have timed it."""
        press = Press()
        one_cycle(press)
        index = ORDER.index(170)
        settle = APP.records[0].members  # TransferSettleMs is the delay
        declared = next(m.initial for m in settle if m.name == "TransferSettleMs")
        self.assertGreaterEqual(press.chart["LastMs"][index], declared)

    def test_a_mode_change_starts_a_new_chart(self):
        press = Press()
        one_cycle(press)
        self.assertTrue(press.rows())
        press.change_mode(demo.MODE_MANUAL)
        self.assertEqual(press.rows(), [])
        self.assertEqual(press.chart["RowCount"], 0)
        press.change_mode(AUTO.mode_ordinal)
        press.unit.update(Running=1, PrevStep=-1)
        press.run_until(lambda p: p.unit["PrevStep"] == 110)   # 110 entered
        # entering AUTO starts at its init step, so that is the new row 1
        self.assertEqual([s for _, s in press.rows()], [0, 100, 110])


class AReportMarksItsRow(unittest.TestCase):
    def test_the_ram_failing_marks_n200_with_its_reason_and_source(self):
        press = Press(faults={"PressRam"})
        # the ram is also commanded at N110; let it through there
        press.faults.clear()
        press.run_until(lambda p: p.unit["Step"] == 180)
        press.faults.add("PressRam")
        press.run_until(lambda p: p.unit["Step"] == 210)
        index = ORDER.index(200)
        self.assertEqual(press.chart["WarnReason"][index], DEVICE_FAULT)
        self.assertEqual(press.chart["WarnSource"][index],
                         gen.module_source(APP, "PressRam"))

    def test_the_next_visit_starts_clean(self):
        press = Press()
        index = ORDER.index(200)
        press.chart["WarnReason"][index] = DEVICE_FAULT
        press.run_until(lambda p: p.unit["Step"] == 220)
        self.assertEqual(press.chart["WarnReason"][index], 0)


class EveryRenditionRecords(unittest.TestCase):
    def test_shared_entry_service_preserves_each_cursor_visit_and_step_clock(self):
        names = gen.Names(APP, in_aoi=False)
        plc = Press().plc
        unit, chart = plc.tags[UNIT], plc.tags[CHART]
        for index, number in enumerate(ORDER):
            with self.subTest(step=number):
                unit.update(Step=number, PrevStep=-1)
                chart['WarnReason'][index] = DEVICE_FAULT
                chart['LastMs'][index] = 99
                chart['StallReason'] = DEVICE_FAULT
                plc.tags[names.scan] = 40
                caller = '\n'.join(gen._mark_step(APP, index, names))
                plc.run(caller)
                self.assertEqual((chart['StepCursor'], chart['ActiveStepNumber']), (index, number))
                self.assertEqual((chart['Visited'][index], chart['EnterCount'][index]), (1, 1))
                self.assertEqual((chart['RowOf'][index], chart['RowCount']), (index + 1, index + 1))
                self.assertEqual((chart['LastMs'][index], chart['WarnReason'][index], chart['StallReason']), (0, 0, 0))
                self.assertEqual((unit['StepScan'], unit['PrevStep'], chart['CurrentStepMs']), (40, number, 0))
                chart['LastMs'][index] = 99
                chart['WarnReason'][index] = DEVICE_FAULT
                plc.tags[names.scan] = 43
                plc.run(caller)
                self.assertEqual(chart['CurrentStepMs'], 3 * APP.task_period_ms)
                self.assertEqual((chart['EnterCount'][index], chart['RowCount']), (1, index + 1))
                self.assertEqual((chart['LastMs'][index], chart['WarnReason'][index]), (99, DEVICE_FAULT))
                unit['PrevStep'] = -1
                plc.run(caller)
                self.assertEqual((chart['EnterCount'][index], chart['RowCount']), (2, index + 1))
                self.assertEqual((chart['LastMs'][index], chart['WarnReason'][index]), (99, 0))
        chart['RowEpoch'] += 1
        chart['RowCount'] = 0
        unit.update(Step=ORDER[0], PrevStep=-1)
        plc.run('\n'.join(gen._mark_step(APP, 0, names)))
        self.assertEqual((chart['RowOf'][0], chart['RowEpochOf'][0], chart['RowCount']), (1, chart['RowEpoch'], 1))
        self.assertEqual(chart['LastMs'][0], 0)

    def test_the_sfc_action_discovers_the_row(self):
        names = gen.Names(APP, in_aoi=False)
        index = ORDER.index(100)
        plc = Press().plc
        plc.tags[UNIT].update(Step=100, PrevStep=-1)
        plc.run("\n".join(gen.sfc_action_logic(
            APP, AUTO, next(s for s in AUTO.steps if s.number == 100), index, names)))
        self.assertEqual(plc.tags[CHART]["RowOf"][index], 1)
        self.assertEqual(plc.tags[CHART]["RowEpochOf"][index], 1)

    def test_the_ladder_rung_discovers_the_row_and_marks_a_report(self):
        names = gen.Names(APP, in_aoi=False)
        step = next(s for s in AUTO.steps if s.number == 200)
        index = ORDER.index(200)
        rung = gen.ld_step_rung(APP, AUTO, step, index, names)
        self.assertIn(f"[NEQ({CHART}.RowEpochOf[{index}],{CHART}.RowEpoch)", rung)
        self.assertIn(f"MOV({CHART}.RowCount,{CHART}.RowOf[{index}])", rung)
        self.assertIn(f"MOV(0,{CHART}.WarnReason[{index}])]", rung)
        self.assertIn(f"{CHART}.WarnReason[{index}])", rung.split("ReportedSource")[1])
        self.assertEqual(rung.count("["), rung.count("]"))


class ThePublishedChart(unittest.TestCase):
    def unit(self, **values):
        unit = st.structure(gen.unit_context_members(APP))
        unit.update(Mode=AUTO.mode_ordinal, **values)
        return unit

    def test_rows_publish_in_row_order_with_their_static_half(self):
        chart = st.structure(gen.chart_members(APP))
        chart["RowEpoch"] = 3
        for number, row in ((100, 1), (110, 2)):
            index = ORDER.index(number)
            chart["RowEpochOf"][index], chart["RowOf"][index] = 3, row
        chart["RowCount"] = 2
        out = projection.sequence_status(APP, self.unit(), chart)
        self.assertEqual(out["SequenceStepCount"], 2)
        self.assertEqual(out["SequenceSteps[1]/StepNo"], 100)
        self.assertEqual(out["SequenceSteps[2]/StepNo"], 110)
        self.assertEqual(out["SequenceSteps[2]/StepName"], "project.step.ramUp")
        self.assertEqual(out["SequenceSteps[2]/AwaitingLabel"], "PressRam.RETRACT")
        self.assertEqual(out["SequenceSteps[2]/AwaitsPath"], f"{N}.PressRam")
        self.assertTrue(out["SequenceSteps[1]/Visited"])
        self.assertFalse(out["SequenceSteps[1]/ErrorActive"])

    def test_a_stale_session_is_not_published(self):
        chart = st.structure(gen.chart_members(APP))
        chart.update(RowEpoch=4, RowCount=0)
        index = ORDER.index(100)
        chart["RowEpochOf"][index], chart["RowOf"][index] = 3, 1
        out = projection.sequence_status(APP, self.unit(), chart)
        self.assertEqual(out["SequenceStepCount"], 0)

    def test_the_path_set_does_not_move_with_the_rows(self):
        empty = projection.sequence_status(APP, self.unit(), st.structure(
            gen.chart_members(APP)))
        chart = st.structure(gen.chart_members(APP))
        chart.update(RowEpoch=1, RowCount=1)
        chart["RowEpochOf"][ORDER.index(100)] = 1
        chart["RowOf"][ORDER.index(100)] = 1
        full = projection.sequence_status(APP, self.unit(), chart)
        self.assertEqual(set(empty), set(full))

    def test_a_report_is_a_warning_row_with_its_note(self):
        chart = st.structure(gen.chart_members(APP))
        chart.update(RowEpoch=1, RowCount=1)
        index = ORDER.index(200)
        chart["RowEpochOf"][index], chart["RowOf"][index] = 1, 1
        chart["WarnReason"][index] = DEVICE_FAULT
        chart["WarnSource"][index] = gen.module_source(APP, "PressRam")
        out = projection.sequence_status(APP, self.unit(), chart)
        self.assertTrue(out["SequenceSteps[1]/WarningActive"])
        self.assertEqual(out["SequenceAnnotationCount"], 1)
        self.assertEqual(out["SequenceAnnotations[1]/RowIdx"], 1)
        # a registered reason carries TC3's text key
        self.assertEqual(out["SequenceAnnotations[1]/Key"], f"std.reason.{DEVICE_FAULT}")
        self.assertEqual(out["SequenceAnnotations[1]/SourcePath"], f"{N}.PressRam")
        self.assertFalse(out["SequenceAnnotations[1]/IsError"])

    def test_the_cursor_follows_the_running_step_only(self):
        chart = st.structure(gen.chart_members(APP))
        chart.update(RowEpoch=1, RowCount=2, ActiveStepNumber=110, CurrentStepMs=40)
        for number, row in ((100, 1), (110, 2)):
            chart["RowEpochOf"][ORDER.index(number)] = 1
            chart["RowOf"][ORDER.index(number)] = row
        running = projection.sequence_status(
            APP, self.unit(Step=110, Running=1), chart)
        self.assertEqual((running["ActiveSteps[1]/RowIdx"],
                          running["ActiveSteps[1]/Elapsed"]), (2, 40))
        stopped = projection.sequence_status(APP, self.unit(Step=110), chart)
        self.assertEqual(stopped["ActiveSteps[1]/RowIdx"], 0)
        faulted = projection.sequence_status(
            APP, self.unit(Step=110, Running=1, Error=1), chart)
        self.assertEqual(faulted["ActiveSteps[1]/RowIdx"], 0)
        moved_on = projection.sequence_status(
            APP, self.unit(Step=130, Running=1), chart)
        self.assertEqual(moved_on["ActiveSteps[1]/RowIdx"], 0)

    def test_the_view_is_enabled_for_a_unit_with_chains(self):
        out = projection.sequence_status(APP, self.unit(), None)
        self.assertTrue(out["SequenceViewEnabled"])
        self.assertEqual(out["SequenceStepCount"], 0)


class TheDeclarationFits(unittest.TestCase):
    def test_the_longest_chain_fits_the_chart(self):
        self.assertLessEqual(projection.sequence_slots(APP), APP.chart_steps)
        self.assertEqual(projection.sequence_slots(APP),
                         max(len(c.steps) for c in APP.chains))


if __name__ == "__main__":
    unittest.main()

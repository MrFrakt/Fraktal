"""Core §8.3 alarm log on the Allen-Bradley binding, run rather than read.

Every test here EXECUTES the ST `alarm_log_logic` emits, on the ST model, scan
by scan, and checks what the tags hold afterwards. The behaviour held to is
TC3's FB_UnitBase/FB_AlarmLog, because Core O8 asks one behaviour of every
binding:

* ERROR entry raises one MANUAL_RESET event; staying in ERROR raises nothing;
* ERROR exit marks it gone, which for a manual event is WAIT_RESET - still
  blocking a restart (§8.3(b));
* an operator reset closes WAIT_RESET events AND active manual ones (TC3
  IMPLEMENTATION_NOTES §76), each into the ring; a cause still present is
  simply raised again as a new event;
* a full active list says so (`Truncated`) and never overwrites an open event;
* the ring wraps, and a wrap is not an out-of-range subscript - which on Logix
  would be a major fault, halting the press.

The one piece of the Unit AOI the bench stands in for is its reset block,
which clears Error/ErrorID/ErrorSource earlier in the same scan
(`unit_logic`, "IF Ctx.ResetRequest <> 0"). A cause that is still live is
modeled by the test setting Error again, which is what the rollup does.
"""

import datetime
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st


APP = demo.application()
N = APP.name
LOW, HIGH = 0, gen.SEVERITY_HIGH
R = demo.REASONS
NOT_EXTENDED, NOT_RETRACTED = R["CYL_NOT_EXTENDED"], R["CYL_NOT_RETRACTED"]
INTERLOCK, TWO_HAND = R["INTERLOCK_DROPPED"], R["TWO_HAND_RELEASED"]
PERIOD = APP.task_period_ms


class Bench:
    """The alarm log's tags, and one scan of it at a time."""

    def __init__(self, logic: list[str] | None = None):
        self.now = datetime.datetime(2026, 9, 29, 23, 59, 59, 999600)
        tags = {
            f"FRK_{N}_Unit": st.structure(gen.unit_context_members(APP)),
            gen.alarm_active_tag(APP): st.structure(gen.alarm_active_members()),
            gen.alarm_ring_tag(APP): st.structure(gen.alarm_ring_members()),
            # The degradation watch's count, which the log turns into events.
            gen.profiler_tag(APP): st.structure(gen.profiler_members(APP)),
            # §8.12's conditions, which the log holds open while they last.
            gen.system_health_tag(APP): st.structure(gen.system_health_members()),
            f"FRK_{N}_ScanCount": 0,
            f"FRK_{N}_ResetRequest": 0,
            **{f"{r.name}Tag": st.structure(r.members) for r in APP.records},
        }
        for module in APP.modules:
            tags[gen.ctx_tag_for(APP, module.name)] = st.structure(
                gen.module_members(module))
        for name, dimension in {**gen.clock_tags(APP),
                                **gen.alarm_scratch_tags(APP),
                                gen.diagnostic_scratch_tag(APP): 0,
                                gen.stall_limit_tag(APP): 0}.items():
            tags[name] = [0] * dimension if dimension else 0
        self.controller = st.Controller(tags, {"GSV": st.wall_clock(self._clock)},
                                        routines=dict(gen.alarm_service_routines(APP)))
        import fraktal_ab_shelving as shelving
        tags[shelving.tag(APP)] = st.structure(shelving.members())
        # The three blocks in routine order, as routine_logic emits them.
        self.program = st.parse("\n".join(
            gen.wall_clock_logic(APP) + gen.diagnostic_logic(APP)
            + (logic or gen.alarm_log_logic(APP))))

    def _clock(self):
        t = self.now
        return (t.year, t.month, t.day, t.hour, t.minute, t.second, t.microsecond)

    @property
    def unit(self):
        return self.controller.tags[f"FRK_{N}_Unit"]

    @property
    def log(self):
        return self.controller.tags[gen.alarm_active_tag(APP)]

    @property
    def ring(self):
        return self.controller.tags[gen.alarm_ring_tag(APP)]

    def ctx(self, module_number):
        return self.controller.tags[
            gen.ctx_tag_for(APP, APP.modules[module_number - 1].name)]

    def scan(self, error=None, reason=NOT_EXTENDED, source=1, reset=False, roles=0,
             report=None):
        """One scan. `error` None leaves the Unit's Error as it was.

        `roles` is what the faulting child's AOI implicated this scan; the
        child still holds it in the scan its fault is adopted or reported, and
        has cleared it by the next (the chain dropped its Execute).
        `report` is (reason, source) for a §6.9(e) report this scan.
        """
        tags = self.controller.tags
        tags[f"FRK_{N}_ScanCount"] += 1
        tags[f"FRK_{N}_ResetRequest"] = 1 if reset else 0
        for number in range(1, len(APP.modules) + 1):
            self.ctx(number).update(OutImm_Reason=0, OutImm_IoRoles=0)
        if reset:
            self.unit.update(Error=0, ErrorID=0, ErrorSource=0)
        if error is not None:
            self.unit.update(Error=int(error), ErrorID=reason if error else 0,
                             ErrorSource=source if error else 0)
            if error and 1 <= source <= len(APP.modules):
                self.ctx(source).update(OutImm_Reason=reason, OutImm_IoRoles=roles)
        if report is not None:
            code, origin = report
            self.unit.update(ReportedReason=code, ReportedSource=origin,
                             ReportedCount=self.unit["ReportedCount"] + 1)
            self.ctx(origin).update(OutImm_Reason=code, OutImm_IoRoles=roles)
        self.controller.run(self.program)
        self.now += datetime.timedelta(milliseconds=PERIOD)

    def open_slots(self):
        return [i for i, state in enumerate(self.log["ActState"]) if state]

    def fault_and_clear(self, reason=NOT_EXTENDED):
        self.scan(error=True, reason=reason)
        self.scan(error=False)


class Raising(unittest.TestCase):
    def test_error_entry_raises_one_manual_event(self):
        bench = Bench()
        bench.scan(error=True, reason=NOT_EXTENDED, source=2)
        log = bench.log
        self.assertEqual(bench.open_slots(), [0])
        self.assertEqual(log["ActState"][0], gen.ALARM_OPEN)
        self.assertEqual(log["ActReasonCode"][0], NOT_EXTENDED)
        self.assertEqual(log["ActResetClass"][0], gen.RESET_MANUAL)
        # ErrorSource 2 is the second declared module; ModuleId 1 is the root
        self.assertEqual(log["ActSourceModuleId"][0], 3)
        self.assertEqual((log["NActive"], log["FaultEvt"], log["Blocking"]),
                         (1, 1, 1))

    def test_staying_in_error_raises_nothing_more(self):
        bench = Bench()
        for _ in range(5):
            bench.scan(error=True)
        self.assertEqual(bench.open_slots(), [0])
        self.assertEqual(bench.log["NActive"], 1)

    def test_severity_follows_the_rationalization_and_fails_closed(self):
        by_name = {name: code for name, code in APP.reasons.items()}
        for name in ("TWO_HAND_RELEASED", "CYL_NOT_EXTENDED", "STEP_STALLED"):
            bench = Bench()
            bench.scan(error=True, reason=by_name[name])
            self.assertEqual(bench.log["ActSeverity"][0], gen.reason_priority(APP, name), name)
        bench = Bench()
        bench.scan(error=True, reason=4242)      # registered nowhere
        self.assertEqual(bench.log["ActSeverity"][0], HIGH)

    def test_the_come_stamp_is_the_controller_clock(self):
        """The clock starts at 999,600 us: a rounding division would carry it
        into a thousandth millisecond, which is no time at all."""
        bench = Bench()
        bench.scan(error=True)
        self.assertEqual(bench.log["ActComeDate"][0], 20260929)
        self.assertEqual(bench.log["ActComeTime"][0], 235959999)
        self.assertEqual(bench.log["ActComeScan"][0], 1)


class Clearing(unittest.TestCase):
    def test_error_exit_leaves_a_manual_event_waiting_and_blocking(self):
        bench = Bench()
        bench.scan(error=True)
        for _ in range(4):
            bench.scan()
        bench.scan(error=False)
        log = bench.log
        self.assertEqual(log["ActState"][0], gen.ALARM_WAIT_RESET)
        self.assertEqual(log["ActDurationMs"][0], 5 * PERIOD)
        self.assertNotEqual(log["ActGoneTime"][0], 0)
        self.assertEqual((log["FaultEvt"], log["Blocking"], log["NActive"]), (0, 1, 1))

    def test_a_reset_closes_it_into_the_ring(self):
        bench = Bench()
        bench.scan(error=True, reason=NOT_RETRACTED, source=1)
        bench.scan(error=False)
        bench.scan(reset=True)
        log, ring = bench.log, bench.ring
        self.assertEqual(bench.open_slots(), [])
        self.assertEqual((log["NActive"], log["Blocking"], log["RingHead"]), (0, 0, 1))
        self.assertEqual(ring["RingState"][0], gen.ALARM_CLOSED)
        self.assertEqual(ring["RingReasonCode"][0], NOT_RETRACTED)
        self.assertEqual(ring["RingSourceModuleId"][0], 2)
        self.assertEqual(ring["RingDurationMs"][0], PERIOD)

    def test_a_reset_in_error_closes_and_records_in_one_scan(self):
        """The Unit clears Error in the reset scan, before the log runs: gone
        and closed happen together, and the ring entry still has a gone time."""
        bench = Bench()
        bench.scan(error=True)
        bench.scan(reset=True)
        self.assertEqual(bench.open_slots(), [])
        self.assertEqual(bench.log["RingHead"], 1)
        self.assertNotEqual(bench.ring["RingGoneTime"][0], 0)

    def test_a_reset_closes_an_active_manual_event_and_a_live_cause_reraises(self):
        """TC3 §76: the reset closes the event even while the cause holds;
        the cause, still there, is a NEW event on the next scan."""
        bench = Bench()
        bench.scan(error=True, reason=NOT_EXTENDED)
        # the rollup re-adopts the fault in the reset scan itself
        bench.scan(reset=True, error=True, reason=NOT_EXTENDED)
        self.assertEqual(bench.log["RingHead"], 1)
        self.assertNotEqual(bench.ring["RingGoneTime"][0], 0)
        bench.scan(error=True, reason=NOT_EXTENDED)
        self.assertEqual(bench.open_slots(), [0])
        self.assertEqual(bench.log["ActComeScan"][0], 3)
        self.assertEqual(bench.log["Blocking"], 1)

    def test_a_reset_with_nothing_logged_changes_nothing(self):
        bench = Bench()
        bench.scan(reset=True)
        self.assertEqual((bench.log["RingHead"], bench.log["NActive"]), (0, 0))


class Capacity(unittest.TestCase):
    def test_simultaneous_fault_and_health_events_keep_identity_across_reset_and_reuse(self):
        bench = Bench()
        health = bench.controller.tags[gen.system_health_tag(APP)]
        health['Bad'] = [1] * len(gen.HEALTH_EVENTS)
        bench.scan(error=True, reason=NOT_EXTENDED, source=2)
        slots = bench.open_slots()
        self.assertEqual(len(slots), 1 + len(gen.HEALTH_EVENTS))
        self.assertEqual(bench.log['ActSourceModuleId'][0], 3)
        self.assertEqual(bench.log['ActReasonCode'][0], NOT_EXTENDED)
        self.assertEqual(bench.log['HealthEvt'], list(range(2, 2 + len(gen.HEALTH_EVENTS))))
        bench.scan(reset=True)
        self.assertEqual(bench.log['NActive'], len(gen.HEALTH_EVENTS))
        self.assertEqual(bench.log['RingHead'], 1)
        health['Bad'] = [0] * len(gen.HEALTH_EVENTS)
        bench.scan(error=True, reason=NOT_RETRACTED, source=1)
        self.assertEqual(bench.log['FaultEvt'], 1)
        self.assertEqual(bench.log['NActive'], 1)
        self.assertEqual(bench.log['ActReasonCode'][0], NOT_RETRACTED)
        self.assertEqual(bench.log['RingHead'], 1 + len(gen.HEALTH_EVENTS))
        self.assertEqual(bench.ring['RingReasonCode'][:1 + len(gen.HEALTH_EVENTS)],
                         [NOT_EXTENDED] + [R[n] for n in gen.HEALTH_EVENTS])
        self.assertEqual(bench.log['HealthEvt'], [0] * len(gen.HEALTH_EVENTS))

    def test_a_full_list_is_said_and_nothing_is_overwritten(self):
        bench = Bench()
        for n in range(gen.ALARM_ACTIVE):
            bench.fault_and_clear(reason=7000 + n)
        before = list(bench.log["ActReasonCode"])
        bench.scan(error=True, reason=9999)
        log = bench.log
        self.assertEqual(log["Truncated"], 1)
        self.assertEqual(log["ActReasonCode"], before)
        self.assertEqual((log["NActive"], log["FaultEvt"]), (gen.ALARM_ACTIVE, 0))
        # a reset frees the list; the cause, still live, is then recorded
        bench.scan(reset=True, error=True, reason=9999)
        bench.scan(error=True, reason=9999)
        self.assertEqual(bench.log["RingHead"], gen.ALARM_ACTIVE)
        self.assertEqual(bench.log["ActReasonCode"][0], 9999)

    def test_the_ring_wraps_without_a_fault(self):
        bench = Bench()
        for n in range(gen.ALARM_RING + 1):
            bench.scan(error=True, reason=7000 + n)
            bench.scan(reset=True)
        ring = bench.ring
        self.assertEqual(bench.log["RingHead"], 1)
        self.assertEqual(ring["RingReasonCode"][0], 7000 + gen.ALARM_RING)
        self.assertEqual(ring["RingReasonCode"][1], 7001)
        self.assertEqual(ring["RingReasonCode"][gen.ALARM_RING - 1],
                         7000 + gen.ALARM_RING - 1)


class Published(unittest.TestCase):
    def test_what_the_controller_holds_is_what_the_client_reads(self):
        """The same tag values, through the projection, in the client's field
        set: the source path is named, the times are UTC ISO."""
        bench = Bench()
        bench.scan(error=True, reason=NOT_EXTENDED, source=1)
        bench.scan(reset=True)
        bench.scan(error=True, reason=NOT_RETRACTED, source=2)
        out = projection.alarm_log_status(APP, bench.log, bench.ring)
        self.assertEqual(out["AlarmLog/Active[1]/ReasonCode"], NOT_RETRACTED)
        self.assertEqual(out["AlarmLog/Active[1]/SourcePath"],
                         f"{N}.{APP.modules[1].name}")
        self.assertEqual(out["AlarmLog/Active[1]/Description"],
                         f"std.reason.{NOT_RETRACTED}")
        self.assertTrue(out["AlarmLog/Blocking"])
        self.assertEqual(out["AlarmLog/Ring[1]/ReasonCode"], NOT_EXTENDED)
        self.assertEqual(out["AlarmLog/Ring[1]/SourcePath"],
                         f"{N}.{APP.modules[0].name}")
        self.assertEqual(out["AlarmLog/Ring[1]/ComeAt"], "2026-09-29T23:59:59.999Z")
        self.assertEqual(out["AlarmLog/Ring[1]/GoneAt"], "2026-09-30T00:00:00.009Z")


class Reports(unittest.TestCase):
    """§6.9(e), TC3's M_SequenceWarn: an occurrence, AUTO_RESET come+gone."""

    def test_a_report_is_a_closed_ring_entry_that_never_blocks(self):
        bench = Bench()
        bench.scan(report=(NOT_EXTENDED, 1))
        log, ring = bench.log, bench.ring
        self.assertEqual((log["RingHead"], log["NActive"], log["Blocking"]), (1, 0, 0))
        self.assertEqual(ring["RingState"][0], gen.ALARM_CLOSED)
        self.assertEqual(ring["RingResetClass"][0], gen.RESET_AUTO)
        self.assertEqual(ring["RingReasonCode"][0], NOT_EXTENDED)
        self.assertEqual(ring["RingSourceModuleId"][0], 2)
        self.assertEqual(ring["RingComeTime"][0], ring["RingGoneTime"][0])
        self.assertNotEqual(ring["RingComeTime"][0], 0)

    def test_a_report_keeps_the_io_its_child_implicated(self):
        bench = Bench()
        bench.scan(report=(NOT_RETRACTED, 3), roles=2)
        self.assertEqual(bench.ring["RingIoRoles"][0], 2)

    def test_each_report_is_logged_once(self):
        bench = Bench()
        bench.scan(report=(NOT_EXTENDED, 1))
        for _ in range(3):
            bench.scan()
        self.assertEqual(bench.log["RingHead"], 1)
        bench.scan(report=(NOT_RETRACTED, 2))
        self.assertEqual(bench.log["RingHead"], 2)

    def test_a_report_is_not_the_units_diagnostic(self):
        """The defect this replaces: ReportedReason is never cleared, so one
        report used to become the Unit's published diagnostic for good."""
        bench = Bench()
        bench.scan(report=(NOT_EXTENDED, 1))
        bench.scan()
        self.assertEqual(bench.unit["DiagReason"], 0)


class UnitDiagnostic(unittest.TestCase):
    def test_an_adopted_fault_is_the_diagnostic_with_the_childs_io(self):
        bench = Bench()
        bench.scan(error=True, reason=NOT_RETRACTED, source=3, roles=2)
        unit = bench.unit
        self.assertEqual((unit["DiagReason"], unit["DiagIoRoles"]), (NOT_RETRACTED, 2))
        self.assertEqual(unit["DiagSinceDate"], 20260929)
        self.assertEqual(bench.log["ActIoRoles"][0], 2)

    def test_every_module_arm_captures_its_own_io(self):
        """One CASE arm per module; each must copy that module's roles, into
        the Unit's diagnostic, the alarm and a report alike."""
        for source in range(1, len(APP.modules) + 1):
            for roles in (1, 2):
                bench = Bench()
                bench.scan(error=True, reason=NOT_RETRACTED, source=source, roles=roles)
                self.assertEqual(bench.log["ActIoRoles"][0], roles, source)
                self.assertEqual(bench.unit["DiagIoRoles"], roles, source)
                bench = Bench()
                bench.scan(report=(NOT_RETRACTED, source), roles=roles)
                self.assertEqual(bench.ring["RingIoRoles"][0], roles, source)

    def test_the_io_survives_the_child_clearing(self):
        """The chain drops the child's Execute, which clears its roles on the
        next scan. The Unit's copy, like TC3's verbatim diagnostic, stays."""
        bench = Bench()
        bench.scan(error=True, reason=NOT_RETRACTED, source=3, roles=2)
        for _ in range(3):
            bench.scan()
        self.assertEqual(bench.unit["DiagIoRoles"], 2)
        self.assertEqual(bench.ctx(3)["OutImm_IoRoles"], 0)

    def test_since_is_the_onset_not_the_latest_scan(self):
        bench = Bench()
        bench.scan(error=True)
        since = bench.unit["DiagSinceTime"]
        for _ in range(5):
            bench.scan()
        self.assertEqual(bench.unit["DiagSinceTime"], since)

    def test_a_module_reason_is_stamped_when_it_changes(self):
        bench = Bench()
        bench.ctx(2).update(OutImm_Reason=INTERLOCK)
        bench.controller.run(bench.program)
        first = bench.ctx(2)["DiagSinceTime"]
        self.assertEqual(bench.ctx(2)["DiagStamped"], INTERLOCK)
        bench.now = bench.now.replace(second=1)
        bench.controller.run(bench.program)
        self.assertEqual(bench.ctx(2)["DiagSinceTime"], first)


class StallWatchdog(unittest.TestCase):
    """Core §6.9, TC3's _tStall: a step that runs unheld past StallTime is a
    stall - a LOW pending STEP_STALLED, never a fault - and a held child is a
    declared wait that disarms it. A step that states an expected time (TC3's
    ExpectedTime; a delay's duration) is timed against that instead."""

    def running(self, stall_ms=100, step=150):
        bench = Bench()
        bench.unit.update(Running=1, Step=step, StallTimeMs=stall_ms)
        return bench

    def test_the_default_is_tc3s(self):
        self.assertEqual(Bench().unit["StallTimeMs"], 30000)

    def test_a_step_that_outruns_stall_time_is_timed_out_and_stalled(self):
        bench = self.running(stall_ms=100)
        for _ in range(10):         # the first scan only starts the clock
            bench.scan()
        self.assertEqual(bench.unit["StepTimedOut"], 0)
        bench.scan()
        self.assertEqual(bench.unit["StepTimedOut"], 1)
        self.assertEqual(bench.unit["DiagReason"], R["STEP_STALLED"])

    def test_a_step_change_restarts_the_clock(self):
        bench = self.running(stall_ms=100)
        for _ in range(8):
            bench.scan()
        bench.unit["Step"] = 170
        for _ in range(8):
            bench.scan()
        self.assertEqual(bench.unit["StepTimedOut"], 0)

    def dwelling(self, step=220):
        bench = Bench()
        auto = next(c for c in APP.chains if c.name == "AUTO")
        bench.unit.update(Running=1, Step=step, Mode=auto.mode_ordinal)
        return bench

    def test_a_step_with_an_expected_time_is_timed_against_it(self):
        """N220 is expected to take the dwell, 300 ms. Run exactly that and it
        is not stalled - it finishes on the next scan; one scan more and it
        is, long before StallTime."""
        bench = self.dwelling()
        dwell = bench.controller.tags[f"{APP.records[0].name}Tag"]["PressDwellMs"]
        for _ in range(dwell // PERIOD + 1):    # the first scan starts the clock
            bench.scan()
        self.assertEqual(bench.unit["StepExpectedMs"], dwell)
        self.assertEqual((bench.unit["StallMs"], bench.unit["StepTimedOut"]), (dwell, 0))
        bench.scan()
        self.assertEqual(bench.unit["StepTimedOut"], 1)
        self.assertEqual(bench.unit["DiagReason"], R["STEP_STALLED"])

    def test_the_expectation_is_the_live_recipe_value(self):
        bench = self.dwelling()
        bench.controller.tags[f"{APP.records[0].name}Tag"]["PressDwellMs"] = 1000
        for _ in range(60):
            bench.scan()
        self.assertEqual((bench.unit["StepExpectedMs"], bench.unit["StepTimedOut"]),
                         (1000, 0))

    def test_a_step_without_one_is_timed_against_stall_time(self):
        bench = self.dwelling(step=200)
        bench.unit["StallTimeMs"] = 100
        for _ in range(11):
            bench.scan()
        self.assertEqual((bench.unit["StepExpectedMs"], bench.unit["StepTimedOut"]),
                         (0, 1))

    def test_the_same_number_in_another_mode_expects_nothing(self):
        bench = self.dwelling()
        bench.unit["Mode"] = APP.manual_mode
        for _ in range(40):
            bench.scan()
        self.assertEqual((bench.unit["StepExpectedMs"], bench.unit["StepTimedOut"]),
                         (0, 0))

    def test_a_held_child_still_disarms_an_expected_time(self):
        bench = self.dwelling()
        for _ in range(60):
            bench.scan()
            bench.ctx(2).update(OutImm_Held=1, OutImm_Reason=INTERLOCK)
            bench.controller.run(bench.program)
        self.assertEqual((bench.unit["StallMs"], bench.unit["StepTimedOut"]), (0, 0))

    def test_a_held_child_rolls_up_and_disarms_it(self):
        """TC3's _M_RollupHold: the first held child's reason is the Unit's,
        so a held cylinder no longer leaves the press saying nothing."""
        bench = self.running(stall_ms=50)
        for _ in range(20):
            bench.scan()
            bench.ctx(2).update(OutImm_Held=1, OutImm_Reason=INTERLOCK)
            bench.controller.run(bench.program)
        self.assertEqual(bench.unit["DiagReason"], INTERLOCK)
        self.assertEqual(bench.unit["StepTimedOut"], 0)

    def test_an_adopted_fault_outranks_a_held_child(self):
        bench = self.running()
        bench.ctx(2).update(OutImm_Held=1, OutImm_Reason=INTERLOCK)
        bench.scan(error=True, reason=NOT_EXTENDED, source=3)
        bench.ctx(2).update(OutImm_Held=1, OutImm_Reason=INTERLOCK)
        bench.controller.run(bench.program)
        self.assertEqual(bench.unit["DiagReason"], NOT_EXTENDED)

    def test_a_stopped_chain_does_not_stall(self):
        bench = self.running(stall_ms=50)
        bench.unit["Running"] = 0
        for _ in range(20):
            bench.scan()
        self.assertEqual((bench.unit["StepTimedOut"], bench.unit["DiagReason"]), (0, 0))


class StartIsRefusedWhileBlocking(unittest.TestCase):
    def test_the_start_branch_consults_blocking_first(self):
        """§8.3(b): an unreset manual event refuses Start. The refusal is the
        mailbox's, so the operator is told why rather than seeing nothing."""
        import fraktal_ab_mailbox as mailbox

        text = "\n".join(mailbox.handler_logic(APP))
        guard = f"IF NOT {gen.start_predicate(APP)} THEN"
        self.assertIn(guard, text)
        after = text[text.index(guard):]
        refusal = after[:after.index("ELSE")]
        self.assertNotIn("RunRequest := 1", refusal)
        self.assertIn("RunRequest := 1", after[after.index("ELSE"):][:400])


class GeneratedStIsModeled(unittest.TestCase):
    def test_every_generated_routine_is_in_the_modeled_subset(self):
        """If the generator emits a construct the model cannot read, the model
        must be extended before anything is claimed about that routine."""
        import fraktal_ab_library as library
        import fraktal_ab_mailbox as mailbox

        st.parse("\n".join(gen.routine_logic(APP)))
        st.parse("\n".join(mailbox.handler_logic(APP)))
        for mtype in library.types_used(APP):
            st.parse("\n".join(gen.type_logic(mtype)))

    def test_the_log_runs_after_the_chain_renditions(self):
        """So a fault a chain adopts is logged in the scan it is adopted,
        while the child still holds its reason and implicated I/O."""
        routine = list(gen.routine_logic(APP))
        first_jsr = min(i for i, line in enumerate(routine)
                        if line.startswith("JSR("))
        log = routine.index(
            "(* Core 8.3 alarm log: fault capture, as TC3's FB_UnitBase *)")
        self.assertGreater(log, first_jsr)


if __name__ == "__main__":
    unittest.main()

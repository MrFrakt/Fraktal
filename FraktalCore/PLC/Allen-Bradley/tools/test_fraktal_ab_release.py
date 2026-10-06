"""TC3's Core §7.8 release reports on the Allen-Bradley binding.

A blocked control never silently no-ops: the HMI asks why, and the PLC answers
with the FULL list - every unmet precondition at once, each with its text, its
reason, its kind and the module that owns it. TC3 has three queries
(ReleaseReportStart, ReleaseReportManual, ReleaseReportAction), and its Start
consumes ReleaseReportStart itself, so the rule and its explanation cannot
drift.

AB computes the start report every scan, and a START, a physical two-hand start
and the HMI's query all read that one result. The manual report is built on
request from the same tests MANUAL_COMMAND gates on, plus the direction's
permit the module would hold on. These tests run the generated mailbox, module
layer and routine on the ST model (the bench of test_fraktal_ab_manual).
"""

import unittest

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
from test_fraktal_ab_core_ordinals import core_enum
from test_fraktal_ab_manual import (AIR, APP, EXTEND, RETRACT, Bench, N, ORDINAL,
                                    UNIT, key)


KIND = gen.RELEASE_KINDS
AUTO = 0


def listed(bench):
    """The answer's report, as (text, reason, owner, kind) rows."""
    report = bench.tags[gen.release_report_tag(APP)]
    return [(report["Key"][i], report["Reason"][i], report["Source"][i], report["Kind"][i])
            for i in range(report["Count"])]


def released(bench):
    return bench.tags[gen.release_report_tag(APP)]["Released"]


class TheContract(unittest.TestCase):
    def test_one_start_report_body_serves_cyclic_and_requested_checks(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(gen.programs(APP))
        helpers = [r for r in root.findall('.//Routine') if r.get('Name') == gen.start_release_routine_name(APP)]
        self.assertEqual(len(helpers), 1)
        marker = f'{gen.start_release_tag(APP)}.Count := 0;'
        self.assertIn(marker, '\n'.join(n.text or '' for n in helpers[0].findall('.//Line')))
        main, handler = '\n'.join(gen.routine_logic(APP)), '\n'.join(mailbox.handler_logic(APP))
        call = f'JSR({gen.start_release_routine_name(APP)},0);'
        self.assertEqual(main.count(call), 1)
        self.assertEqual(handler.count(call), 2)  # START and RELEASE_START each recheck
        self.assertNotIn(marker, main + handler)

    def test_release_kinds_are_tc3s(self):
        self.assertEqual(KIND, core_enum("E_ReleaseKind"))

    def test_the_report_holds_everything_the_press_can_list(self):
        """Start: manual, not ready, alarm, and each start permit. Manual: mode,
        catalogue, busy and one permit."""
        start = 3 + len(APP.start_permits)
        self.assertLessEqual(max(start, 4), gen.RELEASE_CAPACITY)

    def test_start_reads_the_report(self):
        self.assertEqual(gen.start_predicate(APP),
                         f"({gen.start_release_tag(APP)}.Released <> 0)")


class StartReport(unittest.TestCase):
    def test_ready_in_auto_is_released_and_starts(self):
        bench = Bench(mode=AUTO)
        self.assertEqual(bench.request(mailbox.RELEASE_START), (1, 0))
        self.assertEqual((released(bench), listed(bench)), (1, []))
        self.assertEqual(bench.request(mailbox.START), (1, 0))
        self.assertEqual(bench.tags[f"FRK_{N}_RunRequest"], 1)

    def test_manual_has_nothing_to_start(self):
        bench = Bench()
        bench.request(mailbox.RELEASE_START)
        self.assertEqual(listed(bench), [(key(mailbox.MANUAL_HAS_NO_SEQUENCE_KEY), 0, 0,
                                          KIND["MODE"])])

    def test_air_is_a_start_permit(self):
        """TC3's ModeStart: PERMISSIVE_NOT_MET under airPressureOk, owned by
        the Unit - and START is refused with the same reason."""
        bench = Bench(mode=AUTO)
        bench.tags[AIR] = 0
        bench.scan(2)
        bench.request(mailbox.RELEASE_START)
        reason = (key("project.condition.airPressureOk"),
                  demo.REASONS["PERMISSIVE_NOT_MET"], 0, KIND["INTERLOCK"])
        self.assertEqual(listed(bench), [reason])
        self.assertEqual(bench.request(mailbox.START), (0, reason[0]))
        self.assertEqual(listed(bench), [reason], "START answers with the report")
        bench.tags[AIR] = 1
        bench.scan(2)
        self.assertEqual(bench.request(mailbox.START), (1, 0))

    def test_every_reason_at_once(self):
        """A faulted Unit with an unreset alarm and no air: three reasons,
        in TC3's order, and the refusal names the first."""
        bench = Bench(mode=AUTO)
        bench.unit["Error"] = 1
        bench.tags[gen.alarm_active_tag(APP)]["Blocking"] = 1
        bench.tags[AIR] = 0
        bench.scan(2)
        answer = bench.request(mailbox.START)
        self.assertEqual([r[0] for r in listed(bench)],
                         [key(gen.UNIT_NOT_READY_KEY), key(gen.MANUAL_RESET_KEY),
                          key("project.condition.airPressureOk")])
        self.assertEqual([r[3] for r in listed(bench)],
                         [KIND["MODE"], KIND["ALARM"], KIND["INTERLOCK"]])
        self.assertEqual(answer, (0, key(gen.UNIT_NOT_READY_KEY)))

    def test_an_aborted_unit_is_not_ready(self):
        """It used to take the START and then not run - a dead button."""
        bench = Bench(mode=AUTO)
        bench.unit["Aborted"] = 1
        bench.scan()
        self.assertEqual(bench.request(mailbox.START), (0, key(gen.UNIT_NOT_READY_KEY)))
        self.assertEqual(bench.tags[f"FRK_{N}_RunRequest"], 0)


class AResetDoesNotRestart(unittest.TestCase):
    """TC3's OperatorReset releases its own run command: a reset leaves the
    machine restartable, never restarted. Found on press42."""

    def test_a_reset_after_a_fault_leaves_the_press_stopped(self):
        bench = Bench(mode=AUTO)
        self.assertEqual(bench.request(mailbox.START), (1, 0))
        bench.scan()
        self.assertEqual(bench.unit["Running"], 1)
        bench.unit.update(Error=1, ErrorID=demo.REASONS["CYL_NOT_EXTENDED"], Running=0)
        bench.scan(2)
        self.assertEqual(bench.unit["Running"], 0, "a fault stops it")
        self.assertEqual(bench.request(mailbox.OPERATOR_RESET), (1, 0))
        bench.scan(3)
        self.assertEqual((bench.unit["Error"], bench.unit["Running"]), (0, 0),
                         "the reset cleared the fault and did not start it")
        self.assertEqual(bench.request(mailbox.START), (1, 0), "START is the way on")
        bench.scan()
        self.assertEqual(bench.unit["Running"], 1)


class ManualReport(unittest.TestCase):
    def ask(self, bench, module, value):
        accepted = bench.request(mailbox.RELEASE_MANUAL, f"{N}.{module}", value)
        self.assertEqual(accepted, (1, 0), "a query is always answered")
        return listed(bench)

    def test_a_permitted_command_is_released(self):
        bench = Bench()
        self.assertEqual(self.ask(bench, "Door", RETRACT), [])
        self.assertEqual(released(bench), 1)

    def test_a_blocked_direction_names_its_permit_and_its_module(self):
        bench = Bench()
        self.assertEqual(self.ask(bench, "Door", EXTEND), [(
            key("project.interlock.doorCloseRequiresSlideInside"),
            demo.REASONS["INTERLOCK_DROPPED"], ORDINAL["Door"], KIND["INTERLOCK"])])

    def test_the_ram_names_only_its_first_missing_permit(self):
        bench = Bench()
        self.assertEqual([r[0] for r in self.ask(bench, "PressRam", EXTEND)],
                         [key("project.interlock.pressRequiresGuardClosed")])

    def test_outside_manual_the_mode_comes_first(self):
        bench = Bench(mode=AUTO)
        self.assertEqual([(r[0], r[3]) for r in self.ask(bench, "Door", EXTEND)], [
            (key(mailbox.MANUAL_MODE_REQUIRED_KEY), KIND["MODE"]),
            (key("project.interlock.doorCloseRequiresSlideInside"), KIND["INTERLOCK"])])

    def test_the_gates_refusals_are_listed(self):
        bench = Bench()
        self.assertEqual(self.ask(bench, "TwoHand", 1), [(
            key(mailbox.TARGET_KEY), demo.REASONS["UNSUPPORTED_COMMAND"], 0, KIND["OTHER"])])
        self.assertEqual([r[0] for r in self.ask(bench, "Door", 3)],
                         [key(mailbox.MANUAL_COMMAND_UNKNOWN_KEY)])
        bench.request(mailbox.MANUAL_COMMAND, f"{N}.Door", EXTEND)   # held
        bench.scan(3)
        self.assertEqual([(r[0], r[2]) for r in self.ask(bench, "Door", EXTEND)], [
            (key(mailbox.MANUAL_BUSY_KEY), ORDINAL["Door"]),
            (key("project.interlock.doorCloseRequiresSlideInside"), ORDINAL["Door"])])

    def test_it_explains_exactly_what_the_gate_refuses(self):
        """No drift: every refusal MANUAL_COMMAND gives is the first entry of
        the report for the same request."""
        for mode, module, value in ((AUTO, "Door", RETRACT), (None, "TwoHand", 1),
                                    (None, "Door", 3)):
            bench = Bench(mode=mode)
            report = self.ask(bench, module, value)
            answer = bench.request(mailbox.MANUAL_COMMAND, f"{N}.{module}", value)
            self.assertEqual(answer, (0, report[0][0]), (mode, module, value))


class ActionReport(unittest.TestCase):
    def test_a_reset_with_nothing_to_reset(self):
        bench = Bench()
        bench.request(mailbox.RELEASE_ACTION, value=gen.GATED_ALARM_RESET)
        self.assertEqual(listed(bench), [(key(gen.NO_BLOCKING_ALARM_KEY), 0, 0, KIND["OTHER"])])
        bench.tags[gen.alarm_active_tag(APP)]["Blocking"] = 1
        bench.request(mailbox.RELEASE_ACTION, value=gen.GATED_ALARM_RESET)
        self.assertEqual((released(bench), listed(bench)), (1, []))

    def test_the_other_gates_have_nothing_to_explain_here(self):
        bench = Bench()
        for gate in range(12):
            if gate == gen.GATED_ALARM_RESET:
                continue
            bench.request(mailbox.RELEASE_ACTION, value=gate)
            self.assertEqual((released(bench), listed(bench)), (1, []), gate)


class ThePublishedReport(unittest.TestCase):
    def publish(self, bench):
        catalogue = {v: k for k, v in gen.localization_numbers(APP).items()}
        return projection.release_report_values(
            APP, bench.tags[gen.release_report_tag(APP)], catalogue)

    def test_tc3s_24_slots_in_tf6100s_naming(self):
        """The HMI re-reads exactly these paths after an acknowledgement and
        refuses the whole read if one is missing."""
        out = self.publish(Bench())
        for slot in range(1, 25):
            for leaf in ("Description", "ReasonCode", "SourcePath", "Kind", "Bypassable"):
                self.assertIn(f"HmiResponse/Report/Reasons/Reasons[{slot}]/{leaf}", out)

    def test_a_reason_is_named_and_owned(self):
        bench = Bench(mode=AUTO)
        bench.request(mailbox.RELEASE_MANUAL, f"{N}.Door", EXTEND)
        out = self.publish(bench)
        base = "HmiResponse/Report/Reasons/Reasons"
        self.assertEqual((out["HmiResponse/Report/Released"], out["HmiResponse/Report/Count"]),
                         (False, 2))
        self.assertEqual((out[f"{base}[1]/Description"], out[f"{base}[1]/SourcePath"]),
                         (mailbox.MANUAL_MODE_REQUIRED_KEY, APP.name))
        self.assertEqual((out[f"{base}[2]/Description"], out[f"{base}[2]/SourcePath"],
                          out[f"{base}[2]/ReasonCode"], out[f"{base}[2]/Bypassable"]),
                         ("project.interlock.doorCloseRequiresSlideInside", f"{N}.Door",
                          demo.REASONS["INTERLOCK_DROPPED"], False))
        self.assertEqual(out[f"{base}[3]/Description"], "", "empty past Count")

    def test_the_gateway_resolves_the_manual_query_target(self):
        root = f"{N}/HmiRequest"
        writes = [(f"{root}/Kind", "int32", mailbox.RELEASE_MANUAL),
                  (f"{root}/TargetPath", "string", f"{N}.PressRam"),
                  (f"{root}/Sequence", "int32", 3)]
        self.assertIn((f"{root}/{mailbox.MANUAL_TARGET_MEMBER}", "int32", ORDINAL["PressRam"]),
                      mailbox.resolve_batch(APP, writes))


if __name__ == "__main__":
    unittest.main()

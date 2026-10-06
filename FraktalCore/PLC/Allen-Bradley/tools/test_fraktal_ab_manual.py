"""TC3's manual commands and directional interlocks on the Allen-Bradley binding.

TC3's MANUAL mode has no sequence. Each module publishes a command catalogue
(`_M_PublishCommand`), and `ManualCommandTo(TargetPath, Value)` accepts a
command only in MANUAL, routing it through the module's own handshake - so a
command into a blocked direction HOLDS on INTERLOCK_DROPPED, exactly as it would
in AUTO. The press's collision interlocks are `SetDirectionalPermits`: the door
closes only over a slide that is inside, the slide moves only with the door
open, and the ram presses only with air, the guard closed, the slide inside,
both healthy and the two-hand held - named first-out, in that order.

AB had a one-module jog chain instead, swapped cylinder ordinals, no catalogue
and no permits. These tests run the generated mailbox handler, the routine's
module layer and the mode owner's manual logic, in routine order, on the ST
model.
"""

import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st


APP = demo.application()
N = APP.name
UNIT, SCAN = f"FRK_{N}_Unit", f"FRK_{N}_ScanCount"
PART, AIR, TWO_HAND = f"FRK_{N}_PartPresent", f"FRK_{N}_AirOk", f"FRK_{N}_TwoHand"
REQUEST, RESPONSE = mailbox.request_tag_name(APP), mailbox.response_tag_name(APP)
ORDINAL = {m.name: i for i, m in enumerate(APP.modules, start=1)}
EXTEND, RETRACT = 1, 2
HELD = demo.REASONS["INTERLOCK_DROPPED"]


def key(portable):
    return manifest.numeric_key(APP, portable)


def string(length):
    return {"LEN": 0, "DATA": [0] * length}


class Bench:
    """The routine in order: mailbox, modules, then the mode owner's manual
    logic and its reset, abort and mode-change releases."""

    def __init__(self, mode=None):
        tags = {
            gen.config_persist_tag(APP): st.structure(gen.config_persist_members()),
            UNIT: st.structure(gen.unit_context_members(APP)),
            f"FRK_{N}_Chart": st.structure(gen.chart_members(APP)),
            **{f"{r.name}Tag": st.structure(r.members) for r in APP.records},
            SCAN: 0,
            REQUEST: {name: (string(length) if kind == mailbox.STRING_MEMBER else 0)
                      for name, kind, length, _ in mailbox.REQUEST_MEMBERS},
            RESPONSE: {name: 0 for name, *_ in mailbox.RESPONSE_MEMBERS},
            f"FRK_{N}_HmiLastSequence": 0,
            f"FRK_{N}_HmiWipe": 0,
            gen.start_release_tag(APP): st.structure(gen.release_report_members()),
            gen.release_report_tag(APP): st.structure(gen.release_report_members()),
            gen.release_index_tag(APP): 0,
            gen.alarm_active_tag(APP): st.structure(gen.alarm_active_members()),
            gen.oee_tag(APP): st.structure(gen.oee_members()),
        }
        if APP.line is not None:
            import fraktal_ab_line as line
            tags[line.tag(APP, 'Shift')] = st.structure(line.shift_members())
        for name in mailbox.one_shot_requests() + mailbox.LEVEL_REQUESTS:
            tags[f"FRK_{N}_{name}"] = 0
        for module in APP.modules:
            context = st.structure(gen.module_members(module))
            if "Par_TaskPeriodMs" in context:
                context["Par_TaskPeriodMs"] = APP.task_period_ms
            tags[gen.ctx_tag_for(APP, module.name)] = context
        for tag in APP.sim_inputs:
            tags[tag] = 0
        tags.update({PART: 1, AIR: 1, TWO_HAND: 1})
        self.tags = tags
        self.unit["Mode"] = APP.manual_mode if mode is None else mode
        self.unit["ModeRequest"] = self.unit["Mode"]
        tags[f"FRK_{N}_ModeRequest"] = self.unit["Mode"]     # a selection, held
        self.plc = st.Controller(tags)
        from test_fraktal_ab_access import add_access
        add_access(self.plc, APP)
        # The mode owner sees its children under its own parameter names.
        owner = {"Ctx": self.unit, "Chart": tags[f"FRK_{N}_Chart"],
                 **{f"Ctx{m.name}": tags[gen.ctx_tag_for(APP, m.name)]
                                      for m in APP.modules}}
        self.owner = st.Controller(owner)
        self.handler = st.parse("\n".join(mailbox.handler_logic(APP)))
        self.start_release = st.parse("\n".join(gen.start_release_logic(APP)))
        self.manual = st.parse("\n".join(gen.manual_logic(APP)))
        keys = gen.localization_numbers(APP)
        self.modules = []
        for module in sorted(APP.modules, key=lambda m: not library.type_of(m).passive):
            setup = [line for line in gen.module_setup_lines(APP, module, keys)
                     if "Request := FRK_" not in line]
            self.modules.append((gen.ctx_tag_for(APP, module.name), st.parse("\n".join(setup)),
                                 st.parse("\n".join(gen.type_logic(library.type_of(module))))))
        unit_logic = gen.unit_logic(APP)
        self.blocks = {opener: st.parse("\n".join(_block(unit_logic, opener)))
                       for opener in ("IF Ctx.ResetRequest <> 0 THEN",
                                      "IF Ctx.AbortRequest <> 0 THEN",
                                      "IF (Ctx.RunRequest <> 0) AND (Ctx.Error = 0) "
                                      "AND (Ctx.Aborted = 0)",
                                      "IF Ctx.RunRequest = 0 THEN",
                                      "IF Ctx.ModeRequest <> Ctx.Mode THEN")}
        self.sequence = 0
        # A controller has been scanning long before anyone asks: the start
        # report a request reads is the previous scan's.
        self.scan()

    @property
    def unit(self):
        return self.tags[UNIT]

    def ctx(self, name):
        return self.tags[gen.ctx_tag_for(APP, name)]

    def request(self, kind, target="", value=0):
        """Write a request as the gateway would - TargetPath resolved."""
        self.sequence += 1
        request = self.tags[REQUEST]
        request.update(Kind=kind, IntValue=value,
                       DurationMs=mailbox.manual_target(APP, target) if target else 0,
                       Sequence=self.sequence)
        self.scan()
        return self.tags[RESPONSE]["Accepted"], self.tags[RESPONSE]["DiagnosticKey"]

    def scan(self, count=1):
        for _ in range(count):
            self.tags[SCAN] += 1
            self.plc.run(self.handler)
            for ctx, setup, body in self.modules:
                self.plc.run(setup)
                st.Controller({"Ctx": self.tags[ctx], "Scan": self.tags[SCAN]}).run(body)
            self.plc.run(self.start_release)            # Core 7.8, after the modules
            # the mode owner: its request copies, then reset/abort/mode change
            self.unit.update(ResetRequest=self.tags[f"FRK_{N}_ResetRequest"],
                             AbortRequest=self.tags[f"FRK_{N}_AbortRequest"],
                             RunRequest=self.tags[f"FRK_{N}_RunRequest"],
                             ModeRequest=self.tags[f"FRK_{N}_ModeRequest"])
            for block in self.blocks.values():
                self.owner.run(block)
            self.owner.run(self.manual)

    def run(self, name, command, scans=20):
        accepted = self.request(mailbox.MANUAL_COMMAND, f"{N}.{name}", command)
        self.scan(scans)
        return accepted


def _block(lines, opener):
    lines = list(lines)
    start = lines.index(opener)
    depth = 0
    for end in range(start, len(lines)):
        line = lines[end]
        if line.startswith("IF "):
            depth += 1
        if line == "END_IF;":
            depth -= 1
            if depth == 0:
                return lines[start:end + 1]
    raise AssertionError(f"unterminated {opener}")


class TheContract(unittest.TestCase):
    def test_cylinder_ordinals_are_tc3s(self):
        """E_CylinderCommand: NONE 0, EXTEND 1, RETRACT 2 - a manual command
        carries the number, so it has to mean the same on both bindings."""
        for module in APP.modules:
            if library.type_of(module) is library.CYLINDER:
                self.assertEqual([(c.name, c.ordinal) for c in module.commands],
                                 [("EXTEND", EXTEND), ("RETRACT", RETRACT)])

    def test_manual_is_a_mode_without_a_chain(self):
        self.assertIsNotNone(APP.manual_mode)
        self.assertNotIn(APP.manual_mode, {c.mode_ordinal for c in APP.chains})
        self.assertIn(APP.manual_mode, decl.declared_modes(APP))
        self.assertNotIn(f"FRK_{N}_JogCommand", APP.sim_inputs)

    def test_each_cylinder_publishes_tc3s_catalogue(self):
        for module in APP.modules:
            out = projection.command_catalog(APP, module.name)
            if library.type_of(module) is library.CYLINDER:
                self.assertEqual(out, {
                    "CatalogCount": 2,
                    "Catalog[1]/Value": EXTEND, "Catalog[1]/Label": "std.command.extend",
                    "Catalog[1]/Style": 0,
                    "Catalog[2]/Value": RETRACT, "Catalog[2]/Label": "std.command.retract",
                    "Catalog[2]/Style": 0})
            else:
                self.assertEqual(out, {"CatalogCount": 0})

    def test_the_gateway_resolves_a_target_to_its_ordinal(self):
        self.assertEqual(mailbox.manual_target(APP, f"{N}.Door"), ORDINAL["Door"])
        self.assertEqual(mailbox.manual_target(APP, f"{N}.TwoHand"), 0,
                         "a module that takes no commands is not a target")
        self.assertEqual(mailbox.manual_target(APP, f"{N}.Nothing"), 0)
        root = f"{N}/HmiRequest"
        writes = [(f"{root}/Kind", "int32", mailbox.MANUAL_COMMAND),
                  (f"{root}/TargetPath", "string", f"{N}.PartSlide"),
                  (f"{root}/IntValue", "int32", EXTEND),
                  (f"{root}/Sequence", "int32", 7)]
        out = mailbox.resolve_batch(APP, writes)
        self.assertIn((f"{root}/{mailbox.MANUAL_TARGET_MEMBER}", "int32",
                       ORDINAL["PartSlide"]), out)
        self.assertEqual(out[-1][0], f"{root}/Sequence", "the commit stays last")


class ManualCommands(unittest.TestCase):
    def test_a_permitted_command_runs_and_releases(self):
        bench = Bench()
        self.assertEqual(bench.run("PartSlide", EXTEND), (1, 0))
        slide = bench.ctx("PartSlide")
        self.assertEqual((slide["OutImm_Pos"], slide["OutImm_Extended"]), (100, 1))
        self.assertEqual((slide["Execute"], slide["ManualCmd"], slide["DoneCount"]), (0, 0, 1))

    def test_a_command_after_a_fault_starts_afresh(self):
        """A manual command that faults keeps Execute up, so the module stays
        in ERROR where the operator sees it. The next command drops it first,
        so it starts on a fresh edge instead of inheriting the fault."""
        bench = Bench()
        bench.run("PartSlide", EXTEND)
        door = bench.ctx("Door")
        door["FaultRequest"] = 1                       # stuck: it times out
        bench.run("Door", EXTEND, scans=80)
        self.assertEqual((door["Error"], door["Execute"]), (1, 1))
        door["FaultRequest"] = 0
        self.assertEqual(bench.run("Door", EXTEND), (1, 0))
        self.assertEqual((door["Error"], door["OutImm_Pos"], door["ManualCmd"]), (0, 100, 0))

    def test_only_in_the_manual_mode(self):
        bench = Bench(mode=0)
        self.assertEqual(bench.run("PartSlide", EXTEND),
                         (0, key(mailbox.MANUAL_MODE_REQUIRED_KEY)))
        self.assertEqual(bench.ctx("PartSlide")["RunCount"], 0)

    def test_each_refusal_is_named(self):
        bench = Bench()
        self.assertEqual(bench.request(mailbox.MANUAL_COMMAND, f"{N}.TwoHand", 1),
                         (0, key(mailbox.TARGET_KEY)))
        self.assertEqual(bench.request(mailbox.MANUAL_COMMAND, f"{N}.Door", 3),
                         (0, key(mailbox.MANUAL_COMMAND_UNKNOWN_KEY)))
        bench.request(mailbox.MANUAL_COMMAND, f"{N}.Door", EXTEND)  # held: slide out
        bench.scan(3)
        self.assertEqual(bench.request(mailbox.MANUAL_COMMAND, f"{N}.Door", RETRACT),
                         (0, key(mailbox.MANUAL_BUSY_KEY)))

    def test_start_has_nothing_to_run_in_manual(self):
        bench = Bench()
        self.assertEqual(bench.request(mailbox.START),
                         (0, key(mailbox.MANUAL_HAS_NO_SEQUENCE_KEY)))
        self.assertEqual(bench.tags[f"FRK_{N}_RunRequest"], 0)


class DirectionalPermits(unittest.TestCase):
    def assertHeldOn(self, bench, name, portable):
        ctx = bench.ctx(name)
        self.assertEqual((ctx["Busy"], ctx["OutImm_Held"], ctx["OutImm_Reason"], ctx["Error"]),
                         (1, 1, HELD, 0))
        catalogue = {v: k for k, v in gen.localization_numbers(APP).items()}
        self.assertEqual(
            projection.module_status(ctx, APP, name, catalogue)["Status/Diagnostic/Description"],
            portable)

    def test_the_door_does_not_close_over_a_slide_outside(self):
        bench = Bench()
        bench.run("Door", EXTEND)
        self.assertEqual(bench.ctx("Door")["OutImm_Pos"], 0, "it did not move")
        self.assertHeldOn(bench, "Door", "project.interlock.doorCloseRequiresSlideInside")

    def test_the_area_interlock_is_named_before_a_permit(self):
        """TC3's PermIntlk orders SetAreaSafe's condition first: a door held
        for its slide that then loses air says air."""
        bench = Bench()
        bench.run("Door", EXTEND)
        self.assertHeldOn(bench, "Door", "project.interlock.doorCloseRequiresSlideInside")
        bench.tags[AIR] = 0
        bench.scan(3)
        self.assertHeldOn(bench, "Door", "project.interlock.pressRequiresAirPressure")

    def test_the_slide_does_not_move_under_a_closed_door_and_resumes_when_it_opens(self):
        bench = Bench()
        bench.run("PartSlide", EXTEND)
        bench.run("Door", EXTEND)
        self.assertEqual(bench.ctx("Door")["OutImm_Extended"], 1)
        bench.run("PartSlide", RETRACT, scans=10)
        self.assertHeldOn(bench, "PartSlide", "project.interlock.slideOutsideRequiresDoorOpen")
        self.assertEqual(bench.run("Door", RETRACT), (1, 0), "opening is always permitted")
        slide = bench.ctx("PartSlide")
        self.assertEqual((slide["OutImm_Pos"], slide["OutImm_Held"], slide["Error"]),
                         (0, 0, 0), "the held slide went out by itself, without a fault")

    def test_the_ram_names_the_first_missing_permit(self):
        bench = Bench()
        bench.run("PressRam", EXTEND)
        self.assertHeldOn(bench, "PressRam", "project.interlock.pressRequiresGuardClosed")
        bench.run("PartSlide", EXTEND)                    # still held; slide moves in
        bench.tags[AIR] = 0
        bench.scan(3)
        self.assertHeldOn(bench, "PressRam", "project.interlock.pressRequiresAirPressure")

    def test_the_ram_presses_with_everything_in_place(self):
        bench = Bench()
        bench.run("PartSlide", EXTEND)
        bench.run("Door", EXTEND)
        bench.tags[TWO_HAND] = 0
        bench.run("PressRam", EXTEND, scans=5)
        self.assertHeldOn(bench, "PressRam", "project.interlock.pressRequiresTwoHandHeld")
        bench.tags[TWO_HAND] = 1
        bench.scan(10)
        self.assertEqual(bench.ctx("PressRam")["OutImm_Pos"], 100)


class ReleasingAManualCommand(unittest.TestCase):
    """TC3's OperatorReset, abort and mode change release the commands the
    operator left: a held manual command is dropped, never resumed."""

    def held_door(self):
        bench = Bench()
        bench.run("Door", EXTEND, scans=5)
        self.assertEqual(bench.ctx("Door")["OutImm_Held"], 1)
        return bench

    def assertReleased(self, bench):
        door = bench.ctx("Door")
        self.assertEqual((door["Execute"], door["ManualCmd"], door["Busy"]), (0, 0, 0))

    def test_a_reset_releases_it(self):
        bench = self.held_door()
        bench.request(mailbox.OPERATOR_RESET)
        bench.scan(2)
        self.assertReleased(bench)

    def test_a_stop_releases_it(self):
        bench = self.held_door()
        bench.request(mailbox.STOP)
        bench.scan(2)
        self.assertReleased(bench)

    def test_a_mode_change_releases_it(self):
        bench = self.held_door()
        bench.request(mailbox.SET_MODE, value=0)
        bench.scan(2)
        self.assertReleased(bench)


class Validation(unittest.TestCase):
    def findings(self, **changes):
        import dataclasses

        door = next(m for m in APP.modules if m.name == "Door")
        bad = dataclasses.replace(door, **changes)
        app = dataclasses.replace(APP, modules=tuple(
            bad if m.name == "Door" else m for m in APP.modules))
        return decl.validate(app)

    def test_a_permit_names_a_command_the_module_has(self):
        permits = (("OPEN", (decl.Permit((AIR,), "project.interlock.x"),)),)
        self.assertTrue(any("does not have" in f for f in self.findings(permits=permits)))

    def test_a_permit_key_is_a_localization_key(self):
        permits = (("EXTEND", (decl.Permit((AIR,), "door closes"),)),)
        self.assertTrue(any("localization key" in f for f in self.findings(permits=permits)))

    def test_an_area_interlock_names_what_it_reports(self):
        self.assertTrue(any("area interlock" in f
                            for f in self.findings(area_safe_key="")))

    def test_the_manual_mode_runs_no_chain(self):
        import dataclasses

        app = dataclasses.replace(APP, manual_mode=0)
        self.assertTrue(any("manual mode" in f for f in decl.validate(app)))


if __name__ == "__main__":
    unittest.main()

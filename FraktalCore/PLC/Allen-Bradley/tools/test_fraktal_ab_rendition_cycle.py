"""Every rendition commands the plant the same way, over a whole AUTO cycle.

The parity harness compares how often each rendition entered each step. That
proved the three languages walk the same graph, and it could not see that the
SFC chart did not move the press. A commanding step's SFC transition read the
module's Done with no entry guard, and the SFC action never dropped Execute
when a command completed - so a module still Done from its previous command
(the door from N130, the ram from N110) satisfied the next step's transition
on its first scan. The SFC entered N180, N200 and N244 like ST did, and the
door never closed, the ram never pressed and the slide never went out. Found
on 2026-10-01 when TC3's N180 abandon needed the close to be commanded first.

So the comparison here is the plant's, not the graph's: one AUTO cycle per
rendition against the generated module layer, in routine order (passive
modules, then cylinders, then the chain), and every rendition must issue the
same commands, complete them, and drive the same motions as ST.
"""

import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_ld_model as ld
import fraktal_ab_library as library
import fraktal_ab_press_demo as demo
import fraktal_ab_st_model as st


# The capability variant: AUTO in ST, SFC and LD. The shipped press carries
# the ladder alone (press80); every rendition must still walk the same cycle.
from test_fraktal_ab_renditions import every_rendition
APP = every_rendition(demo.application())
N = APP.name
AUTO = next(c for c in APP.chains if c.name == "AUTO")
UNIT, CHART, SCAN = f"FRK_{N}_Unit", f"FRK_{N}_Chart", f"FRK_{N}_ScanCount"
PART, AIR, TWO_HAND = f"FRK_{N}_PartPresent", f"FRK_{N}_AirOk", f"FRK_{N}_TwoHand"
PROBE = "FRK_Test_Transition"
NAMES = gen.Names(APP, in_aoi=False)
ORDER = gen.ordered_steps(APP)
CYLINDERS = [m.name for m in APP.modules
             if library.type_of(m) is library.CYLINDER]


def controller():
    tags = {
        UNIT: st.structure(gen.unit_context_members(APP)),
        CHART: st.structure(gen.chart_members(APP)),
        **{f"{r.name}Tag": st.structure(r.members) for r in APP.records},
        SCAN: 0,
        f"FRK_{N}_ResetRequest": 0,
        gen.ld_advanced_tag(APP): 0,
        gen.ld_scratch_tag(APP): 0,
        PROBE: 0,
    }
    for module in APP.modules:
        context = st.structure(gen.module_members(module))
        if "Par_TaskPeriodMs" in context:          # the tag's declared value
            context["Par_TaskPeriodMs"] = APP.task_period_ms
        tags[gen.ctx_tag_for(APP, module.name)] = context
    for tag in APP.sim_inputs:
        tags[tag] = 0
    return st.Controller(tags, routines={gen.step_mark_routine_name(APP): gen.step_mark_logic(APP)})


class Press:
    """The routine, scan by scan: every module, then one AUTO rendition."""

    def __init__(self, language, start=100):
        self.language = language
        self.plc = controller()
        self.plc.tags.update({PART: 1, AIR: 1, TWO_HAND: 1})
        self.plc.tags[UNIT].update(Mode=AUTO.mode_ordinal, Running=1, Step=start,
                                   PrevStep=-1, StartLatched=1)
        self.modules = []
        keys = gen.localization_numbers(APP)
        for module in sorted(APP.modules,
                             key=lambda m: not library.type_of(m).passive):
            ctx = gen.ctx_tag_for(APP, module.name)
            # The routine's own module layer - feed, configuration, area
            # interlock and directional permits - minus the simulation
            # injections, which stay 0 here.
            setup = [line for line in gen.module_setup_lines(APP, module, keys)
                     if "Request := FRK_" not in line]
            self.modules.append((ctx, st.parse("\n".join(setup)),
                                 st.parse("\n".join(gen.type_logic(library.type_of(module))))))
        if language == decl.ST:
            self.logic = st.parse("\n".join(gen.chain_st_logic(APP, AUTO)))
        elif language == decl.LD:
            self.rungs = [ld.parse_rung(r) for r in gen.chain_ld_rungs(APP, AUTO)]
        else:
            self.active = start
            self.actions, self.transitions = {}, {}
            for step in AUTO.steps:
                index = ORDER.index(step.number)
                self.actions[step.number] = st.parse("\n".join(
                    gen.sfc_action_logic(APP, AUTO, step, index, NAMES)))
                self.transitions[step.number] = [
                    (target, st.parse(f"IF {gen.sfc_condition(APP, step, kind, NAMES)} "
                                      f"THEN {PROBE} := 1; ELSE {PROBE} := 0; END_IF;"))
                    for kind, target in (("A", step.on_advance), ("J", step.on_jump))
                    if target != -1]

    def ctx(self, name):
        return self.plc.tags[gen.ctx_tag_for(APP, name)]

    def step(self):
        return self.active if self.language == decl.SFC else self.plc.tags[UNIT]["Step"]

    def scan(self):
        tags = self.plc.tags
        tags[SCAN] += 1
        for ctx, setup, body in self.modules:
            self.plc.run(setup)
            st.Controller({"Ctx": tags[ctx], "Scan": tags[SCAN]}).run(body)
        if self.language == decl.ST:
            self.plc.run(self.logic)
        elif self.language == decl.LD:
            ld.run_rungs(self.plc, self.rungs)
        else:
            # Logix SFC, executing the active step only: its action, then its
            # transitions in the chart's order; a fired one activates the next
            # step for the following scan.
            self.plc.run(self.actions[self.active])
            for target, transition in self.transitions[self.active]:
                self.plc.run(transition)
                if tags[PROBE] == 1:
                    self.active = target
                    break

    def one_cycle(self, limit=3000):
        """Scan from N100 until the loop closes back at N100. Returns what the
        plant did."""
        runs = {n: self.ctx(n)["RunCount"] for n in CYLINDERS}
        dones = {n: self.ctx(n)["DoneCount"] for n in CYLINDERS}
        reach = {n: self.ctx(n)["OutImm_Pos"] for n in CYLINDERS}
        steps, seen_end = [], False
        for scans in range(1, limit + 1):
            self.scan()
            for n in CYLINDERS:
                reach[n] = max(reach[n], self.ctx(n)["OutImm_Pos"])
            if not steps or steps[-1] != self.step():
                steps.append(self.step())
            seen_end = seen_end or self.step() == 999
            if seen_end and self.step() == 100:
                break
        else:
            raise AssertionError(f"{self.language}: the cycle did not close")
        return {
            "runs": {n: self.ctx(n)["RunCount"] - runs[n] for n in CYLINDERS},
            "dones": {n: self.ctx(n)["DoneCount"] - dones[n] for n in CYLINDERS},
            "reach": reach,
            "steps": steps,
            "scans": scans,
            "executeLeft": {n: self.ctx(n)["Execute"] for n in CYLINDERS},
            "errors": {n: self.ctx(n)["Error"] for n in CYLINDERS},
        }


def commands_per_module():
    """What the declared AUTO cycle commands, module by module, on its happy
    path (N180 completed, N200 reached)."""
    path = (110, 130, 150, 180, 200, 240, 242, 244)
    by = {s.number: s for s in AUTO.steps}
    return {n: sum(1 for p in path if by[p].module == n) for n in CYLINDERS}


class TheSameCommandsInEveryRendition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cycles = {language: Press(language).one_cycle() for language in AUTO.renditions}

    def test_st_issues_and_completes_exactly_the_declared_commands(self):
        st_cycle = self.cycles[decl.ST]
        self.assertEqual(st_cycle["runs"], commands_per_module())
        self.assertEqual(st_cycle["dones"], commands_per_module())

    def test_every_rendition_issues_and_completes_the_same_commands(self):
        reference = self.cycles[decl.ST]
        for language in AUTO.renditions[1:]:
            with self.subTest(language):
                self.assertEqual(self.cycles[language]["runs"], reference["runs"])
                self.assertEqual(self.cycles[language]["dones"], reference["dones"])

    def test_the_door_closes_and_the_ram_presses_in_every_rendition(self):
        for language in AUTO.renditions:
            with self.subTest(language):
                reach = self.cycles[language]["reach"]
                self.assertEqual(reach, {n: 100 for n in CYLINDERS})

    def test_every_rendition_walks_the_same_steps(self):
        reference = self.cycles[decl.ST]["steps"]
        for language in AUTO.renditions[1:]:
            with self.subTest(language):
                self.assertEqual(self.cycles[language]["steps"], reference)

    def test_every_rendition_leaves_its_modules_released(self):
        """Completion drops Execute, so no module is left Done for the next
        step that commands it to mistake for its own result."""
        for language in AUTO.renditions:
            with self.subTest(language):
                self.assertEqual(self.cycles[language]["executeLeft"],
                                 {n: 0 for n in CYLINDERS})
                self.assertEqual(self.cycles[language]["errors"],
                                 {n: 0 for n in CYLINDERS})


class AStaleDoneIsNotTheStepsOwn(unittest.TestCase):
    """A module can still hold Done from an earlier command when a step that
    commands it is entered - one an abort stood down, or a path that left
    Execute up. ST and LD read the module only after the entry scan, so the
    step commands it afresh; the SFC transition must not take the old Done
    as its own and leave the module unmoved."""

    # Where a real cycle has the rest of the plant when it reaches each step,
    # so the directional permits (TC3's collision interlocks) are satisfied:
    # the door closes over a slide that is inside, and the ram presses with
    # the guard closed and the slide inside.
    PLANT = {180: {"PartSlide": 100}, 200: {"PartSlide": 100, "Door": 100}}

    def enter_with_stale_done(self, language, number, module, target):
        press = Press(language, start=number)
        for other, position in self.PLANT.get(number, {}).items():
            press.ctx(other).update(OutImm_Pos=position, ParCmd_Latched=position,
                                    OutImm_Extended=int(position == 100),
                                    OutImm_Retracted=int(position == 0))
        ctx = press.ctx(module)
        start = 100 - target                 # the other end, so it has to move
        ctx.update(Execute=1, Done=1, OutImm_Pos=start, ParCmd_Latched=start,
                   ExecutePrev=1)
        runs = ctx["RunCount"]
        for _ in range(200):
            press.scan()
            if press.step() != number:
                break
        else:
            self.fail(f"{language} never left N{number}")
        return ctx["RunCount"] - runs, ctx["OutImm_Pos"]

    def test_every_commanding_step_commands_its_module_afresh(self):
        by = {s.number: s for s in AUTO.steps}
        for number in (110, 150, 180, 200):
            step = by[number]
            module = next(m for m in APP.modules if m.name == step.module)
            target = next(c for c in module.commands if c.name == step.command)
            for language in AUTO.renditions:
                with self.subTest(step=number, rendition=language):
                    runs, position = self.enter_with_stale_done(
                        language, number, step.module, target.target_position)
                    self.assertEqual((runs, position), (1, target.target_position))


if __name__ == "__main__":
    unittest.main()

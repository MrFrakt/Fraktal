"""Limits Studio 5000 v33 enforces on generated ST, held as tests.

press36 failed to compile on 2026-10-01: "Too many 'OR' operators in
expression with enough parentheses", on the stall watchdog's test of whether
anything was held - one OR per module, six of them. press35 had compiled the
same line with five. So the measured bound is five operators of one kind in
an expression, and the generator now keeps every chain inside it. Above all,
a chain may not grow with the application: what scales with modules is
written as one IF per module instead.

Measured bound, not a documented one: AND chains are held to the same five,
the most the bench has proved, until a longer one is compiled.
"""

import dataclasses
import re
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo

MAX_SAME_OPERATOR = 5        # Studio v33: 5 ORs compiled (press35), 6 did not (press36)
APP = demo.application()


def st_lines(app):
    """Every line of structured text the generator emits for `app`."""
    names = gen.Names(app, in_aoi=False)
    order = gen.ordered_steps(app)
    lines = list(gen.routine_logic(app)) + list(mailbox.handler_logic(app))
    lines += gen.start_release_logic(app)
    for _, body in gen.alarm_service_routines(app):
        lines += body
    if any(decl.ST in c.renditions or decl.SFC in c.renditions for c in gen.multi_chains(app)):
        lines += gen.step_mark_logic(app)
    if app.line is not None:
        import fraktal_ab_line as line
        for body in (line.validation_logic, line.search_logic, line.close_logic, line.apply_calendar):
            lines += body(app)
    if gen.editable_values(app):
        import fraktal_ab_config as config
        lines += config.audit_logic(app)
    if app.access_users is not None:
        import fraktal_ab_access as access
        import fraktal_ab_shelving as shelving
        for _, body in access.routines(app):
            lines += body
        lines += shelving.handler(app)
    lines += list(gen.unit_logic(app))
    for mtype in library.types_used(app):
        lines += list(gen.type_logic(mtype))
    for chain in gen.multi_chains(app):
        if decl.ST in chain.renditions:
            lines += list(gen.chain_st_logic(app, chain))
        if decl.SFC in chain.renditions:
            for step in chain.steps:
                lines += list(gen.sfc_action_logic(
                    app, chain, step, order.index(step.number), names))
                for kind in ("A", "B"):
                    lines.append(gen.sfc_condition(app, step, kind, names))
    return lines


def worst(lines, operator):
    found = max(((line.count(f" {operator} "), line) for line in lines),
                default=(0, ""))
    return found


class NoChainOutgrowsTheCompiler(unittest.TestCase):
    def test_generated_subscripts_do_not_nest_array_lookups(self):
        # press69 failed Verify on Levels[SetStaged.Ordinal[SetIndex] - 1].
        # Arithmetic over scalar indices remains supported (catalog byte loops).
        import fraktal_ab_station_template as template
        for app in (APP, template.application()):
            text = '\n'.join(st_lines(app))
            text = re.sub(r'\(\*.*?\*\)|//[^\n]*', '', text, flags=re.S)
            self.assertIsNone(re.search(r'\[[^\]\n]*\[', text), app.name)

    def test_generated_st_uses_numeric_boolean_values_not_iec_literal_names(self):
        # press56's 54 EnableIn := TRUE statements failed Studio v33 Verify.
        # Cover every emitted routine in the press and the empty-user template.
        import fraktal_ab_station_template as template
        for app in (APP, template.application()):
            text = '\n'.join(st_lines(app))
            text = re.sub(r'\(\*.*?\*\)|//[^\n]*', '', text, flags=re.S)
            self.assertIsNone(re.search(r'\b(?:TRUE|FALSE)\b', text), app.name)

    def test_the_press(self):
        lines = st_lines(APP)
        for operator in ("OR", "AND"):
            count, line = worst(lines, operator)
            self.assertLessEqual(count, MAX_SAME_OPERATOR, f"{operator}: {line[:200]}")

    def test_an_application_with_many_more_modules(self):
        """What failed was a chain that grew with the module count. Twelve
        more cylinders must not move the worst chain at all."""
        cylinder = next(m for m in APP.modules
                        if library.type_of(m) is library.CYLINDER)
        extra = tuple(dataclasses.replace(cylinder, name=f"Extra{i}")
                      for i in range(12))
        bigger = dataclasses.replace(APP, modules=APP.modules + extra)
        lines = st_lines(bigger)
        for operator in ("OR", "AND"):
            self.assertEqual(worst(lines, operator)[0], worst(st_lines(APP), operator)[0],
                             operator)

    def test_the_watchdog_tests_each_holder_on_its_own_line(self):
        logic = gen.diagnostic_logic(APP)
        flag = gen.diagnostic_scratch_tag(APP)
        holders = [l for l in logic if re.match(rf"IF \S+Held <> 0 THEN {flag} := 1;", l)]
        self.assertEqual(len(holders), len(APP.modules))


if __name__ == "__main__":
    unittest.main()

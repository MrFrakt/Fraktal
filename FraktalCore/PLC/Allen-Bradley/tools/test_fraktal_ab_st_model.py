"""The ST model is a test instrument, so it is tested first.

A model that clamped a subscript, rounded a division or read an undeclared tag
as zero would pass every routine run on it and prove nothing. These pin the
places where Logix differs from what a Python reading would assume.
"""

import unittest

import fraktal_ab_st_model as st


def run(text, **tags):
    controller = st.Controller({k: v for k, v in tags.items()})
    controller.run(text)
    return controller.tags


class Arithmetic(unittest.TestCase):
    def test_division_truncates_toward_zero(self):
        tags = run("A := -7 / 2; B := 7 / -2; C := 7 / 2;", A=0, B=0, C=0)
        self.assertEqual((tags["A"], tags["B"], tags["C"]), (-3, -3, 3))

    def test_mod_takes_the_sign_of_the_dividend(self):
        tags = run("A := -7 MOD 3; B := 7 MOD -3; C := 64 MOD 64;", A=0, B=0, C=0)
        self.assertEqual((tags["A"], tags["B"], tags["C"]), (-1, 1, 0))

    def test_a_dint_wraps(self):
        tags = run("A := 2147483647 + 1;", A=0)
        self.assertEqual(tags["A"], -2147483648)

    def test_divide_by_zero_is_a_fault_not_a_value(self):
        with self.assertRaises(st.StFault):
            run("A := 1 / B;", A=0, B=0)
        with self.assertRaises(st.StFault):
            run("A := 1 MOD B;", A=0, B=0)

    def test_precedence(self):
        tags = run("A := 2 + 3 * 4 - (1 + 1) * 2;", A=0)
        self.assertEqual(tags["A"], 10)

    def test_and_on_dints_is_bitwise_and_on_bools_is_logical(self):
        tags = run("A := 12 AND 10; B := (1 = 1) AND (2 = 3);", A=0, B=0)
        self.assertEqual((tags["A"], tags["B"]), (8, 0))


class Strictness(unittest.TestCase):
    def test_true_and_false_are_tag_names_not_logix_boolean_literals(self):
        for name in ('TRUE', 'FALSE'):
            with self.assertRaises(st.StFault):
                run(f'A := {name};', A=0)
        self.assertEqual(run('A := TRUE;', A=0, TRUE=1)['A'], 1)

    def test_synchronous_structure_copy_is_independent_and_bounds_checked(self):
        tags = {'Source': {'SchemaVersion': 1, 'Value': [41, 2]},
                'Dest': {'SchemaVersion': 0, 'Value': [0, 0]}}
        c = st.Controller(tags, calls={'CPS': st.cps_structure})
        c.run('CPS(Source,Dest,1); Source.Value[0] := 99;')
        self.assertEqual(c.tags['Dest']['Value'], [41, 2])
        with self.assertRaises(st.StError):
            c.run('CPS(Source,Dest,2);')
        c.tags['Dest']['Value'].append(0)
        with self.assertRaises(st.StFault):
            c.run('CPS(Source,Dest,1);')
    def test_a_subscript_out_of_range_faults(self):
        """A clamp here would hide exactly the ring off-by-one this exists
        to find; on the controller it halts the program."""
        with self.assertRaises(st.StFault):
            run("A[4] := 1;", A=[0, 0, 0, 0])
        with self.assertRaises(st.StFault):
            run("B := A[-1];", A=[0], B=0)

    def test_an_undeclared_tag_faults(self):
        with self.assertRaises(st.StFault):
            run("A := Missing;", A=0)

    def test_an_undeclared_member_faults(self):
        with self.assertRaises(st.StFault):
            run("S.Nope := 1;", S={"Yes": 0})

    def test_a_dint_condition_is_refused(self):
        with self.assertRaises(st.StFault):
            run("IF A THEN B := 1; END_IF;", A=1, B=0)

    def test_an_unmodeled_call_is_refused_not_skipped(self):
        with self.assertRaises(st.StError):
            run("SomeAoi(A);", A=0)

    def test_a_real_literal_is_refused(self):
        with self.assertRaises(st.StError):
            st.parse("A := 1.5;")


class Control(unittest.TestCase):
    def test_jsr_runs_the_supplied_native_body_in_caller_storage_and_order(self):
        c = st.Controller({'A': 1}, routines={'Increment': ['A := A + 2;']})
        c.run('JSR(Increment,0); A := A * 3; JSR(Increment,0);')
        self.assertEqual(c.tags['A'], 11)

    def test_jsr_requires_a_body_and_refuses_unmodeled_parameters(self):
        with self.assertRaises(st.StError):
            st.Controller({}).run('JSR(Missing,0);')
        c = st.Controller({'A': 1}, routines={'Increment': 'A := A + 2;'})
        for call in ('JSR(Increment,1);', 'JSR(Increment,0,A);'):
            with self.subTest(call=call), self.assertRaises(st.StError):
                c.run(call)
        self.assertEqual(c.tags['A'], 1)

    def test_for_is_inclusive_and_leaves_the_index_past_the_end(self):
        tags = run("S := 0; FOR I := 0 TO 3 DO S := S + I; END_FOR;", S=0, I=0)
        self.assertEqual((tags["S"], tags["I"]), (6, 4))

    def test_for_that_starts_past_its_end_runs_nothing(self):
        tags = run("FOR I := 5 TO 3 DO S := 1; END_FOR;", S=0, I=0)
        self.assertEqual(tags["S"], 0)

    def test_elsif_takes_the_first_true_arm_only(self):
        text = ("IF A = 1 THEN B := 1; ELSIF A < 5 THEN B := 2; "
                "ELSE B := 3; END_IF;")
        self.assertEqual(run(text, A=1, B=0)["B"], 1)
        self.assertEqual(run(text, A=3, B=0)["B"], 2)
        self.assertEqual(run(text, A=9, B=0)["B"], 3)

    def test_case_with_lists_ranges_and_else(self):
        text = ("CASE A OF 1, 2: B := 1; 5..7: B := 2; "
                "ELSE B := 3; END_CASE;")
        self.assertEqual([run(text, A=a, B=0)["B"] for a in (2, 6, 9)], [1, 2, 3])

    def test_members_and_expression_subscripts(self):
        tags = run("S.V[S.N - 1] := 7;", S={"N": 2, "V": [0, 0]})
        self.assertEqual(tags["S"]["V"], [0, 7])

    def test_comments_are_ignored(self):
        self.assertEqual(run("(* a (comment) *) A := 1;", A=0)["A"], 1)


class WallClock(unittest.TestCase):
    def test_gsv_writes_seven_dints_from_the_destination_on(self):
        controller = st.Controller(
            {"C": [0] * 7},
            {"GSV": st.wall_clock(lambda: (2026, 9, 29, 4, 5, 6, 789012))})
        controller.run("GSV(WallClockTime,,DateTime,C[0]);")
        self.assertEqual(controller.tags["C"], [2026, 9, 29, 4, 5, 6, 789012])

    def test_a_destination_too_short_faults(self):
        controller = st.Controller(
            {"C": [0] * 6},
            {"GSV": st.wall_clock(lambda: (2026, 9, 29, 4, 5, 6, 0))})
        with self.assertRaises(st.StFault):
            controller.run("GSV(WallClockTime,,DateTime,C[0]);")


if __name__ == "__main__":
    unittest.main()

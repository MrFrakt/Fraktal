"""The ladder model itself: Logix's rung semantics, on the subset it claims."""

import unittest

import fraktal_ab_generate as gen
import fraktal_ab_ld_model as ld
import fraktal_ab_press_demo as demo
import fraktal_ab_st_model as st


def plc(**tags):
    return st.Controller(dict(tags))


class RungSemantics(unittest.TestCase):
    def test_series_conditions_gate_the_output(self):
        p = plc(A=1, B=0, X=0)
        ld.run_rung(p, "NEQ(A,0)NEQ(B,0)MOV(5,X);")
        self.assertEqual(p.tags["X"], 0)
        p.tags["B"] = 1
        ld.run_rung(p, "NEQ(A,0)NEQ(B,0)MOV(5,X);")
        self.assertEqual(p.tags["X"], 5)

    def test_a_branch_is_the_or_of_its_legs(self):
        p = plc(A=0, B=1, X=0)
        self.assertTrue(ld.run_rung(p, "[NEQ(A,0),NEQ(B,0)]MOV(1,X);"))
        self.assertEqual(p.tags["X"], 1)
        p.tags["B"] = 0
        p.tags["X"] = 0
        self.assertFalse(ld.run_rung(p, "[NEQ(A,0),NEQ(B,0)]MOV(1,X);"))
        self.assertEqual(p.tags["X"], 0)

    def test_every_leg_runs_even_after_one_is_true(self):
        p = plc(X=0, Y=0)
        ld.run_rung(p, "[MOV(1,X),MOV(2,Y)];")
        self.assertEqual((p.tags["X"], p.tags["Y"]), (1, 2))

    def test_a_later_leg_sees_an_earlier_legs_write(self):
        """Logix executes in order, so a MOV in one leg feeds the next."""
        p = plc(X=0, Y=0)
        ld.run_rung(p, "[MOV(7,X),EQU(X,7)MOV(1,Y)];")
        self.assertEqual(p.tags["Y"], 1)

    def test_outputs_on_a_false_rung_do_nothing(self):
        p = plc(X=3, Y=4)
        ld.run_rung(p, "EQU(1,0)ADD(X,1,X)MOV(9,Y);")
        self.assertEqual((p.tags["X"], p.tags["Y"]), (3, 4))

    def test_math_wraps_as_a_dint(self):
        p = plc(X=st.DINT_MAX)
        ld.run_rung(p, "ADD(X,1,X);")
        self.assertEqual(p.tags["X"], st.DINT_MIN)

    def test_members_and_subscripts_are_the_st_models(self):
        p = plc(S={"A": [0, 0, 0]}, I=2)
        ld.run_rung(p, "MOV(4,S.A[I]);")
        self.assertEqual(p.tags["S"]["A"], [0, 0, 4])
        with self.assertRaises(st.StFault):
            ld.run_rung(p, "MOV(4,S.A[3]);")

    def test_an_unmodeled_instruction_is_refused(self):
        with self.assertRaises(st.StError):
            ld.run_rung(plc(X=0), "OTE(X);")

    def test_a_malformed_rung_is_refused(self):
        with self.assertRaises(st.StError):
            ld.parse_rung("[NEQ(A,0)MOV(1,X);")


class TheGeneratedLadderIsInTheSubset(unittest.TestCase):
    def test_every_auto_rung_parses(self):
        app = demo.application()
        for chain in gen.multi_chains(app):
            for rung in gen.chain_ld_rungs(app, chain):
                ld.parse_rung(rung)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

# check_consistency stays at the repository root (it spans PLC, HMI and
# Specification) but reaches into the TwinCAT binding's own tools for the
# ladder readers; importing it first is what puts them on sys.path.
from tools.check_consistency import (
    Finding,
    _is_test_source,
    _ld_chain,
    _reference_roots,
    _st_chain,
    _st_step_writes,
    check_inventory,
    check_localization,
    check_parity,
    emit_stubs,
)

PLC_ROOT = Path("FraktalCore/PLC/TwinCAT")


class LocalizationTests(unittest.TestCase):
    """A key with no catalogue entry renders on the HMI as the raw key."""

    def test_shipping_code_is_measured_and_test_fixtures_are_not(self):
        # The distinction is the whole point: a probe FB may use a throwaway
        # key, but anything an operator can reach may not.
        self.assertTrue(_is_test_source(Path("x/FB_Unit_Tests.TcPOU")))
        self.assertTrue(_is_test_source(Path("x/FB_ProbeCM.TcPOU")))
        self.assertTrue(_is_test_source(Path("scaffold/FB_TemplateCM.TcPOU")))
        self.assertFalse(_is_test_source(Path("x/FB_PressDemoUnit.TcPOU")))

    def test_findings_are_warnings_so_the_gate_stays_usable(self):
        # The catalogue has a real backlog. A check that turns the gate red on
        # the day it lands teaches everyone to skip the gate.
        findings, _ = check_localization(PLC_ROOT)
        self.assertTrue(all(f.severity == "warning" for f in findings),
                        "localization findings must not fail the run yet")

    def test_emit_produces_pasteable_dart_for_every_missing_key(self):
        _, missing = check_localization(PLC_ROOT)
        stubs = emit_stubs(missing)
        for key in missing:
            self.assertIn(f"'{key}': 'TODO',", stubs)
        self.assertIn("Replace every TODO", stubs)


class InventoryTests(unittest.TestCase):
    """A suite that no runner instantiates does not run, and says nothing."""

    def test_the_shipped_inventory_is_consistent(self):
        # This is the check that would have caught 84/26 drifting from 94/29
        # while two of the three new suites did not even compile.
        errors = [f for f in check_inventory(PLC_ROOT) if f.severity == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_an_unregistered_suite_is_an_error(self):
        # Guard the guard: if the rule silently stopped firing it would look
        # exactly like a clean repository.
        from tools import check_consistency
        original = check_consistency._sources
        fake = Path("FB_Orphan_Tests.TcPOU")
        try:
            check_consistency._sources = lambda root: [fake]
            check_consistency._read = lambda path: (
                "EXTENDS TcUnit.FB_TestSuite\nTEST('a');\nTEST('b');")
            findings = check_inventory(PLC_ROOT)
        finally:
            check_consistency._sources = original
            check_consistency._read = lambda path: path.read_text(
                encoding="utf-8-sig", errors="replace")
        self.assertTrue(any("no TcUnit runner" in f.message for f in findings))


class ParityTests(unittest.TestCase):
    """A chain carried in two languages is the same chain in both."""

    def test_the_shipped_renditions_agree(self):
        errors = [f for f in check_parity(PLC_ROOT) if f.severity == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_st_chain_reads_labels_and_advance_targets(self):
        source = """CASE _step OF
    0:
        M_Advance(OnAdvance := 100);
    100:
        M_Advance(OnAdvance := 200, OnJump1 := 185);
ELSE
"""
        self.assertEqual(_st_chain(source), {0: {100}, 100: {200, 185}})

    def test_parity_compares_the_real_ladder_against_its_real_twin(self):
        # Not a fixture: the point of the check is that it reads the artifacts.
        ladder = (PLC_ROOT / "Examples/PressDemo/Fraktal_Press_Demo/01_PneumaticPress"
                  / "Sequences/FB_LD_PressDemoAuto.TcPOU")
        twin = ladder.with_name("FB_PressDemoAuto.TcPOU")
        self.assertTrue(ladder.is_file() and twin.is_file())
        import xml.etree.ElementTree as ET

        from ld_rung_gen import split_networks
        st = _st_chain(twin.read_text(encoding="utf-8-sig"))
        ld = _ld_chain(ladder.read_text(encoding="utf-8-sig"), split_networks, ET)
        self.assertEqual(sorted(st), sorted(ld))
        self.assertEqual(len(ld), 16)
        # A rung whose gate was `EQ(215, 0)` would simply be absent here - that
        # is exactly how two dead rungs passed every other gate.
        self.assertIn(215, ld)


class StepEffectTests(unittest.TestCase):
    """Same steps and same transitions is not yet the same chain.

    `FB_LD_PressDemoAuto` step 190 agreed on both and still dropped
    `_startLatched := FALSE`, which looped the machine after a two-hand abort.
    """

    def test_only_state_that_escapes_the_chain_is_compared(self):
        declaration = """FUNCTION_BLOCK FB_X EXTENDS FB_SequenceBase
VAR
    _scratch, _partProcessed : BOOL;
    _door : REFERENCE TO FB_CylinderCM;
    _startLatched : REFERENCE TO BOOL;
END_VAR]]"""
        self.assertEqual(_reference_roots(declaration),
                         {"_door", "_startLatched"})

    def test_step_writes_ignore_named_arguments_and_locals(self):
        source = """CASE _step OF
    190:
        M_Step(StepNo := 190, Awaits := _partSlide, Branch := 0);
        _scratch := M_TryIssue(Steppable := TRUE);
        IF _partSlide.Done THEN
            _door.Execute := FALSE;
            _startLatched := FALSE;
        END_IF
ELSE
"""
        roots = {"_door", "_startLatched", "_partSlide"}
        # `StepNo :=` and `Steppable :=` bind parameters; `_scratch` is a local.
        self.assertEqual(_st_step_writes(source, roots),
                         {190: {"_door.Execute", "_startLatched"}})

    def test_the_dropped_effect_that_shipped_is_now_an_error(self):
        # Rebuild the exact regression: the ladder rung for step 190 without its
        # `_startLatched` reset coil, against the real ST twin.
        import xml.etree.ElementTree as ET

        from tools.check_consistency import _ld_step_writes
        from ld_dump import _value
        from ld_rung_gen import split_networks

        ladder = (PLC_ROOT / "Examples/PressDemo/Fraktal_Press_Demo/01_PneumaticPress"
                  / "Sequences/FB_LD_PressDemoAuto.TcPOU")
        text = ladder.read_text(encoding="utf-8-sig")
        per_step, continuous = _ld_step_writes(text, split_networks, ET, _value)
        self.assertIn("_startLatched", per_step[190],
                      "the shipped rung must carry the abort's start-latch reset")
        # A plain coil drives its symbol every scan, so the ST twin's explicit
        # clears in other steps have no ladder counterpart to find and must not
        # be reported. `_outCmd` is written by exactly such a coil.
        self.assertIn("_outCmd", continuous)


class CommandLineTests(unittest.TestCase):
    '''The invocation CI uses, which no test covered.

    `checks` is a nargs="*" positional. Give argparse a `choices=` alongside
    that and Python <= 3.12 validates the empty DEFAULT against choices, so the
    documented no-argument form ("run everything") dies with
    `invalid choice: '[]'` and exit 2 - a broken CLI, not a failing gate.
    Python 3.13 stopped doing it, so on a newer interpreter the bug is
    invisible. It survived because every caller either named all three checks
    explicitly or ran a new enough Python; the first hosted job to run the bare
    form found it immediately.

    These call the parser in-process rather than shelling out, so they assert
    the behaviour on whatever interpreter is running the suite.
    '''

    def _parse(self, argv):
        import tools.check_consistency as cc
        return cc.build_parser().parse_args(argv)

    def test_no_arguments_selects_every_check(self):
        self.assertEqual(self._parse([]).checks, [])

    def test_named_checks_are_kept(self):
        self.assertEqual(self._parse(["parity"]).checks, ["parity"])

    def test_an_unknown_check_is_still_rejected(self):
        import tools.check_consistency as cc
        with self.assertRaises(SystemExit) as raised:
            cc.main(["check_consistency.py", "bogus"])
        self.assertEqual(raised.exception.code, 2)


class FindingTests(unittest.TestCase):
    def test_severity_is_visible_at_a_glance(self):
        self.assertTrue(str(Finding("x", "error", "f", "m")).startswith("ERROR"))
        self.assertTrue(str(Finding("x", "warning", "f", "m")).startswith("warn"))


if __name__ == "__main__":
    unittest.main()

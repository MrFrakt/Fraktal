"""The AB binding's ordinals against the Core DUTs that define them.

`AGENTS.md` §4 says it plainly: the enum ordinals are the PLC contract, and both
bindings must carry the same ones. Nothing checked it, and the AB press demo
declared `MANUAL = 0, AUTO = 1` while Core `E_Mode` says `AUTO := 0,
MANUAL := 1`. Every published `Mode` and `ModeRequest` value was one place out
from what an HMI resolves against, so an operator screen reading the AB
controller would have rendered MANUAL as AUTO.

That is not the kind of thing to fix once. These tests read the TwinCAT DUTs
themselves rather than restating their values here - a test that carried its own
copy of the ordinals would agree with whatever it was written from, which is
exactly how the two sides drifted apart in the first place.
"""

import re
import unittest
from pathlib import Path

import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo

CORE_DUTS = (Path(__file__).resolve().parents[2]
             / "TwinCAT" / "Framework" / "Fraktal_Core" / "DUTs")

MEMBER = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)\s*:=\s*(-?\d+)\s*,?\s*(?://.*)?$")


def core_enum(name):
    """The ordinals a Core DUT actually declares, read from the DUT.

    Comments come off before the closing parenthesis is looked for. Several
    members carry a trailing ``// ... (optional)``, and splitting on the first
    ``)`` cut E_Mode off at CAPABILITY - a reader that silently returns six of
    seven members is worse than one that cannot read the file at all.
    """
    source = (CORE_DUTS / f"{name}.TcDUT").read_text(encoding="utf-8")
    body = source.split(f"TYPE {name} :", 1)[1]
    uncommented = chr(10).join(
        line.split("//", 1)[0] for line in body.split(chr(10)))
    found = {}
    for line in uncommented.split(")", 1)[0].split(chr(10)):
        match = MEMBER.match(line)
        if match:
            found[match.group(1)] = int(match.group(2))
    return found


class CoreDutReadingTests(unittest.TestCase):
    """If the reader is wrong, everything below it is decoration."""

    def test_the_core_duts_are_where_this_expects_them(self):
        self.assertTrue(CORE_DUTS.is_dir(), str(CORE_DUTS))

    def test_it_reads_e_mode(self):
        modes = core_enum("E_Mode")
        self.assertEqual(modes["AUTO"], 0)
        self.assertEqual(modes["MANUAL"], 1)
        self.assertEqual(modes["HOME"], 2)

    def test_it_reads_every_declared_member(self):
        self.assertEqual(len(core_enum("E_Mode")), 7)
        self.assertEqual(len(core_enum("E_ExecState")), 5)

    def test_it_does_not_invent_members(self):
        self.assertNotIn("NONSENSE", core_enum("E_Mode"))


class ModeOrdinalTests(unittest.TestCase):
    def setUp(self):
        self.core = core_enum("E_Mode")

    def test_auto_matches_core(self):
        self.assertEqual(demo.MODE_AUTO, self.core["AUTO"])

    def test_manual_matches_core(self):
        self.assertEqual(demo.MODE_MANUAL, self.core["MANUAL"])

    def test_home_matches_core(self):
        self.assertEqual(demo.MODE_HOME, self.core["HOME"])

    def test_the_declared_chains_carry_the_core_ordinals(self):
        # The ordinal reaches the controller through the chain declaration, so
        # checking the constants alone would miss a chain wired to the wrong one.
        app = demo.application()
        by_name = {c.name: c.mode_ordinal for c in app.chains}
        self.assertEqual(by_name["AUTO"], self.core["AUTO"])
        self.assertEqual(by_name["MANUAL"], self.core["MANUAL"])
        self.assertEqual(by_name["HOME"], self.core["HOME"])

    def test_no_two_chains_claim_the_same_mode(self):
        app = demo.application()
        ordinals = [c.mode_ordinal for c in app.chains]
        self.assertEqual(len(ordinals), len(set(ordinals)))


class ExecStateOrdinalTests(unittest.TestCase):
    def setUp(self):
        self.core = core_enum("E_ExecState")

    def test_every_generated_state_matches_core(self):
        self.assertEqual(gen.STATE_READY, self.core["READY"])
        self.assertEqual(gen.STATE_BUSY, self.core["BUSY"])
        self.assertEqual(gen.STATE_DONE, self.core["DONE"])
        self.assertEqual(gen.STATE_ERROR, self.core["ERROR"])
        self.assertEqual(gen.STATE_ABORTED, self.core["ABORTED"])

    def test_held_is_not_an_exec_state(self):
        # Core §6.1: Held is a separate flag, never a sixth ordinal.
        self.assertNotIn("HELD", self.core)


if __name__ == "__main__":
    unittest.main()

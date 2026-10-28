"""Core §8.8/§8.9: the AB binding's reason numbers, held to their sources.

The registry is the collision authority and TwinCAT's parameter lists carry the
numbers (the HMI's reason catalogue is generated from the same two). A code
this binding restates is pinned here against the file that defines it, so a
renumbering on either side fails a test instead of shipping two meanings for
one number. The DUTs are read, not transcribed, for the reason
test_fraktal_ab_core_ordinals gives.
"""

import dataclasses
import json
import re
import unittest
from pathlib import Path

import fraktal_ab_library as library
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_reasons as reasons
from test_fraktal_ab_core_ordinals import core_enum

TWINCAT = Path(__file__).resolve().parents[2] / "TwinCAT"
SOURCES = (
    TWINCAT / "Framework" / "Fraktal_Core" / "DUTs" / "E_Reason.TcDUT",
    TWINCAT / "Framework" / "Fraktal_Core" / "Params" / "PL_TcpDevReasons.TcGVL",
    TWINCAT / "Framework" / "Fraktal_Modules" / "Params" / "PL_ModuleReasons.TcGVL",
)
PRESS = (TWINCAT / "Examples" / "PressDemo" / "Fraktal_Press_Demo"
         / "01_PneumaticPress" / "PL_PressReasons.TcGVL")
CONSTANT = re.compile(r"([A-Z_][A-Z0-9_]*)\s*(?::\s*DINT\s*)?:=\s*(\d+)")
APP = demo.application()


def twincat_codes() -> dict[str, int]:
    """Every reason symbol TwinCAT defines, with its number."""
    codes: dict[str, int] = {}
    for source in SOURCES:
        text = "\n".join(line.split("//", 1)[0] for line in
                         source.read_text(encoding="utf-8").splitlines())
        for name, code in CONSTANT.findall(text):
            codes.setdefault(name, int(code))
    if not codes:
        raise AssertionError("read no reason codes from the TwinCAT sources")
    return codes


class TheNumbersAreTwinCATs(unittest.TestCase):
    def test_every_registered_reason_carries_its_registered_code(self):
        codes = twincat_codes()
        for name, code in APP.reasons.items():
            if reasons.registered(name):
                self.assertEqual(code, codes.get(name), name)

    def test_the_core_codes_this_binding_raises(self):
        codes = twincat_codes()
        for name, code in reasons.CORE.items():
            self.assertEqual(code, codes[name], name)

    def test_the_cylinder_raises_tc3s_cylinder_codes(self):
        codes = twincat_codes()
        for name, code in library.CYLINDER.reasons.items():
            self.assertEqual(code, codes[name], name)
            self.assertTrue(reasons.registered(name), name)

    def test_the_two_hand_release_is_tc3s_press_code(self):
        text = PRESS.read_text(encoding="utf-8")
        found = re.search(r"PRESS_TWO_HAND_RELEASED\s*:\s*DINT\s*:=\s*(\d+)", text)
        self.assertIsNotNone(found)
        self.assertEqual(APP.reasons["TWO_HAND_RELEASED"], int(found.group(1)))

    def test_the_published_ordinals_are_core_enums(self):
        self.assertEqual(reasons.PRIORITY, core_enum("E_Severity"))
        self.assertEqual(reasons.CATEGORY, core_enum("E_Category"))


class OneRationale(unittest.TestCase):
    def test_a_registered_reason_is_the_registrys(self):
        entry = json.loads(reasons.REGISTRY_PATH.read_text(encoding="utf-8"))[
            "reasons"]["CYL_NOT_EXTENDED"]
        rationale = reasons.of(APP, "CYL_NOT_EXTENDED")
        self.assertEqual(rationale.priority, reasons.PRIORITY[entry["priority"]])
        self.assertEqual(rationale.category, reasons.CATEGORY[entry["category"]])
        self.assertEqual(rationale.shelvable, entry["shelvable"])
        self.assertEqual(rationale.stem, "std.reason.10101")

    def test_the_manifest_row_is_the_rationale(self):
        rows = {r["ReasonCode"]: r for r in manifest.content(APP)["Rationalization"]}
        keys = {r["NumericKey"]: r["PortableKey"]
                for r in manifest.content(APP)["Localization"]}
        for name, code in APP.reasons.items():
            rationale = reasons.of(APP, name)
            row = rows[code]
            self.assertEqual((row["Priority"], row["Category"], bool(row["Shelvable"])),
                             (rationale.priority, rationale.category, rationale.shelvable),
                             name)
            self.assertEqual(keys[row["ActionKey"]], f"{rationale.stem}.action", name)

    def test_a_wait_is_the_machine_asking(self):
        """From the declaration's use, not the name: N100's hold reason."""
        self.assertIn("PART_NOT_PRESENT", reasons.waiting_reasons(APP))
        rationale = reasons.of(APP, "PART_NOT_PRESENT")
        self.assertEqual((rationale.priority, rationale.shelvable), (0, True))
        self.assertEqual(rationale.category, reasons.CATEGORY["PROCESS"])

    def test_no_project_reason_is_filed_as_safety_or_system(self):
        """The defect this replaced: category 1 is SAFETY and 2 is SYSTEM,
        and every press wait was published as a safety alarm."""
        for name in APP.reasons:
            if not reasons.registered(name):
                self.assertEqual(reasons.of(APP, name).category,
                                 reasons.CATEGORY["PROCESS"], name)


class BandRules(unittest.TestCase):
    def test_the_press_is_clean(self):
        self.assertEqual(reasons.validate(APP), [])

    def test_a_project_code_below_the_band_is_refused(self):
        app = dataclasses.replace(APP, reasons={**APP.reasons, "MY_REASON": 6100})
        self.assertTrue(any("project band" in f for f in reasons.validate(app)))

    def test_a_core_reason_with_another_number_is_refused(self):
        app = dataclasses.replace(APP, reasons={**APP.reasons, "STEP_STALLED": 6120})
        self.assertTrue(any("is Core 2005" in f for f in reasons.validate(app)))

    def test_a_stall_reason_a_step_publishes_must_be_registered(self):
        trimmed = {k: v for k, v in APP.reasons.items() if k != "WAIT_DELAY"}
        app = dataclasses.replace(APP, reasons=trimmed)
        self.assertTrue(any("WAIT_DELAY" in f for f in reasons.validate(app)))


if __name__ == "__main__":
    unittest.main()

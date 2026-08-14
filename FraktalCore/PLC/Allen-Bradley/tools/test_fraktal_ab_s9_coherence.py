import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fraktal_ab_l5x_inventory import inventory
from fraktal_ab_s9_coherence_fixture import (
    DATA_LENGTH,
    DATA_TAG,
    DEFAULT_PERIOD,
    MAX_PERIOD,
    MIN_PERIOD,
    generate,
    routine_lines,
)
from fraktal_ab_s9_execute import _arguments, _consistent, guarded_read


SEED = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetType="Controller" TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33">
<DataTypes/>
<Modules><Module Name="Discrete_IO" Inhibited="false"/></Modules>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


def build(temporary: str):
    source = Path(temporary) / "seed.L5X"
    output = Path(temporary) / "coherence.L5X"
    source.write_text(SEED, encoding="utf-8")
    evidence = generate(source, output)
    return evidence, output.read_text(encoding="utf-8"), inventory(output)


class Reply:
    def __init__(self, status="Success", value=None):
        self.Status = status
        self.Value = value


class MutatingController:
    """A controller whose payload advances a generation on every read."""

    def __init__(self, mutate: bool):
        self.mutate = mutate
        self.generation = 1
        self.revision = 1

    def _advance(self):
        if self.mutate:
            self.generation += 1
            self.revision += 1

    def Read(self, tag, count=None):
        if tag == "FRK_S9_DataRevision":
            return Reply(value=self.revision)
        if tag == DATA_TAG:
            first = self.generation
            self._advance()
            # a torn payload straddles two generations
            half = [first] * (DATA_LENGTH // 2)
            return Reply(value=half + [self.generation] * (DATA_LENGTH - len(half)))
        return Reply(status="Path segment error")


class StableController(MutatingController):
    def __init__(self):
        super().__init__(mutate=False)

    def Read(self, tag, count=None):
        if tag == "FRK_S9_DataRevision":
            return Reply(value=self.revision)
        if tag == DATA_TAG:
            return Reply(value=[self.generation] * DATA_LENGTH)
        return Reply(status="Path segment error")


class S9FixtureTests(unittest.TestCase):
    def test_output_is_well_formed_and_publishes_the_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text, census = build(temporary)
            ElementTree.fromstring(text)
            self.assertIn("FRK_S9_DataRevision", census["ControllerTags"])
            self.assertEqual(
                census["ControllerTags"][DATA_TAG]["dimensions"], str(DATA_LENGTH)
            )

    def test_the_token_is_published_after_the_payload_it_describes(self):
        lines = routine_lines()
        payload = next(
            index for index, line in enumerate(lines) if "END_FOR;" in line
        )
        token = next(
            index for index, line in enumerate(lines)
            if "FRK_S9_DataRevision := " in line
        )
        self.assertLess(payload, token)

    def test_the_whole_payload_moves_inside_one_scan(self):
        # a mutation spread across scans would need seqlock semantics rather
        # than a single monotonic token
        lines = "\n".join(routine_lines())
        self.assertIn(f"FOR FRK_S9_Index := 0 TO {DATA_LENGTH - 1} DO", lines)
        self.assertIn("END_FOR;", lines)

    def test_the_requested_period_is_range_checked_before_use(self):
        lines = "\n".join(routine_lines())
        self.assertIn(f"FRK_S9_MutationPeriod >= {MIN_PERIOD}", lines)
        self.assertIn(f"FRK_S9_MutationPeriod <= {MAX_PERIOD}", lines)
        self.assertIn(f"FRK_S9_PeriodInUse := {DEFAULT_PERIOD};", lines)

    def test_only_the_two_declared_inputs_are_writable(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, _, census = build(temporary)
            writable = sorted(
                name for name, tag in census["ControllerTags"].items()
                if tag["externalAccess"] == "Read/Write"
            )
            self.assertEqual(writable, sorted(evidence["WritableInputs"]))

    def test_no_faulting_construct_is_generated(self):
        lines = "\n".join(routine_lines())
        self.assertNotIn("/", lines)

    def test_fixture_stays_memory_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, text, _ = build(temporary)
            self.assertNotRegex(text, r"\b(?:Local|Discrete_IO):[IOC]")
            self.assertIn('Module Name="Discrete_IO" Inhibited="true"', text)
            self.assertEqual(evidence["PhysicalIoReferences"], 0)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "seed.L5X"
            output = Path(temporary) / "coherence.L5X"
            source.write_text(SEED, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                generate(source, output)


class S9GuardTests(unittest.TestCase):
    def test_consistency_predicate(self):
        self.assertTrue(_consistent([7] * 10))
        self.assertFalse(_consistent([7] * 9 + [8]))

    def test_the_guard_rejects_a_read_that_spans_a_mutation(self):
        result = guarded_read(MutatingController(mutate=True))
        self.assertFalse(result["accepted"])
        # and the payload really was torn, so the rejection was warranted
        self.assertFalse(result["internallyConsistent"])

    def test_the_guard_accepts_a_quiet_controller(self):
        result = guarded_read(StableController())
        self.assertTrue(result["accepted"])
        self.assertTrue(result["internallyConsistent"])

    def test_arm_flag_and_bounds_are_enforced(self):
        with self.assertRaises(SystemExit):
            _arguments(["192.0.2.1", "--expect-serial", "7036B510"])
        with self.assertRaises(SystemExit):
            _arguments([
                "192.0.2.1", "--expect-serial", "7036B510",
                "--execute-fixture", "--sweep", "0",
            ])


if __name__ == "__main__":
    unittest.main()

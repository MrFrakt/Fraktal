import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fraktal_ab_s11_fixture import (
    ENTRY_STEP,
    ENTRY_TRANSITION,
    FINAL_STEP,
    JOIN_TRANSITION,
    LEG_STEPS,
    SFC_EXECUTION_CONTROL,
    SFC_LAST_SCAN,
    SFC_RESTART_POSITION,
    STEPS,
    expected_trace,
    generate,
)


EMPTY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetType="Controller" TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33" SFCExecutionControl="CurrentActive" SFCRestartPosition="MostRecent" SFCLastScan="DontScan">
<DataTypes/>
<Modules><Module Name="Discrete_IO" Inhibited="false"/></Modules>
<AddOnInstructionDefinitions/>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


def build(temporary: str) -> tuple[dict[str, object], str]:
    source = Path(temporary) / "empty.L5X"
    output = Path(temporary) / "fixture.L5X"
    source.write_text(EMPTY, encoding="utf-8")
    return generate(source, output), output.read_text(encoding="utf-8")


class S11FixtureTests(unittest.TestCase):
    def test_output_is_well_formed_xml(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            ElementTree.fromstring(text)

    def test_both_forms_come_from_one_graph_declaration(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            chart = ElementTree.fromstring(text).find(".//SFCContent")
            charted = {step.get("Operand") for step in chart.findall("Step")}
            self.assertEqual(charted, {step.step_tag for step in STEPS})

            sequence = next(
                definition
                for definition in ElementTree.fromstring(text).iter(
                    "AddOnInstructionDefinition"
                )
                if definition.get("Name") == "FRK_S11_SeqSt"
            )
            body = "\n".join(
                line.text or ""
                for line in sequence.iter("Line")
            )
            for step in STEPS:
                # the ST twin dispatches on the same Core step numbers the
                # chart carries as step tags
                self.assertIn(
                    f"FRK_Seq_Step(Svc{step.number},Ctx,{step.number},{step.branch});",
                    body,
                )
            self.assertEqual(result["ExpectedTrace"], list(expected_trace()))

    def test_chart_wiring_is_complete_and_resolvable(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            chart = ElementTree.fromstring(text).find(".//SFCContent")

            declared = set()
            for element in chart:
                if element.tag in {"Step", "Transition", "Branch"}:
                    declared.add(int(element.get("ID")))
                if element.tag == "Step":
                    declared.update(
                        int(action.get("ID")) for action in element.findall("Action")
                    )
                if element.tag == "Branch":
                    declared.update(
                        int(leg.get("ID")) for leg in element.findall("Leg")
                    )

            sources: list[int] = []
            targets: list[int] = []
            for link in chart.findall("DirectedLink"):
                source = int(link.get("FromID"))
                target = int(link.get("ToID"))
                self.assertIn(source, declared)
                self.assertIn(target, declared)
                sources.append(source)
                targets.append(target)

            self.assertEqual(len(sources), len(set(sources)))
            self.assertEqual(len(targets), len(set(targets)))

            identifiers = {
                element.get("Operand"): int(element.get("ID"))
                for element in chart
                if element.tag in {"Step", "Transition"}
            }
            # the initial step has no predecessor and the terminal step no
            # successor; every other element is wired on both sides
            self.assertNotIn(identifiers[ENTRY_STEP.step_tag], targets)
            self.assertNotIn(identifiers[FINAL_STEP.step_tag], sources)
            for step in LEG_STEPS:
                self.assertIn(identifiers[step.step_tag], sources)
                self.assertIn(identifiers[step.step_tag], targets)
            for transition in (ENTRY_TRANSITION, JOIN_TRANSITION):
                self.assertIn(identifiers[transition], sources)
                self.assertIn(identifiers[transition], targets)

    def test_simultaneous_branch_has_one_leg_per_core_branch(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            chart = ElementTree.fromstring(text).find(".//SFCContent")
            branches = chart.findall("Branch")
            self.assertEqual(len(branches), result["SfcSimultaneousBranches"])
            self.assertEqual(
                [branch.get("BranchType") for branch in branches],
                ["Simultaneous", "Simultaneous"],
            )
            self.assertEqual(
                [branch.get("BranchFlow") for branch in branches],
                ["Diverge", "Converge"],
            )
            for branch in branches:
                self.assertEqual(len(branch.findall("Leg")), len(LEG_STEPS))

    def test_actions_are_non_stored_and_call_only_permitted_surfaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            chart = ElementTree.fromstring(text).find(".//SFCContent")
            for step in chart.findall("Step"):
                actions = step.findall("Action")
                self.assertEqual(len(actions), 1)
                self.assertEqual(actions[0].get("Qualifier"), "NonStored")
                self.assertEqual(actions[0].get("IsBoolean"), "false")
                body = "\n".join(
                    line.text or "" for line in actions[0].iter("Line")
                )
                self.assertIn("FRK_Seq_Step(", body)
                # AB §3.5 forbids an action calling a public module AOI
                self.assertNotIn("FRK_S11_Module(", body)
                self.assertNotIn("FRK_S11_Owner(", body)
                self.assertNotIn("JSR(", body)

    def test_wrapper_resets_to_the_declared_initial_step(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            self.assertIn(
                f"SFR(FRK_S11_SfcChain,{ENTRY_STEP.step_tag});", text
            )
            self.assertIn("IF FRK_S11_SfcCtx.Busy <> 0 THEN", text)
            self.assertIn("JSR(FRK_S11_SfcChain,0);", text)

    def test_owner_runs_the_module_aoi_before_the_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            module = text.index("FRK_S11_Module(Module,Ctx,ScanNo);")
            sequence = text.index("FRK_S11_SeqSt(Seq,Ctx,ScanNo);")
            self.assertLess(module, sequence)

    def test_declares_the_required_controller_sfc_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            self.assertIn(f'SFCExecutionControl="{SFC_EXECUTION_CONTROL}"', text)
            self.assertIn(f'SFCRestartPosition="{SFC_RESTART_POSITION}"', text)
            self.assertIn(f'SFCLastScan="{SFC_LAST_SCAN}"', text)
            self.assertEqual(result["SfcRestartPosition"], SFC_RESTART_POSITION)

    def test_fixture_stays_memory_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            self.assertNotRegex(text, r"\b(?:Local|Discrete_IO):[IOC]")
            self.assertIn('Module Name="Discrete_IO" Inhibited="true"', text)
            self.assertIn('DisableUpdateOutputs="true"', text)
            self.assertEqual(result["PhysicalIoReferences"], 0)
            self.assertEqual(
                result["WritableInputs"],
                ["FRK_S11_Command", "FRK_S11_ResetRequest"],
            )

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            output = Path(temporary) / "fixture.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                generate(source, output)

    def test_rejects_a_source_that_is_not_the_empty_v33_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            output = Path(temporary) / "fixture.L5X"
            source.write_text(EMPTY.replace("<Tasks/>", ""), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not the expected empty"):
                generate(source, output)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from fraktal_ab_sfc_roundtrip_compare import ChartError, chart_model, compare


def document(
    *,
    steps: str | None = None,
    transition_condition: str = "Ctx.Result = 10",
    qualifier: str = "NonStored",
    branch_type: str = "Simultaneous",
    first_id: int = 0,
    settings: str = 'SFCExecutionControl="CurrentActive" '
    'SFCRestartPosition="InitialStep" SFCLastScan="DontScan"',
) -> str:
    """A two-leg simultaneous chart whose element IDs start at `first_id`."""
    identifier = first_id
    n10, a10, n30, n40, t10 = (identifier + offset for offset in range(5))
    diverge, leg1, leg2 = (identifier + offset for offset in (5, 6, 7))
    step_block = steps or f"""<Step ID="{n10}" X="0" Y="0" Operand="N10" InitialStep="true">
<Action ID="{a10}" Operand="A10" Qualifier="{qualifier}" IsBoolean="false">
<Body><STContent><Line Number="0"><![CDATA[Ctx.Intent := 10;]]></Line></STContent></Body>
</Action>
</Step>
<Step ID="{n30}" X="0" Y="100" Operand="N30" InitialStep="false"/>
<Step ID="{n40}" X="100" Y="100" Operand="N40" InitialStep="false"/>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content>
<Controller Use="Target" Name="Fixture" {settings}>
<Programs>
<Program Name="P">
<Routines>
<Routine Name="Chart" Type="SFC">
<SFCContent SheetSize="Letter - 8.5 x 11 in">
{step_block}
<Transition ID="{t10}" X="0" Y="50" Operand="T10">
<Condition><STContent><Line Number="0"><![CDATA[{transition_condition}]]></Line></STContent></Condition>
</Transition>
<Branch ID="{diverge}" Y="80" BranchType="{branch_type}" BranchFlow="Diverge">
<Leg ID="{leg1}"/>
<Leg ID="{leg2}"/>
</Branch>
<DirectedLink FromID="{n10}" ToID="{t10}" Show="true"/>
<DirectedLink FromID="{t10}" ToID="{diverge}" Show="true"/>
<DirectedLink FromID="{leg1}" ToID="{n30}" Show="true"/>
<DirectedLink FromID="{leg2}" ToID="{n40}" Show="true"/>
</SFCContent>
</Routine>
</Routines>
</Program>
</Programs>
</Controller>
</RSLogix5000Content>
"""


class SfcRoundTripCompareTests(unittest.TestCase):
    def compare_documents(self, left: str, right: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.L5X"
            second = Path(temporary) / "second.L5X"
            first.write_text(left, encoding="utf-8")
            second.write_text(right, encoding="utf-8")
            return compare(first, second)

    def test_identical_charts_are_equivalent(self):
        report = self.compare_documents(document(), document())
        self.assertTrue(report["Equivalent"], report["Differences"])
        self.assertEqual(report["ChartsCompared"], ["P/Chart"])
        self.assertEqual(report["StepsCompared"], 3)

    def test_renumbered_identifiers_are_still_equivalent(self):
        report = self.compare_documents(
            document(first_id=0), document(first_id=500)
        )
        self.assertTrue(report["Equivalent"], report["Differences"])

    def test_changed_transition_condition_is_reported(self):
        report = self.compare_documents(
            document(), document(transition_condition="Ctx.Result = 99")
        )
        self.assertFalse(report["Equivalent"])
        self.assertIn("P/Chart: transitions differ", report["Differences"])

    def test_changed_action_qualifier_is_reported(self):
        report = self.compare_documents(
            document(), document(qualifier="Stored")
        )
        self.assertFalse(report["Equivalent"])
        self.assertIn("P/Chart: steps differ", report["Differences"])

    def test_changed_branch_type_is_reported(self):
        report = self.compare_documents(
            document(), document(branch_type="Selection")
        )
        self.assertFalse(report["Equivalent"])
        self.assertIn("P/Chart: branches differ", report["Differences"])

    def test_changed_execution_setting_is_reported(self):
        report = self.compare_documents(
            document(),
            document(
                settings='SFCExecutionControl="UntilFalse" '
                'SFCRestartPosition="InitialStep" SFCLastScan="DontScan"'
            ),
        )
        self.assertFalse(report["Equivalent"])
        self.assertIn(
            "controller SFCExecutionControl: 'CurrentActive' vs 'UntilFalse'",
            report["Differences"],
        )

    def test_a_dropped_chart_is_reported(self):
        without = document().replace('Type="SFC"', 'Type="ST"')
        report = self.compare_documents(document(), without)
        self.assertFalse(report["Equivalent"])
        self.assertIn(
            "chart only in the first document: P/Chart", report["Differences"]
        )

    def test_unresolvable_branch_fails_closed(self):
        # a branch wired only to another branch cannot be named, so the tool
        # must refuse rather than claim a comparison
        orphan = document().replace(
            '<DirectedLink FromID="1" ToID="4" Show="true"/>', ""
        ).replace(
            '<DirectedLink FromID="4" ToID="5" Show="true"/>',
            '<Branch ID="900" Y="90" BranchType="Simultaneous" BranchFlow="Converge">'
            '<Leg ID="901"/><Leg ID="902"/></Branch>'
            '<DirectedLink FromID="901" ToID="902" Show="true"/>',
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "orphan.L5X"
            path.write_text(orphan, encoding="utf-8")
            with self.assertRaisesRegex(ChartError, "not resolvable"):
                chart_model(path)


if __name__ == "__main__":
    unittest.main()

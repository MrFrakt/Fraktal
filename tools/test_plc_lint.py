import tempfile
import unittest

_NL = chr(10)
from pathlib import Path

from tools.plc_lint import (
    _parse_dart_enum,
    _parse_plc_enum,
    iter_sources,
    lint_file,
    lint_repository,
)


def _pou(name: str, declaration: str, body: str = "", methods: str = "") -> str:
    return f'''<?xml version="1.0" encoding="utf-8"?>
<TcPlcObject><POU Name="{name}" Id="{{00000000-0000-0000-0000-{name[-1:].encode().hex():0>12}}}">
<Declaration><![CDATA[{declaration}]]></Declaration>
<Implementation><ST><![CDATA[{body}]]></ST></Implementation>
{methods}</POU></TcPlcObject>'''


def _method(name: str, code: str) -> str:
    return f'''<Method Name="{name}" Id="{{10000000-0000-0000-0000-{name[-1:].encode().hex():0>12}}}">
<Declaration><![CDATA[METHOD PROTECTED {name} : DINT]]></Declaration>
<Implementation><ST><![CDATA[{code}]]></ST></Implementation></Method>'''


def _contract(extra: str = "") -> str:
    return f'''VAR_INPUT
    ParCfg : ST_TestParCfg;
    ParCmd : DINT;
END_VAR
VAR_OUTPUT
    OutCmd : DINT;
    OutImm : DINT;
END_VAR
{extra}'''


class PlcLintConformanceTests(unittest.TestCase):
    def _root(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def _write(self, root: Path, relative: str, text: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _rules(self, root: Path):
        return {finding.rule for finding in lint_repository([root])}

    def test_d1_contract_and_schema_negative_fixtures(self):
        root = self._root()
        self._write(root, "Framework/FB_Bad.TcPOU", _pou(
            "FB_Bad", "FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase",
            "Cyclic();"))
        self._write(root, "Framework/ST_BadParCfg.TcDUT", '''<TcPlcObject>
<DUT Name="ST_BadParCfg"><Declaration><![CDATA[TYPE ST_BadParCfg : STRUCT
Speed : LREAL; SchemaVersion : UINT; END_STRUCT END_TYPE]]></Declaration></DUT>
</TcPlcObject>''')
        self.assertIn("D1", self._rules(root))

    def test_h1_hook_and_body_negative_fixtures(self):
        root = self._root()
        declaration = "FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase\n" + _contract()
        self._write(root, "Framework/FB_Bad.TcPOU", _pou(
            "FB_Bad", declaration, "Cyclic(); OutCmd := 1;",
            _method("OnInit", "OnInit := 0;")))
        self.assertIn("H1", self._rules(root))

    def test_c5_case_requires_else(self):
        root = self._root()
        declaration = "FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase\n" + _contract()
        self._write(root, "Framework/FB_Bad.TcPOU", _pou(
            "FB_Bad", declaration, "Cyclic();",
            _method("M_Check", "CASE OutCmd OF 0: OutCmd := 1; END_CASE")))
        self.assertIn("C5", self._rules(root))

    def test_c2_rejects_reserved_enum_member(self):
        for keyword in ("TIME", "CLASS"):
            root = self._root()
            path = self._write(root, "Framework/E_Bad.TcDUT", f'''<TcPlcObject>
<DUT Name="E_Bad"><Declaration><![CDATA[{{attribute 'qualified_only'}}
TYPE E_Bad : (READY := 0, {keyword} := 1) DINT; END_TYPE
]]></Declaration></DUT></TcPlcObject>''')
            with self.subTest(keyword=keyword):
                self.assertIn("C2", {finding.rule for finding in lint_file(path)})

    def test_c2_rejects_iec_standard_function_names_as_identifiers(self):
        # A METHOD input named `Sub` parsed as the subtraction operator and
        # produced ~40 cascading syntax errors on innocent lines. The word list
        # had been inconsistent: MOD/MAX/MIN were present, ADD/SUB/DIV were not.
        # Variable identifiers only — a qualified enum member does not collide
        # (E_CylinderPosition.MID compiles), so RESERVED_FUNCTIONS is not applied
        # to enum members.
        for keyword in ("Sub", "Add", "Len", "Sel"):
            root = self._root()
            path = self._write(root, "Framework/FB_Bad.TcPOU", _pou(
                "FB_Bad", "FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase",
                "Cyclic();",
                f'''<Method Name="M_Take" Id="{{10000000-0000-0000-0000-00000000000e}}">
<Declaration><![CDATA[METHOD M_Take : DINT
VAR_INPUT
    {keyword} : REFERENCE TO FB_SequenceBase;
END_VAR]]></Declaration>
<Implementation><ST><![CDATA[;]]></ST></Implementation></Method>'''))
            with self.subTest(keyword=keyword):
                self.assertIn("C2", {f.rule for f in lint_file(path)})

    def test_c2_allows_a_function_name_as_a_qualified_enum_member(self):
        # E_CylinderPosition.MID is real, shipped and compiles: qualification
        # keeps it clear of the MID() string function.
        root = self._root()
        path = self._write(root, "Framework/E_Pos.TcDUT", '''<TcPlcObject>
<DUT Name="E_Pos"><Declaration><![CDATA[{attribute 'qualified_only'}
TYPE E_Pos : (LOW := 0, MID := 1, HIGH := 2) DINT; END_TYPE
]]></Declaration></DUT></TcPlcObject>''')
        self.assertNotIn("C2", {f.rule for f in lint_file(path)})

    def test_c6_rejects_string_case_labels(self):
        root = self._root()
        declaration = "FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase\n" + _contract()
        self._write(root, "Framework/FB_Bad.TcPOU", _pou(
            "FB_Bad", declaration, "Cyclic();",
            _method("M_Check",
                    "CASE TextValue OF\n'0': OutCmd := 1;\nELSE OutCmd := 0;\nEND_CASE")))
        self.assertIn("C6", self._rules(root))

    def test_c7_rejects_null_call_guarded_by_the_same_condition(self):
        # The real defect from FB_AsciiDeviceCM.SendRequest: without
        # short-circuit evaluation _chan.State() is called when _chan is 0.
        root = self._root()
        declaration = "FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase\n" + _contract()
        self._write(root, "Framework/FB_Bad.TcPOU", _pou(
            "FB_Bad", declaration, "Cyclic();",
            _method("M_Send",
                    "IF _chan = 0 OR (_chan.State() <> 1) THEN\nRETURN;\nEND_IF")))
        self.assertIn("C7", self._rules(root))

    def test_c7_rejects_one_based_index_guarded_by_the_same_condition(self):
        # The real defect from FB_LocalRecipeProvider.Load: _size[0] is read on
        # the ordinary not-found path.
        root = self._root()
        declaration = ("FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase\n"
                       "VAR\n_size : ARRAY[1..16] OF UDINT;\nEND_VAR\n" + _contract())
        self._write(root, "Framework/FB_Bad.TcPOU", _pou(
            "FB_Bad", declaration, "Cyclic();",
            _method("M_Load",
                    "IF (hit = 0) OR (_size[hit] <> Size) THEN\nRETURN;\nEND_IF")))
        self.assertIn("C7", self._rules(root))

    def test_c7_accepts_the_split_guard(self):
        # The shipped fix: sentinel test in its own statement.
        root = self._root()
        declaration = ("FUNCTION_BLOCK FB_Good EXTENDS FB_ControlModuleBase\n"
                       "VAR\n_size : ARRAY[1..16] OF UDINT;\nEND_VAR\n" + _contract())
        self._write(root, "Framework/FB_Good.TcPOU", _pou(
            "FB_Good", declaration, "Cyclic();",
            _method("M_Load",
                    "IF hit = 0 THEN\nRETURN;\nEND_IF\n"
                    "IF _size[hit] <> Size THEN\nRETURN;\nEND_IF")))
        self.assertNotIn("C7", self._rules(root))

    def test_pou_qualifiers_do_not_hide_inheritance(self):
        # `FUNCTION_BLOCK INTERNAL FB_X EXTENDS FB_SequenceBase` used to parse as
        # name="INTERNAL" with no base, so every inheritance-keyed rule silently
        # skipped the object. A rule that does not apply must not look like a pass.
        root = self._root()
        self._write(root, "Fraktal_Press_Demo/FB_QualBad.TcPOU", _pou(
            "FB_QualBad",
            "FUNCTION_BLOCK INTERNAL FB_QualBad EXTENDS FB_SequenceBase", ""))
        self.assertIn("S1", self._rules(root))

    def test_s1_chart_body_is_not_held_to_the_st_skeleton(self):
        # An SFC chart's runtime owns the transition, so CASE _step OF / M_Advance
        # are the wrong requirement; it must still carry the shared result, record
        # steps, and clear the result once per scan.
        root = self._root()
        good = _pou("FB_Chart", "FUNCTION_BLOCK FB_Chart EXTENDS FB_SequenceBase", "")
        good = good.replace("<ST><![CDATA[]]></ST>",
                            "<SFC><![CDATA[_retVal M_Step(]]></SFC>")
        self._write(root, "Fraktal_Press_Demo/FB_Chart.TcPOU", good)
        self.assertNotIn("S1", self._rules(root))

    def test_s1_ladder_chain_uses_the_integer_state_machine_contract(self):
        # TwinCAT writes a ladder body as <LADDER>, not <LD>. Missing that spelling
        # made S1 demand the ST skeleton of every ladder chain. A ladder chain's
        # rungs dispatch but do not evaluate transitions, so unlike SFC its actions
        # still commit through M_Advance.
        root = self._root()
        good = _pou("FB_Rung", "FUNCTION_BLOCK FB_Rung EXTENDS FB_SequenceBase", "")
        good = good.replace("<ST><![CDATA[]]></ST>",
                            "<LADDER><![CDATA[_retVal M_Step( M_Advance(]]></LADDER>")
        self._write(root, "Fraktal_Press_Demo/FB_Rung.TcPOU", good)
        self.assertNotIn("S1", self._rules(root))

    def test_l1_library_type_no_library_object_owns_is_rejected(self):
        # ST_PneumaticPress* sat in Fraktal_Modules while only the press project
        # used them: every consumer of the library carried four structs for a
        # machine they do not have.
        root = self._root()
        self._write(root, "Framework/Fraktal_Modules/DUTs/ST_OnlyAppUses.TcDUT",
                    "<TcPlcObject><DUT Name=\"ST_OnlyAppUses\"><Declaration>"
                    "<![CDATA[TYPE ST_OnlyAppUses : STRUCT x : BOOL; END_STRUCT END_TYPE]]>"
                    "</Declaration></DUT></TcPlcObject>")
        self._write(root, "Fraktal_Press_Demo/FB_App.TcPOU", _pou(
            "FB_App", "FUNCTION_BLOCK FB_App" + _NL + "VAR" + _NL
            + "  d : ST_OnlyAppUses;" + _NL + "END_VAR"))
        self.assertIn("L1", self._rules(root))

    def test_l1_accepts_a_type_another_library_owns(self):
        # Cross-library ownership is correct layering: ST_IoPointIdentity lives
        # in Fraktal_Core and is owned by Fraktal_Modules. Only "no library at
        # all" is misfiling.
        root = self._root()
        self._write(root, "Framework/Fraktal_Core/DUTs/ST_Shared.TcDUT",
                    "<TcPlcObject><DUT Name=\"ST_Shared\"><Declaration>"
                    "<![CDATA[TYPE ST_Shared : STRUCT x : BOOL; END_STRUCT END_TYPE]]>"
                    "</Declaration></DUT></TcPlcObject>")
        self._write(root, "Framework/Fraktal_Modules/FB_Owner.TcPOU", _pou(
            "FB_Owner", "FUNCTION_BLOCK FB_Owner" + _NL + "VAR" + _NL
            + "  d : ST_Shared;" + _NL + "END_VAR"))
        self.assertNotIn("L1", self._rules(root))

    def test_l1_accepts_ownership_through_array_of(self):
        # ST_BusNode owns ST_IoChannel as `ARRAY[..] OF`; matching only `: Name`
        # made three correctly-placed Core types look misfiled.
        root = self._root()
        self._write(root, "Framework/Fraktal_Core/DUTs/ST_Elem.TcDUT",
                    "<TcPlcObject><DUT Name=\"ST_Elem\"><Declaration>"
                    "<![CDATA[TYPE ST_Elem : STRUCT x : BOOL; END_STRUCT END_TYPE]]>"
                    "</Declaration></DUT></TcPlcObject>")
        self._write(root, "Framework/Fraktal_Core/DUTs/ST_Holder.TcDUT",
                    "<TcPlcObject><DUT Name=\"ST_Holder\"><Declaration>"
                    "<![CDATA[TYPE ST_Holder : STRUCT items : ARRAY[1..4] OF ST_Elem; END_STRUCT END_TYPE]]>"
                    "</Declaration></DUT></TcPlcObject>")
        self._write(root, "Fraktal_Press_Demo/FB_App3.TcPOU", _pou(
            "FB_App3", "FUNCTION_BLOCK FB_App3" + _NL + "VAR" + _NL
            + "  d : ST_Elem;" + _NL + "END_VAR"))
        self.assertNotIn("L1", self._rules(root))

    def test_s1_ladder_may_drive_step_directly(self):
        # The integer-state-machine form: a rung MOVEs the next state into _step.
        # It needs neither _retVal nor M_Advance, and demanding them would have
        # forced a rung through a transition mechanism ladder does not use.
        root = self._root()
        good = _pou("FB_Rung2", "FUNCTION_BLOCK FB_Rung2 EXTENDS FB_SequenceBase", "")
        good = good.replace("<ST><![CDATA[]]></ST>",
                            '<LADDER><![CDATA[<v n="BoxType">"M_Step"</v>'
                            '<v n="Operand">"_step"</v>]]></LADDER>')
        self._write(root, "Fraktal_Press_Demo/FB_Rung2.TcPOU", good)
        self.assertNotIn("S1", self._rules(root))

    def test_s1_chart_that_cannot_progress_at_all_is_rejected(self):
        # Records steps but has no way to leave one: no M_Advance, no _retVal for a
        # chart runtime to read, no _step for a rung to write.
        root = self._root()
        bad = _pou("FB_Rung3", "FUNCTION_BLOCK FB_Rung3 EXTENDS FB_SequenceBase", "")
        bad = bad.replace("<ST><![CDATA[]]></ST>",
                          '<LADDER><![CDATA[<v n="BoxType">"M_Step"</v>]]></LADDER>')
        self._write(root, "Fraktal_Press_Demo/FB_Rung3.TcPOU", bad)
        self.assertIn("S1", self._rules(root))

    def test_s1_follows_the_inheritance_chain_to_fb_sequencebase(self):
        # FB_SequenceBaseLd sits between the ladder chains and FB_SequenceBase.
        # A direct-equality test on the base name skipped every POU behind it, so
        # the ladder chain was never checked at all.
        root = self._root()
        self._write(root, "Framework/FB_MidBase.TcPOU", _pou(
            "FB_MidBase", "FUNCTION_BLOCK ABSTRACT FB_MidBase EXTENDS FB_SequenceBase", ""))
        self._write(root, "Fraktal_Press_Demo/FB_Chain.TcPOU", _pou(
            "FB_Chain", "FUNCTION_BLOCK FB_Chain EXTENDS FB_MidBase", ""))
        self.assertIn("S1", self._rules(root))

    def test_s1_skips_abstract_bases(self):
        # An ABSTRACT base is scaffolding, not a chain: it carries no steps.
        root = self._root()
        self._write(root, "Framework/FB_AbstractBase.TcPOU", _pou(
            "FB_AbstractBase",
            "FUNCTION_BLOCK ABSTRACT FB_AbstractBase EXTENDS FB_SequenceBase", ""))
        self.assertNotIn("S1", self._rules(root))

    def test_s1_accepts_a_network_list_ladder_body(self):
        # TwinCAT stores a ladder body as <NWL> and a call appears as a BoxType
        # string ("M_Step"), never the ST call syntax "M_Step(".
        root = self._root()
        good = _pou("FB_Nwl", "FUNCTION_BLOCK FB_Nwl EXTENDS FB_SequenceBase", "")
        good = good.replace("<ST><![CDATA[]]></ST>",
                            '<NWL><![CDATA[<v n="BoxType">"M_Step"</v>'
                            '<v n="BoxType">"M_Advance"</v>_retVal]]></NWL>')
        self._write(root, "Fraktal_Press_Demo/FB_Nwl.TcPOU", good)
        self.assertNotIn("S1", self._rules(root))

    def test_s1_chart_still_needs_the_shared_result_and_step_record(self):
        # A chart object can only prove what it contains. The per-scan clear is
        # the owner's call (M_BeginScan) or an editor-wired exit action, neither
        # of which is visible here - so S1 checks the two things that are.
        root = self._root()
        bad = _pou("FB_Chart2", "FUNCTION_BLOCK FB_Chart2 EXTENDS FB_SequenceBase", "")
        bad = bad.replace("<ST><![CDATA[]]></ST>", "<SFC><![CDATA[nothing useful]]></SFC>")
        self._write(root, "Fraktal_Press_Demo/FB_Chart2.TcPOU", bad)
        self.assertIn("S1", self._rules(root))

    def test_s1_sequence_skeleton_negative_fixture(self):
        root = self._root()
        self._write(root, "Fraktal_Press_Demo/FB_BadSeq.TcPOU", _pou(
            "FB_BadSeq", "FUNCTION_BLOCK FB_BadSeq EXTENDS FB_SequenceBase",
            "", _method("M_Run", "CASE _step OF 0: _retVal := E_StepResult.ADVANCE; ELSE RETURN; END_CASE")))
        self.assertIn("S1", self._rules(root))

    def test_a1_em_cannot_contain_unit(self):
        root = self._root()
        self._write(root, "Framework/FB_TestUnit.TcPOU", _pou(
            "FB_TestUnit", "FUNCTION_BLOCK FB_TestUnit EXTENDS FB_UnitBase\n" + _contract(),
            "Cyclic();"))
        self._write(root, "Framework/FB_TestEM.TcPOU", _pou(
            "FB_TestEM", "FUNCTION_BLOCK FB_TestEM EXTENDS FB_EquipmentModuleBase\n" +
            _contract("Child : FB_TestUnit;"), "Cyclic();"))
        self.assertIn("A1", self._rules(root))

    def test_r1_reason_band_and_collision(self):
        root = self._root()
        for index, value in ((1, 9999), (2, 9999)):
            self._write(root, f"Framework/PL_Type{index}Reasons.TcGVL", f'''<TcPlcObject>
<GVL Name="PL_Type{index}Reasons"><Declaration><![CDATA[VAR_GLOBAL CONSTANT
BAD_REASON : DINT := {value}; END_VAR]]></Declaration></GVL></TcPlcObject>''')
        self.assertIn("R1", self._rules(root))

    def test_e1_enum_parsers_expose_reordering(self):
        plc = "TYPE E_Test : (READY := 0, BUSY := 1) DINT; END_TYPE"
        dart = "enum Test { busy, ready }"
        self.assertEqual(_parse_plc_enum(plc, "E_Test"),
                         [("READY", 0), ("BUSY", 1)])
        self.assertEqual(_parse_dart_enum(dart, "Test"), ["busy", "ready"])

    def test_p1_compile_coverage_and_root_marker(self):
        root = self._root()
        app = root / "Fraktal_Demo"
        unit = self._write(root, "Fraktal_Demo/FB_TestUnit.TcPOU", _pou(
            "FB_TestUnit", "FUNCTION_BLOCK FB_TestUnit EXTENDS FB_UnitBase\n" + _contract(),
            "Cyclic();"))
        main = self._write(root, "Fraktal_Demo/MAIN.TcPOU", _pou(
            "MAIN", "PROGRAM MAIN\nVAR\nRoot : FB_TestUnit;\nEND_VAR", "Root();"))
        self._write(root, "Fraktal_Demo/Fraktal_Demo.plcproj", f'''<Project>
<Compile Include="{unit.name}"/><Compile Include="{main.name}"/></Project>''')
        self.assertIn("P1", self._rules(root))

    def test_p1_common_ancestor_manifest_owns_only_matching_source_folder(self):
        # TwinCAT rejects '..' in linked Compile paths, so an aggregate manifest
        # must be allowed at the common ancestor without claiming every sibling
        # project's authored files as its own.
        root = self._root()
        runner = self._write(root,
            "Tests/Fraktal_Tests/PRG_TcUnitRunner.TcPOU",
            _pou("PRG_TcUnitRunner", "PROGRAM PRG_TcUnitRunner", ""))
        linked = self._write(root,
            "Examples/Fraktal_Press_Demo/PRG_Linked.TcPOU",
            _pou("PRG_Linked", "PROGRAM PRG_Linked", ""))
        demo = self._write(root,
            "Examples/Fraktal_Demo/MAIN.TcPOU",
            _pou("MAIN", "PROGRAM MAIN", ""))
        self._write(root, "Fraktal_Tests.plcproj", f'''<Project>
<Compile Include="Tests\\Fraktal_Tests\\{runner.name}"/>
<Compile Include="Examples\\Fraktal_Press_Demo\\{linked.name}"/></Project>''')
        self._write(root,
            "Examples/Fraktal_Press_Demo/Fraktal_Press_Demo.plcproj",
            f'<Project><Compile Include="{linked.name}"/></Project>')
        self._write(root, "Examples/Fraktal_Demo/Fraktal_Demo.plcproj",
            f'<Project><Compile Include="{demo.name}"/></Project>')
        self.assertNotIn("P1", self._rules(root))

    def test_p1_rejects_parent_relative_compile_include(self):
        root = self._root()
        linked = self._write(root, "Sibling/PRG_Linked.TcPOU",
            _pou("PRG_Linked", "PROGRAM PRG_Linked", ""))
        self._write(root, "Aggregate/Aggregate.plcproj", f'''<Project>
<Compile Include="..\\Sibling\\{linked.name}"/></Project>''')
        self.assertIn("P1", self._rules(root))

    def test_p1_rejects_duplicate_source_loaded_by_two_xae_plc_projects(self):
        root = self._root()
        shared = self._write(root, "Fixture/Shared/PRG_Shared.TcPOU",
            _pou("PRG_Shared", "PROGRAM PRG_Shared", ""))
        for name in ("App", "Tests"):
            self._write(root, f"Fixture/{name}.plcproj", f'''<Project>
<Compile Include="Shared\\{shared.name}"/></Project>''')
        self._write(root, "Fixture/Both.tsproj", '''<TcSmProject><Project><Plc>
<Project PrjFilePath="App.plcproj"/><Project PrjFilePath="Tests.plcproj"/>
</Plc></Project></TcSmProject>''')
        self.assertIn("P1", self._rules(root))

    def _borrowing_fixture(self, root: Path, borrow_the_dut: bool):
        """Bench owns a Unit plus the DUT it declares; BenchTests borrows them.

        This is the PressTests/Fraktal_Press_Demo shape: the test manifest links
        the shipping Unit source directly rather than copying it.
        """
        self._write(root, "Bench/DUTs/ST_BenchParCfg.TcDUT", '''<TcPlcObject>
<DUT Name="ST_BenchParCfg"><Declaration><![CDATA[TYPE ST_BenchParCfg : STRUCT
SchemaVersion : UINT; Speed : LREAL; END_STRUCT END_TYPE]]></Declaration></DUT>
</TcPlcObject>''')
        self._write(root, "Bench/FB_BenchUnit.TcPOU", _pou(
            "FB_BenchUnit",
            "FUNCTION_BLOCK FB_BenchUnit EXTENDS FB_UnitBase" + _NL
            + "VAR" + _NL + "Cfg : ST_BenchParCfg;" + _NL + "END_VAR",
            "Cyclic();"))
        self._write(root, "Bench/Bench.plcproj", '''<Project>
<Compile Include="DUTs\\ST_BenchParCfg.TcDUT"/>
<Compile Include="FB_BenchUnit.TcPOU"/></Project>''')
        self._write(root, "BenchTests/FB_Bench_Tests.TcPOU", _pou(
            "FB_Bench_Tests",
            "FUNCTION_BLOCK FB_Bench_Tests" + _NL + "VAR" + _NL
            + "Unit : FB_BenchUnit;" + _NL + "END_VAR", ""))
        borrowed_dut = ('<Compile Include="Bench\\DUTs\\ST_BenchParCfg.TcDUT"/>'
                        if borrow_the_dut else "")
        self._write(root, "BenchTests.plcproj", f'''<Project>
<Compile Include="BenchTests\\FB_Bench_Tests.TcPOU"/>
<Compile Include="Bench\\FB_BenchUnit.TcPOU"/>
{borrowed_dut}</Project>''')

    def test_p2_rejects_incomplete_cross_project_borrowing(self):
        # The historical break: a DUT moves INTO the lender's tree, the lender's
        # own manifest gains it (so P1 stays green), and the borrower does not.
        root = self._root()
        self._borrowing_fixture(root, borrow_the_dut=False)
        self.assertIn("P2", self._rules(root))

    def test_p2_accepts_a_complete_borrow(self):
        root = self._root()
        self._borrowing_fixture(root, borrow_the_dut=True)
        self.assertNotIn("P2", self._rules(root))

    def test_p2_ignores_types_that_come_from_a_library_reference(self):
        # Framework types are consumed through an installed library, never
        # borrowed as source: a project that borrows nothing has no lender, and
        # one that borrows from a bench must not be judged against the library.
        root = self._root()
        self._borrowing_fixture(root, borrow_the_dut=True)
        self._write(root, "Framework/Fraktal_Core/ST_Diagnostic.TcDUT", '''<TcPlcObject>
<DUT Name="ST_Diagnostic"><Declaration><![CDATA[TYPE ST_Diagnostic : STRUCT
Reason : DINT; END_STRUCT END_TYPE]]></Declaration></DUT></TcPlcObject>''')
        self._write(root, "Framework/Fraktal_Core/Fraktal_Core.plcproj",
                    '<Project><Compile Include="ST_Diagnostic.TcDUT"/></Project>')
        self.assertNotIn("P2", self._rules(root))

    # ---- regression fixtures for the three rules corrected after the audit ----
    # Each pair proves the fix narrowed the rule to the CORRECT invariant rather
    # than disabling it: the legitimate pattern passes, the real defect still
    # fails. Before these, all three rules produced false positives against the
    # shipped tree while the fixture suite stayed green.

    def test_d1_accepts_contract_inherited_from_a_base(self):
        # 2.2: a device variant may declare none of the four itself and inherit
        # them (FB_Iv3VisionCM EXTENDS FB_TcpVisionCM). Must NOT be reported.
        root = self._root()
        self._write(root, "Framework/FB_Base.TcPOU", _pou(
            "FB_Base",
            "FUNCTION_BLOCK FB_Base EXTENDS FB_ControlModuleBase\n" + _contract(),
            "Cyclic();"))
        self._write(root, "Framework/FB_Variant.TcPOU", _pou(
            "FB_Variant", "FUNCTION_BLOCK FB_Variant EXTENDS FB_Base",
            "Cyclic();"))
        self.assertNotIn("D1", self._rules(root))

    def test_d1_still_fails_when_no_ancestor_declares_the_contract(self):
        root = self._root()
        self._write(root, "Framework/FB_Middle.TcPOU", _pou(
            "FB_Middle", "FUNCTION_BLOCK FB_Middle EXTENDS FB_ControlModuleBase",
            "Cyclic();"))
        self._write(root, "Framework/FB_Leaf.TcPOU", _pou(
            "FB_Leaf", "FUNCTION_BLOCK FB_Leaf EXTENDS FB_Middle", "Cyclic();"))
        self.assertIn("D1", self._rules(root))

    def test_c5_accepts_defaulted_target_with_guard(self):
        # The M_Advance idiom: safe default before, guard after. 5.6 asks for a
        # defined safe reaction, not empty ELSE boilerplate.
        root = self._root()
        declaration = "FUNCTION_BLOCK FB_Ok EXTENDS FB_ControlModuleBase\n" + _contract()
        self._write(root, "Framework/FB_Ok.TcPOU", _pou(
            "FB_Ok", declaration, "Cyclic();",
            _method("M_Advance2",
                    "target := -1;\n"
                    "CASE OutCmd OF\n 0: target := 10;\n 1: target := 20;\n"
                    "END_CASE\n"
                    "IF target >= 0 THEN OutCmd := target; END_IF")))
        self.assertNotIn("C5", self._rules(root))

    def test_c5_still_fails_without_a_guard(self):
        # Same shape but the result is used unguarded: an unmatched selector
        # silently keeps the default, which is the defect C5 exists to catch.
        root = self._root()
        declaration = "FUNCTION_BLOCK FB_Bad EXTENDS FB_ControlModuleBase\n" + _contract()
        self._write(root, "Framework/FB_Bad.TcPOU", _pou(
            "FB_Bad", declaration, "Cyclic();",
            _method("M_Check",
                    "target := -1;\n"
                    "CASE OutCmd OF\n 0: target := 10;\n END_CASE\n"
                    "OutCmd := target;")))
        self.assertIn("C5", self._rules(root))

    def test_s1_accepts_a_terminal_step_without_advance(self):
        # 6.8: the terminal step ends the chain (M_Complete / Done := TRUE) and
        # must not advance. Requiring M_Advance there inverts the contract.
        root = self._root()
        body = ("CASE _step OF\n"
                "  0: M_Step(); _retVal := 1; M_Advance(OnAdvance := 999);\n"
                "  999: M_Step(); M_Complete();\n"
                "END_CASE")
        self._write(root, "Framework/FB_Seq.TcPOU", _pou(
            "FB_Seq", "FUNCTION_BLOCK FB_Seq EXTENDS FB_SequenceBase",
            "", _method("M_Run", body)))
        self.assertNotIn("S1", self._rules(root))

    def test_s1_still_fails_when_a_mid_chain_step_cannot_advance(self):
        root = self._root()
        body = ("CASE _step OF\n"
                "  0: M_Step(); _retVal := 1; M_Advance(OnAdvance := 10);\n"
                "  10: M_Step();\n"
                "  999: M_Step(); M_Complete();\n"
                "END_CASE")
        self._write(root, "Framework/FB_Seq.TcPOU", _pou(
            "FB_Seq", "FUNCTION_BLOCK FB_Seq EXTENDS FB_SequenceBase",
            "", _method("M_Run", body)))
        self.assertIn("S1", self._rules(root))

    def test_linter_is_clean_against_the_real_repository(self):
        """The guard that was missing.

        The suite previously exercised only synthetic snippets, so every rule
        could pass its fixtures while failing against the tree it gates - which
        is exactly what happened (6 false positives, undetected). Running the
        real source here means a rule encoding the wrong invariant fails at the
        moment it is written, not after it blocks a release.
        """
        source = Path(__file__).resolve().parents[1] / "FraktalCore" / "PLC"
        if not source.exists():          # tooling copied out of the repo
            self.skipTest("PLC tree not present next to tools/")
        # Mirror main(): per-file rules take the profile, cross-file rules do not.
        for legacy in (False, True):
            findings = []
            for path in iter_sources([source]):
                findings.extend(lint_file(path, legacy_4024=legacy))
            findings.extend(lint_repository([source]))
            self.assertEqual(
                [], [str(f) for f in findings],
                f"linter must be clean against the shipped tree "
                f"(profile={'4024' if legacy else 'modern'})")

    def test_positive_module_fixture_is_clean_for_new_source_rules(self):
        root = self._root()
        declaration = "FUNCTION_BLOCK FB_Good EXTENDS FB_ControlModuleBase\n" + _contract()
        methods = _method("OnInit", "OnInit := SUPER^.OnInit();") + _method(
            "M_Check", "CASE OutCmd OF 0: OutCmd := 1; ELSE OutCmd := 0; END_CASE")
        self._write(root, "Framework/FB_Good.TcPOU", _pou(
            "FB_Good", declaration, "Cyclic();", methods))
        self._write(root, "Framework/ST_TestParCfg.TcDUT", '''<TcPlcObject>
<DUT Name="ST_TestParCfg"><Declaration><![CDATA[TYPE ST_TestParCfg : STRUCT
SchemaVersion : UINT; Speed : LREAL; END_STRUCT END_TYPE]]></Declaration></DUT>
</TcPlcObject>''')
        self.assertFalse(self._rules(root) & {"D1", "H1", "C5", "S1", "A1", "R1"})


if __name__ == "__main__":
    unittest.main()

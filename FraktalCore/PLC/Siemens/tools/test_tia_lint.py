"""Every tia_lint rule rejects a deliberately broken invariant in a copy of the
real S2 sources, and the unmodified tree is clean (Part IV §5.3; plan Phase 2
exit: "each deliberately broken invariant is rejected by a named rule").

    python -m unittest discover -s FraktalCore/PLC/Siemens/tools -t FraktalCore/PLC/Siemens/tools
"""

import pathlib
import shutil
import tempfile
import unittest
import importlib.util

import tia_lint

S2 = pathlib.Path(__file__).resolve().parents[1] / "Spikes" / "S2_Shape"


class TiaLintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        for f in S2.iterdir():
            if f.is_file():
                shutil.copy2(f, self.tmp / f.name)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def mutate(self, name, old, new, count=1):
        path = self.tmp / name
        text = path.read_text(encoding="ascii")
        self.assertEqual(text.count(old), count, "fixture drifted: %r not found %d time(s) in %s" % (old, count, name))
        path.write_text(text.replace(old, new), encoding="latin-1")

    def rules(self):
        return {f.rule for f in tia_lint.lint([self.tmp])}

    def assertRejected(self, rule):
        found = tia_lint.lint([self.tmp])
        self.assertIn(rule, {f.rule for f in found}, "expected %s, got %s" % (rule, [str(f) for f in found]))

    # ------------------------------------------------------------ baseline

    def test_unmodified_s2_tree_is_clean(self):
        self.assertEqual([str(f) for f in tia_lint.lint([self.tmp])], [])

    # --------------------------------------------------------------- rules

    def test_ascii(self):
        self.mutate("30_CylinderCM.scl", "// owner-supplied interlock", "// owner-supplied interlock \xe9")
        self.assertRejected("T-ASCII")

    def test_typefile_text_before_type(self):
        self.mutate("00_07_ST_HmiRequest.udt", 'TYPE "ST_HmiRequest"', '// header\nTYPE "ST_HmiRequest"')
        self.assertRejected("T-TYPEFILE")

    def test_typefile_two_types(self):
        path = self.tmp / "00_07_ST_HmiRequest.udt"
        path.write_text(path.read_text() + '\nTYPE "X"\nSTRUCT\n a : Int;\nEND_STRUCT;\nEND_TYPE\n')
        self.assertRejected("T-TYPEFILE")

    def test_case_without_else(self):
        # the device CASE's ELSE becomes a further label (the IF's ELSE stays)
        self.mutate("30_CylinderCM.scl", "\t            ELSE\n", "\t            11:\n")
        self.assertRejected("T-CASE")

    def test_keyword_member_unquoted(self):
        self.mutate("00_02_ST_ModuleStatus.udt", '"Name" :', "Name :")
        self.assertRejected("T-KEYWORD")

    def test_collide_case_only(self):
        self.mutate("50_Unit.scl", "   VAR CONSTANT\n", "   VAR CONSTANT\n      BUSY : DInt := 1;\n")
        self.assertRejected("T-COLLIDE")

    def test_collide_reserved_word(self):
        self.mutate("30_CylinderCM.scl", "      deltaRel : Real;", "      dt : Real;")
        self.assertRejected("T-COLLIDE")

    def test_ext_writable_beyond_mailbox(self):
        self.mutate("50_Unit.scl", "Mode { ExternalWritable := 'False'}", "Mode { ExternalWritable := 'True'}")
        self.assertRejected("T-EXT")

    def test_ext_private_static_published(self):
        self.mutate("50_Unit.scl",
                    "RunReq { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;",
                    "RunReq : Bool;")
        self.assertRejected("T-EXT")

    def test_frame_without_quiescent_guard(self):
        self.mutate("30_CylinderCM.scl", "AND NOT #Core.EvInit) THEN", "AND NOT #Core.EvInit AND TRUE) THEN")
        self.assertRejected("T-FRAME")

    def quiet_unit(self):
        fixture = S2.parent / "S3_Budget/make_fixture.py"
        spec = importlib.util.spec_from_file_location("s3_fixture", fixture)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        path = self.tmp / "50_Unit.scl"
        path.write_bytes(module.unit_quiet(path.read_text(encoding="ascii")).encode("ascii"))

    def test_unit_quiet_keeps_children_and_mailbox_live(self):
        self.quiet_unit()
        self.assertEqual([str(f) for f in tia_lint.lint([self.tmp])], [])
        self.mutate("50_Unit.scl", "#CylA(ParentIndex", "IF #LifecycleActive THEN\n#CylA(ParentIndex")
        self.mutate("50_Unit.scl", "Hal := #Hal.CylA);", "Hal := #Hal.CylA);\nEND_IF;")
        self.assertRejected("T-CYCLIC")

    def test_unit_quiet_rejects_changed_permit_and_conditional_mirror(self):
        self.quiet_unit()
        self.mutate("50_Unit.scl", "AND NOT #Core.EvInit);", "AND NOT #Core.EvInit AND #ModeActive = 0);")
        self.assertRejected("T-FRAME")

    def test_unit_quiet_rejects_conditional_published_mode(self):
        self.quiet_unit()
        self.mutate("50_Unit.scl", "#Mode := #ModeActive;", "IF #LifecycleActive THEN\n#Mode := #ModeActive;\nEND_IF;")
        self.assertRejected("T-FRAME")

    def test_unit_quiet_rejects_conditional_mailbox(self):
        self.quiet_unit()
        self.mutate("50_Unit.scl", "IF #HmiRequest.Sequence <> #MbLastSeq THEN", "IF #LifecycleActive THEN\nIF #HmiRequest.Sequence <> #MbLastSeq THEN")
        self.mutate("50_Unit.scl", "#HmiResponse.AckSequence := #HmiRequest.Sequence;", "#HmiResponse.AckSequence := #HmiRequest.Sequence;\nEND_IF;")
        self.assertRejected("T-FRAME")

    def test_unit_quiet_rejects_conditional_scan_clear(self):
        self.quiet_unit()
        self.mutate("50_Unit.scl", "#Seq.RetVal := 0;                              // per-scan", "IF #LifecycleActive THEN\n#Seq.RetVal := 0;\nEND_IF;                              // per-scan")
        self.assertRejected("T-FRAME")

    def test_unit_quiet_rejects_predicate_before_mailbox(self):
        self.quiet_unit()
        path = self.tmp / "50_Unit.scl"
        text = path.read_text(encoding="ascii")
        predicate = next(line for line in text.splitlines(keepends=True) if "#LifecycleActive :=" in line)
        text = text.replace(predicate, "", 1)
        text = text.replace("IF #HmiRequest.Sequence <> #MbLastSeq THEN", predicate + "IF #HmiRequest.Sequence <> #MbLastSeq THEN", 1)
        path.write_bytes(text.encode("ascii"))
        self.assertRejected("T-FRAME")

    def test_frame_end_twice(self):
        self.mutate("50_Unit.scl", '"FRK_End"(', '"FRK_End"(Core := #Core, Status := #Status, Busy => #Busy, Done => #Done, '
                    'Error => #Error, Aborted => #Aborted, ErrorID => #ErrorID);\n\t"FRK_End"(')
        self.assertRejected("T-FRAME")

    def test_cyclic_child_called_twice(self):
        path = self.tmp / "50_Unit.scl"
        text = path.read_text()
        call = next(line for line in text.splitlines() if line.strip().startswith("#CylA("))
        path.write_text(text.replace(call, call + "\n" + call, 1))
        self.assertRejected("T-CYCLIC")

    def test_core_written_by_authored_code(self):
        self.mutate("30_CylinderCM.scl", "                #Core.Step := 10;", "                #Core.Step := 10;\n                #Core.Exec := 2;")
        self.assertRejected("T-CORE")

    def test_ownio_reads_own_output(self):
        self.mutate("30_CylinderCM.scl", "    IF NOT #IntlkOk THEN", "    IF NOT #IntlkOk OR #Busy THEN")
        self.assertRejected("T-OWNIO")

    def test_ownio_writes_own_input(self):
        self.mutate("30_CylinderCM.scl", "                #Core.Step := 10;", "                #Core.Step := 10;\n                #Execute := FALSE;")
        self.assertRejected("T-OWNIO")

    def test_seq_step_without_advance(self):
        self.mutate("40_AutoSeq.scl", '"FRK_Seq_Advance"(OnAdvance := 120, OnJump1 := -1, Seq := #Seq);', ";")
        self.assertRejected("T-SEQ")

    def test_pending_rules_are_reported_never_passed(self):
        self.assertEqual(set(tia_lint.PENDING), {"T-TIER", "T-IO", "T-WIDTH", "T-GEN"})


if __name__ == "__main__":
    unittest.main()

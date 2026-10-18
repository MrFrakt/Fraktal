"""Compiler witnesses must fail closed, including licensing/tool failures."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_v38_native_gate as gate
import fraktal_ab_v38_native_probe as probe
from test_fraktal_ab_s12_type_probe import SEED


class CompilerResultTests(unittest.TestCase):
    def test_readback_summary_must_be_the_native_hosts_explicit_evidence(self):
        self.assertEqual(gate.readback_evidence('[INFO] Build succeeded'), {})
        self.assertEqual(gate.readback_evidence('{"Schema":"other"}'), {})
        output = ('[INFO] Build succeeded\n'
                  '{"Schema":"fraktal.ab.offline-probe-build-readback",'
                  '"InputUnchanged":true}')
        self.assertIs(gate.readback_evidence(output)["InputUnchanged"], True)

    def test_success_requires_the_build_event_and_successful_process(self):
        output = "[stamp][INFO][file] Build started\n[stamp][INFO][file] Build succeeded\n"
        self.assertIs(gate.build_result(0, output)["Accepted"], True)
        self.assertIs(gate.build_result(1, output)["Accepted"], False)
        self.assertIs(gate.build_result(0, "")["Accepted"], False)

    def test_negative_control_requires_an_actual_compiler_diagnostic(self):
        output = ("[stamp][INFO][file] Build started\n"
                  "[stamp][ERROR][file] RxSTX_E_INVALID_FUNC - Unknown instruction\n")
        result = gate.build_result(1, output)
        self.assertIs(result["Accepted"], False)
        self.assertIs(result["CompilerRejected"], True)
        self.assertIs(gate.build_result(1, output.replace(
            "RxSTX_E_INVALID_FUNC", "RxCMP_E_AUDIT_BADATTR"))["CompilerRejected"], True)
        self.assertIs(gate.build_result(1, "No valid license")["CompilerRejected"], False)
        self.assertIs(gate.build_result(1, "SDK not installed")["CompilerRejected"], False)
        self.assertIs(gate.build_result(1, "RxSTX_E_INVALID_FUNC")["CompilerRejected"], False)

    def test_sdk_error_cannot_be_hidden_by_a_zero_exit_code(self):
        output = ("[stamp][ERROR][file] tool failed\n"
                  "[stamp][INFO][file] Build succeeded\n")
        self.assertIs(gate.build_result(0, output)["Accepted"], False)


class ReadbackAndScopeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        seed = self.root / "seed.L5X"
        seed.write_text(SEED.replace("1769-L24ER-QB1B", "1756-L81E").replace(
            'MajorRev="33"', 'MajorRev="38"'), encoding="utf-8")
        self.report = probe.generate_all(seed, self.root / "generated")
        self.source = Path(self.report["Cases"][0]["Output"])
        self.sdk = self.root / "Fraktal.Ab.OfflineProbe.exe"
        self.sdk.write_text("not executable", encoding="utf-8")

    def test_readback_detects_narrowed_members_altered_logic_and_output_updates(self):
        original = gate.project_model(self.source)
        mutations = (
            ('DataType="INT"', 'DataType="DINT"'),
            ('DisableUpdateOutputs="true"', 'DisableUpdateOutputs="false"'),
            ('EntryStatus,', 'FaultCode,'),
        )
        source = self.source.read_text(encoding="utf-8")
        for old, new in mutations:
            with self.subTest(mutation=new):
                self.assertIn(old, source)
                mutant = self.root / "mutant.L5X"
                mutant.write_text(source.replace(old, new, 1), encoding="utf-8")
                self.assertNotEqual(original, gate.project_model(mutant))

    def test_readback_compares_st_even_when_the_editor_resplits_lines(self):
        original = gate.project_model(self.source)
        root = ET.parse(self.source)
        content = root.find("Controller/Programs/Program/Routines/Routine/STContent")
        statements = [part for line in content for part in (line.text or "").splitlines()]
        content.clear()
        for index, statement in enumerate(statements):
            ET.SubElement(content, "Line", Number=str(index)).text = statement
        export = self.root / "export.L5X"
        root.write(export, encoding="utf-8")
        self.assertEqual(original, gate.project_model(export))

    def test_changed_source_is_refused_before_the_sdk_or_output_directory(self):
        self.source.write_text("changed", encoding="utf-8")
        destination = self.root / "compiled"
        with patch.object(gate.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "source changed"):
                gate.compile_cases(self.report, destination, ("module_local",), sdk=self.sdk)
            run.assert_not_called()
        self.assertFalse(destination.exists())

    def test_unknown_case_or_target_cannot_execute(self):
        for cases, targets in (((), gate.TARGETS), (("not_generated",), gate.TARGETS),
                               (("module_local",), ("OnlineController",)),
                               (("module_local", "module_local"), gate.TARGETS)):
            with self.subTest(cases=cases, targets=targets):
                with patch.object(gate.subprocess, "run") as run:
                    with self.assertRaises(ValueError):
                        gate.compile_cases(self.report, self.root / "compiled",
                                           cases, targets, sdk=self.sdk)
                    run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

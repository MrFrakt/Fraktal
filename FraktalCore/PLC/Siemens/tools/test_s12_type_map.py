"""Reject narrowed Core fields and semantic differences in source round-trips."""
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1] / "Spikes/S12_TypeMap"


def module(name):
    spec = importlib.util.spec_from_file_location("s12_" + name, ROOT / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    try:
        spec.loader.exec_module(loaded)
    finally:
        sys.path.remove(str(ROOT))
    return loaded


VERIFY = module("verify_roundtrip")
BUILD = module("make_fixture")
SCALARS = module("verify_scalars")
RUN = module("run_plan")


class TypeMapTests(unittest.TestCase):
    def test_private_dtl_annotation_keeps_publication_flags_significant(self):
        original="Data {ExternalAccessible := 'False'; ExternalWritable := 'False'} : DTL;"
        native="Data {InstructionName := 'DTL'; LibVersion := '1.0'; ExternalAccessible := 'False'; ExternalWritable := 'False'} : DTL;"
        self.assertEqual(VERIFY.canonical(original),VERIFY.canonical(native))
        self.assertNotEqual(VERIFY.canonical(original),VERIFY.canonical(native.replace("ExternalWritable := 'False'","ExternalWritable := 'True'")))
        self.assertNotEqual(VERIFY.canonical(original),VERIFY.canonical(native.replace("LibVersion := '1.0'","LibVersion := '2.0'")))
    def test_comment_format_does_not_change_code(self):
        self.assertEqual(VERIFY.canonical('x := 1; // note\n'), VERIFY.canonical('X:=1;(* note *)'))
        self.assertNotEqual(VERIFY.canonical('X:=1;'), VERIFY.canonical('X:=2;'))

    def test_string_content_and_escaping_are_preserved(self):
        source = "X := 'A$'//B'; // actual comment\n"
        self.assertIn("'A$'//B'", VERIFY.canonical(source))
        self.assertNotEqual(VERIFY.canonical("X:='Key';"), VERIFY.canonical("X:='KEY';"))

    def test_bounds_and_qualifiers_cannot_disappear(self):
        self.assertNotEqual(VERIFY.canonical('X:Array[-2..2] of DInt;'), VERIFY.canonical('X:Array[0..2] of DInt;'))
        self.assertNotEqual(VERIFY.canonical("X {ExternalWritable:='False'} : DInt;"), VERIFY.canonical('X:DInt;'))

    def test_enum_values_are_explicit_and_strict(self):
        self.assertEqual(BUILD.enum_values('TYPE E_X : (A := -1, B := 7) DINT; END_TYPE'), {'A': -1, 'B': 7})
        with self.assertRaises(ValueError):
            BUILD.enum_values('TYPE E_X : (A := 0, B) DINT; END_TYPE')
        with self.assertRaises(ValueError):
            BUILD.enum_values('TYPE E_X : (A := 0, a := 1) DINT; END_TYPE')
        with self.assertRaises(ValueError):
            BUILD.enum_values('TYPE E_X : (A := 2147483648) DINT; END_TYPE')

    def test_unparsed_fields_are_refused(self):
        self.assertEqual(BUILD.COMMON.struct_fields('STRUCT\nFirst:UINT;\nNext: ARRAY[-2..2] OF DINT;\nEND_STRUCT'),
                         [('First', 'UINT'), ('Next', 'ARRAY[-2..2] OF DINT')])
        with self.assertRaises(ValueError):
            BUILD.COMMON.struct_fields('STRUCT\nFirst:UINT;\n"Quoted":DINT;\nEND_STRUCT')
        with self.assertRaises(ValueError):
            BUILD.COMMON.struct_fields('STRUCT\nFirst:UINT;\nFIRST:UINT;\nEND_STRUCT')

    def test_same_line_fields_and_private_attributes_survive(self):
        declaration = "STRUCT First:UINT; Next:BOOL;\n{attribute 'OPC.UA.DA' := '0'} Private:DINT; END_STRUCT"
        members = BUILD.COMMON.struct_members(declaration)
        self.assertEqual([member["name"] for member in members], ["First", "Next", "Private"])
        self.assertEqual([member["accessible"] for member in members], [True, True, False])
        with self.assertRaises(ValueError):
            BUILD.COMMON.struct_members("STRUCT First:UINT; {attribute 'Unknown' := '0'} Next:BOOL; END_STRUCT")

    def test_only_native_ob_inputs_are_ignored(self):
        native = 'ORGANIZATION_BLOCK "Main"\nVAR_INPUT Initial_Call:Bool; Remanence:Bool; END_VAR\nBEGIN X:=1; END_ORGANIZATION_BLOCK'
        exported = 'ORGANIZATION_BLOCK "Main"\nBEGIN X:=1; END_ORGANIZATION_BLOCK'
        self.assertEqual(VERIFY.canonical(native), VERIFY.canonical(exported))
        custom = native.replace('Remanence:Bool;', 'Remanence:Bool; UserFlag:Bool;')
        self.assertNotEqual(VERIFY.canonical(custom), VERIFY.canonical(exported))
        self.assertNotEqual(VERIFY.canonical(native.replace('ORGANIZATION_BLOCK', 'FUNCTION_BLOCK')),
                            VERIFY.canonical(exported.replace('ORGANIZATION_BLOCK', 'FUNCTION_BLOCK')))

    def test_packed_date_preserves_leap_day_and_rejects_invalid_bytes(self):
        packed = int.from_bytes(bytes.fromhex("2402292359580005"), "little")
        self.assertEqual(SCALARS.packed_dt(packed), SCALARS.STAMP)
        for corrupt in ("2402302359580005", "2402292359580006", "24022a2359580005"):
            with self.assertRaises(ValueError):
                SCALARS.packed_dt(int.from_bytes(bytes.fromhex(corrupt), "little"))

    def test_download_refuses_physical_target_and_adapter_mapping(self):
        status = {"name": "FrkS12", "cpu": "CPU1516", "comm": "TCPIP",
                  "addresses": ["169.254.212.49"], "ie1": 0, "ie2": 0, "ie3": 0}
        command = 'download --plc PLC_1 --pc-interface "Siemens PLCSIM Virtual Ethernet Adapter" --pc-number 1 --target "1 X1" --confirm-target 169.254.212.49'
        with tempfile.TemporaryDirectory() as directory:
            plan = pathlib.Path(directory) / "download.plan"
            for altered, mapping in ((command.replace("169.254.212.49", "192.168.0.10"), 0), (command, 2)):
                plan.write_bytes(altered.encode("ascii"))
                observed = dict(status, ie1=mapping)
                result = types.SimpleNamespace(returncode=0, stdout=json.dumps(observed).encode("ascii"))
                with mock.patch.object(RUN.subprocess, "run", return_value=result):
                    with self.assertRaises(ValueError):
                        RUN.guard_downloads(plan, [], io.BytesIO())
            plan.write_bytes(b"${download}")
            result = types.SimpleNamespace(returncode=0, stdout=json.dumps(status).encode("ascii"))
            with mock.patch.object(RUN.subprocess, "run", return_value=result) as process:
                RUN.guard_downloads(plan, ["download=" + command], io.BytesIO())
                self.assertEqual(process.call_count, 1)

    def test_unresolved_plan_refuses_before_any_process(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = pathlib.Path(directory) / "plan"
            plan.write_bytes(b"${download}")
            with mock.patch.object(RUN.subprocess, "run") as process:
                with self.assertRaises(ValueError):
                    RUN.guard_downloads(plan, [], io.BytesIO())
                process.assert_not_called()

    def test_ldt_candidate_preserves_contract_and_uses_scalar_wire_values(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "ldt"
            BUILD.generate(output)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["timestamp_representation"], "LDT")
            dates = [field for fields in manifest["types"].values() for field in fields
                     if field["core_type"] == "DT"]
            self.assertTrue(dates)
            self.assertTrue(all(field["native_type"] == "LDT" for field in dates))
            self.assertTrue(manifest["witness_encodings"])
            self.assertEqual(set(manifest["witness_encodings"].values()), {"ldt"})
            for path in manifest["witness_encodings"]:
                self.assertEqual(manifest["witnesses"][path], 1709251198123456789)
                self.assertFalse(any(name.startswith(path + ".") for name in manifest["witnesses"]))
            self.assertEqual(sum(len(fields) for fields in manifest["types"].values()), 611)  # + ST_IoChannel.UnitCode

    def test_unknown_timestamp_candidate_refuses_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "unsupported"
            with self.assertRaises(ValueError):
                BUILD.generate(output, "UnixDouble")
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()

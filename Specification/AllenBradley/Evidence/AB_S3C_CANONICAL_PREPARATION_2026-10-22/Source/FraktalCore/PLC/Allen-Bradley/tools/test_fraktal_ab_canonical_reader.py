"""S1 synthetic layouts plus immutable controller captures; no PLC writes."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_equivalence as equivalence

FIXTURES = Path(__file__).with_name("fixtures") / "canonical"


def member(name, code, offset, info=0):
    return dict(name=name, code=code, offset=offset, info=info)


def synthetic():
    """Synthetic wire model, deliberately not labelled a controller recording."""
    templates = [
        dict(handle=0x2D1, name="ArbitraryText", byteSize=20,
             members=[member("LEN", 0xC4, 0), member("DATA", 0x20C2, 4, 16)]),
        dict(handle=0x200, name="State", byteSize=28, members=[
            member("Name", 0x82D1, 0), member("ModuleType", 0xC4, 20), member("State", 0xC4, 24)]),
        dict(handle=0x300, name="Child", byteSize=8, members=[
            member("Flag", 0xC1, 0, 9), member("Value", 0xC4, 4)]),
        dict(handle=0x100, name="Module", byteSize=88, members=[
            member("Status", 0x8200, 0), member("Duration", 0xC4, 28),
            member("Bits", 0x20D3, 32, 1), member("Count", 0xC5, 40),
            member("Stamp", 0xCC, 48), member("Kids", 0xA300, 56, 2),
            member("End", 0xC4, 80)])]
    raw = bytearray(88)
    struct.pack_into("<i", raw, 0, 5)
    raw[4:9] = b"Mixer"
    struct.pack_into("<iiiI", raw, 20, 1, 0, 1500, 5)
    struct.pack_into("<qq", raw, 40, 9007199254740993, 1792413296123456789)
    raw[57] = 2
    struct.pack_into("<i", raw, 60, 7)
    struct.pack_into("<i", raw, 68, -9)
    raw[72:80] = b"padding!"  # A next-member-gap stride would read the wrong second child.
    struct.pack_into("<i", raw, 80, 42)
    manifest = dict(schemaMajor=6, valid=True, truncated=False, contentHash="SYNTHETIC", configRevision=1,
                    annotations={"Mixer/Duration": dict(logicalType="DURATION"),
                                 "Mixer/Stamp": dict(logicalType="TIMESTAMP"),
                                 "Mixer/Bits": dict(logicalType="BOOL", lowerBound=0, elementCount=3),
                                 "Mixer/Kids": dict(lowerBound=1, elementCount=2)})
    return dict(schema=reader.SCHEMA, schemaVersion=1, synthetic=True,
                symbols=[dict(name="Mixer", handle=0x100, arrayRank=0)], templates=templates,
                records=[dict(tag="Mixer", rawHex=raw.hex())], manifest=manifest,
                coherenceBefore=["SYNTHETIC", 1], coherenceAfter=["SYNTHETIC", 1])


class ReaderTests(unittest.TestCase):
    def test_discovery_types_bounds_full_handle_and_authoritative_stride(self):
        doc = reader.snapshot(synthetic())
        self.assertEqual(doc["values"]["Mixer/Count"], "9007199254740993")
        self.assertEqual(doc["values"]["Mixer/Stamp"], "2026-10-19T12:34:56.123456789Z")
        self.assertEqual(doc["values"]["Mixer/Duration"], 1500)
        self.assertEqual(doc["types"]["Mixer/Duration"], "Int32")
        self.assertEqual(doc["types"]["Mixer/Count"], "Int64")
        self.assertEqual([doc["values"][f"Mixer/Bits[{i}]"] for i in range(3)], [True, False, True])
        self.assertEqual(doc["values"]["Mixer/Kids[1]/Flag"], True)
        self.assertEqual(doc["values"]["Mixer/Kids[2]/Value"], -9)
        self.assertEqual(doc["moduleCount"], 1)
        self.assertNotIn("Mixer/Bits[3]", doc["values"])

    def test_no_status_no_discovery_and_root_identity_must_match(self):
        capture = synthetic()
        capture["symbols"][0]["handle"] = 0x300
        with self.assertRaisesRegex(ValueError, "top-level Status"):
            reader.snapshot(capture)
        capture = synthetic()
        capture["symbols"][0]["name"] = "Alias"
        capture["records"][0]["tag"] = "Alias"
        with self.assertRaisesRegex(ValueError, "browse name"):
            reader.snapshot(capture)

    def test_signed_nanoseconds_exact_boundaries_and_unset(self):
        self.assertEqual(reader.timestamp_ns(0), 0)
        self.assertEqual(reader.timestamp_ns(-1), "1969-12-31T23:59:59.999999999Z")
        self.assertEqual(reader.timestamp_ns(1), "1970-01-01T00:00:00.000000001Z")
        self.assertEqual(reader.timestamp_ns(1_000_000_000), "1970-01-01T00:00:01.000Z")
        self.assertEqual(reader.timestamp_ns(1_100_000_000), "1970-01-01T00:00:01.100Z")

    def test_missing_size_rejected_instead_of_inferred(self):
        capture = synthetic()
        del capture["templates"][2]["byteSize"]
        with self.assertRaisesRegex(ValueError, "attribute 5"):
            reader.snapshot(capture)

    def test_bad_len_utf8_nonfinite_and_truncation_fail_closed(self):
        for label, edit in [
            ("negative LEN", lambda r: struct.pack_into("<i", r, 0, -1)),
            ("oversized LEN", lambda r: struct.pack_into("<i", r, 0, 17)),
            ("invalid UTF8", lambda r: r.__setitem__(4, 255)),
        ]:
            with self.subTest(label=label):
                capture = synthetic()
                raw = bytearray.fromhex(capture["records"][0]["rawHex"])
                edit(raw)
                capture["records"][0]["rawHex"] = raw.hex()
                with self.assertRaises((ValueError, UnicodeDecodeError)):
                    reader.snapshot(capture)
        capture = synthetic()
        capture["records"][0]["rawHex"] = capture["records"][0]["rawHex"][:-2]
        with self.assertRaisesRegex(ValueError, "record length"):
            reader.snapshot(capture)
        capture = synthetic()
        capture["templates"][3]["members"][-1]["code"] = 0xCA
        raw = bytearray.fromhex(capture["records"][0]["rawHex"])
        struct.pack_into("<f", raw, 80, float("nan"))
        capture["records"][0]["rawHex"] = raw.hex()
        with self.assertRaisesRegex(ValueError, "non-finite"):
            reader.snapshot(capture)

    def test_unknown_types_cycles_missing_references_and_overruns(self):
        for code in (0xDD, 0x8100, 0x8FFF):
            capture = synthetic()
            capture["templates"][3]["members"][-1]["code"] = code
            with self.subTest(code=code), self.assertRaises(ValueError):
                reader.snapshot(capture)
        capture = synthetic()
        capture["templates"][2]["members"][-1]["offset"] = 8
        with self.assertRaisesRegex(ValueError, "extent"):
            reader.snapshot(capture)

    def test_manifest_required_bounds_count_type_and_coherence(self):
        edits = [lambda c: c["manifest"].update(schemaMajor=5),
                 lambda c: c["manifest"].update(truncated=True),
                 lambda c: c.update(coherenceAfter=["DIFFERENT", 1]),
                 lambda c: c["manifest"]["annotations"]["Mixer/Bits"].pop("lowerBound"),
                 lambda c: c["manifest"]["annotations"]["Mixer/Bits"].update(elementCount=33),
                 lambda c: c["manifest"]["annotations"]["Mixer/Kids"].update(elementCount=1),
                 lambda c: c["manifest"]["annotations"]["Mixer/Duration"].update(logicalType="TIMESTAMP"),
                 lambda c: c["manifest"]["annotations"].update({"Mixer/Ghost": {}})]
        for index, edit in enumerate(edits):
            capture = synthetic()
            edit(capture)
            with self.subTest(index=index), self.assertRaises(ValueError):
                reader.snapshot(capture)

    def test_multidimensional_arrays_are_explicitly_unsupported(self):
        capture = synthetic()
        capture["templates"][3]["members"][-2]["code"] = 0xC300
        with self.assertRaisesRegex(ValueError, "array rank"):
            reader.snapshot(capture)

    def test_template_size_reply_validates_per_attribute_status(self):
        response = bytes(46) + struct.pack("<BBBBHHHI", 0x83, 0, 0, 0, 1, 5, 0, 88)
        class Comm:
            def _cip_message(self, *args):
                self.request = args
                return b"read only"
        comm = Comm()
        comm.conn = SimpleNamespace(send=lambda request: (0, response))
        self.assertEqual(reader.template_byte_size(comm, 0x2D1), 88)
        self.assertEqual(comm.request, (3, 0x6C, 0x2D1, [5]))
        for packet in (response[:-1], response[:54] + b"\x01\x00" + response[56:]):
            comm.conn.send = lambda request, packet=packet: (0, packet)
            with self.assertRaises(ValueError):
                reader.template_byte_size(comm, 0x2D1)

    def test_live_seam_has_only_read_operations_and_serial_guard(self):
        capture = synthetic()
        objects, sizes = reader.template_objects(capture["templates"])
        tag = SimpleNamespace(TagName="Mixer", DataTypeValue=0x100, Struct=1, Array=0)
        class Comm:
            UDT = objects
            def GetDeviceProperties(self):
                return SimpleNamespace(Status="Success", Value=SimpleNamespace(SerialNumber="0x12345678"))
            def GetTagList(self, *, allTags):
                return SimpleNamespace(Status="Success", Value=[tag])
            def Read(self, name):
                if name != "Mixer":
                    raise AssertionError(name)
                return SimpleNamespace(Status="Success", Value=bytes.fromhex(capture["records"][0]["rawHex"]))
            def _cip_message(self, service, cls, handle, attributes):
                if (service, cls, attributes) != (3, 0x6C, [5]):
                    raise AssertionError("unexpected service")
                return handle
        comm = Comm()
        comm.conn = SimpleNamespace(send=lambda h: (0, bytes(46) + struct.pack(
            "<BBBBHHHI", 0x83, 0, 0, 0, 1, 5, 0, sizes[h])))
        doc, recorded = reader.read_document(comm, lambda *args: capture["manifest"], expect_serial="12345678")
        self.assertEqual(doc["values"]["Mixer/End"], 42)
        self.assertTrue(recorded["readOnly"])
        with self.assertRaisesRegex(ValueError, "serial guard"):
            reader.read_document(comm, lambda *args: capture["manifest"], expect_serial="87654321")
        calls = []
        def changing_manifest(*args):
            calls.append(1)
            if len(calls) == 2:
                capture["manifest"]["configRevision"] = 2
            return capture["manifest"]
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            reader.read_document(comm, changing_manifest, expect_serial="12345678")

    def test_cli_outputs_are_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            capture = Path(folder) / "capture.json"
            output = Path(folder) / "snapshot.json"
            capture.write_text(json.dumps(synthetic()), encoding="utf-8")
            tool = Path(reader.__file__)
            command = [sys.executable, str(tool), "--capture", str(capture), "--output", str(output)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(output.read_bytes(), before)

    def test_json_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON"):
                reader.load_json(path)


class EquivalenceTests(unittest.TestCase):
    def test_all_five_d2_corrections_and_no_other_reindexing(self):
        old = {"Plant/U/Status/ModuleType": 1, "Plant/U/Other[1]": 9}
        new = dict(old)
        for rule in equivalence.corrections():
            path = "Plant/U/" + rule["path"].removeprefix("<Unit>/")
            old[path + "[1]/Value"] = 7
            new[path + "[0]/Value"] = 7
        result = equivalence.compare_documents(dict(values=old, types={p: "Int32" for p in old}),
                                               dict(values=new, types={p: "Int32" for p in new}))
        self.assertTrue(result["equal"])
        self.assertTrue(result["typeAcceptance"])
        self.assertEqual(len(result["correctedPaths"]), 5)
        new["Plant/U/Other[0]"] = new.pop("Plant/U/Other[1]")
        self.assertFalse(equivalence.compare_documents(dict(values=old), dict(values=new), require_types=False)["equal"])

    def test_bool_int_float_and_exact_lreal_types_do_not_coerce(self):
        for old, new in ((True, 1), (1, 1.0), (3.141592653589793, 3.1415927410125732)):
            report = equivalence.compare_documents(dict(values={"P": old}), dict(values={"P": new}), require_types=False)
            self.assertFalse(report["equal"])
        doc = dict(values={"P": 1}, types={"P": "Int32"})
        other = dict(values={"P": 1}, types={"P": "Int16"})
        report = equivalence.compare_documents(doc, other)
        self.assertEqual(report["differences"][0]["kind"], "type")
        self.assertFalse(report["typeAcceptance"])

    def test_missing_extra_and_missing_transport_types_are_reported(self):
        report = equivalence.compare_documents(dict(values={"A": 1, "B": 2}), dict(values={"A": 1, "C": 3}))
        self.assertEqual({d["kind"] for d in report["differences"]}, {"missingCanonical", "extraCanonical", "missingType"})
        self.assertFalse(report["typeAcceptance"])

    def test_unstable_live_pair_rejected(self):
        with self.assertRaisesRegex(ValueError, "same-state"):
            equivalence.compare_live(lambda: dict(sameStateVerified=False))


class RecordedCaptureTests(unittest.TestCase):
    def test_fixture_hashes_and_storage_budget(self):
        manifest = reader.load_json(FIXTURES / "manifest.json")
        total = 0
        import gzip
        for row in manifest["captures"]:
            path = FIXTURES / row["file"]
            data = path.read_bytes()
            expanded = gzip.decompress(data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
            self.assertEqual(hashlib.sha256(expanded).hexdigest(), row["sourceSha256"])
            self.assertEqual(len(expanded), row["sourceBytes"])
            total += len(data)
        self.assertLessEqual(total, manifest["compressedBudgetBytes"])

    def test_recorded_s0_native_bytes_and_diagnostic_limitations(self):
        capture = reader.load_json(FIXTURES / "s0_raw_capture_02.json.gz")
        values = reader.replay_s0(capture)
        self.assertEqual(values["Big"], 72623859790382856)
        self.assertEqual(values["DurUs"], 1500000)
        self.assertEqual(values["Dur32"], 1500000)
        self.assertEqual(values["DurNs"], 1500000000)
        self.assertEqual(values["StampUsFromLint"], 1792413296123)
        self.assertEqual(values["StampNsFromLint"], 1792413296123456789)
        self.assertEqual(values["Wide"], 3.1415927410125732)
        self.assertEqual(values["Kids"][2]["Value"], -9)
        self.assertEqual(values["S80"]["LEN"], 3)
        self.assertEqual(bytes.fromhex(values["S80"]["bytes"]).decode("utf-8"), "Aé")
        self.assertNotIn("Status", values)
        with self.assertRaises(ValueError):
            reader.snapshot(capture)

    def test_all_47_s0_checks_reproduce_both_historical_findings(self):
        capture = reader.load_json(FIXTURES / "s0_raw_capture_02.json.gz")
        measured = reader.load_json(FIXTURES / "s0_measurement_replay_03.json.gz")
        decoded = reader.replay_s0(capture)
        findings = []
        for check in measured["checks"]:
            path = check["path"].split(".", 1)[1]
            value = decoded
            for name, index in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]", path):
                if name == "DATA" and isinstance(value, dict) and value.get("string"):
                    value = bytes.fromhex(value["bytes"])
                else:
                    value = value[name] if name else value[int(index)]
            if check["path"] == "bools.Flags":
                value = [i for i in range(len(value) * 32) if value[i // 32] >> (i % 32) & 1]
            previous = check["decoded"]
            if isinstance(previous, dict) and "asSignedLE" in previous:
                previous = previous["asSignedLE"]
            with self.subTest(path=path):
                self.assertEqual(value, previous)
                self.assertEqual(value == check["expected"], check["equal"])
            if value != check["expected"]:
                findings.append(check["path"])
        self.assertEqual(len(measured["checks"]), 47)
        self.assertEqual(findings, ["numbers.Wide", "dt_from_lint.StampUsFromLint"])

    def test_recorded_genealogy_projection_all_50_reads_4437_paths(self):
        tool = Path(__file__).with_name("fraktal_ab_projection_replay.py")
        run = subprocess.run([sys.executable, str(tool), str(FIXTURES / "genealogy_projection_01.json.gz")],
                             capture_output=True, text=True, timeout=40)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual((report["reads"], report["paths"]), (50, 4437))
        self.assertTrue(report["equal"])
        self.assertFalse(report["typeAcceptance"])


if __name__ == "__main__":
    unittest.main()

"""S0 supplement: generated layout, fragmented reads and bounded restoration."""
import copy
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_s0_supplementary_probe as probe
import fraktal_ab_s0_supplementary_measure as measure
import fraktal_ab_s0_supplementary_access as access
from test_fraktal_ab_s12_type_probe import SEED


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.seed = self.base / "seed.L5X"
        self.seed.write_text(SEED.replace("1769-L24ER-QB1B", "1756-L81E").replace('MajorRev="33"','MajorRev="38"'))

    def test_combined_root_access_contrasts_and_inert_task(self):
        report = probe.generate(self.seed, self.base / "outputs")
        case = next(row for row in report["cases"] if row["case"] == "combined")
        root = ET.parse(case["output"])
        tags = {t.get("Name"):t for t in root.findall("Controller/Tags/Tag")}
        self.assertEqual(tags["Press"].get("DataType"), probe.PREFIX + "Root")
        self.assertEqual(tags["Press"].get("ExternalAccess"), "Read Only")
        self.assertNotIn("FRK_S12_Probe", tags)
        for name, expected in probe.ACCESS_TAGS.items():
            self.assertEqual(tags[name].get("ExternalAccess"), expected)
        self.assertFalse(report["runtimeAccepted"])
        task = root.find("Controller/Tasks/Task")
        self.assertEqual((task.get("Rate"),task.get("DisableUpdateOutputs")),("10","true"))
        statements = "\n".join(n.text or "" for n in root.findall(".//STContent/Line"))
        self.assertNotIn("SSV(", statements)
        self.assertNotIn("Local:", statements)
        self.assertFalse(any(path in statements for path in probe.WRITE_PATHS))
        for path in probe.WRITE_PATHS:
            self.assertTrue(path.startswith(("FRK_S0S_AccessRO.","FRK_S0S_AccessRW.")))
        members = {t.get("Name"):{m.get("Name"):m.get("ExternalAccess") for m in t.findall("Members/Member")}
                   for t in root.findall("Controller/DataTypes/DataType")}
        self.assertEqual(members[probe.PREFIX+"Access"],dict(Readback="Read Only",HmiRequest="Read/Write"))
        self.assertEqual(members[probe.PREFIX+"PrivateAccess"]["Private"],"None")
        text=root.find(f"Controller/DataTypes/DataType[@Name='{probe.PREFIX}Text16']")
        self.assertEqual(text.find("Members/Member[@Name='DATA']").get("Radix"),"ASCII")

    def test_precision_initializers_are_typed_and_not_narrowed_to_real(self):
        report = probe.generate(self.seed,self.base/"out")
        root = ET.parse(next(r["output"] for r in report["cases"] if r["case"] == "literal"))
        values = {t.get("Name"):t.find("Data/DataValue") for t in root.findall("Controller/Tags/Tag")
                  if t.get("Name") in ("FRK_S0S_WideInit","FRK_S0S_NextInit")}
        self.assertEqual(values["FRK_S0S_WideInit"].get("DataType"),"LREAL")
        self.assertEqual(values["FRK_S0S_NextInit"].get("Value"),probe.NEXT_TEXT)
        self.assertNotEqual(probe.NEXT,struct.unpack("<f",struct.pack("<f",probe.NEXT))[0])

    def test_size_boundary_is_exact_and_seed_is_unchanged(self):
        before=self.seed.read_bytes()
        report=probe.generate(self.seed,self.base/"out")
        cases={row["case"]:row for row in report["cases"]}
        self.assertEqual(cases["limit"]["structureBytes"],2097152)
        self.assertEqual(cases["over_limit"]["structureBytes"],2097156)
        self.assertEqual(self.seed.read_bytes(),before)
        self.assertEqual(report["expectedSizes"]["FRK_S0S_Largest"],2097152)
        with self.assertRaisesRegex(ValueError,"existing"):
            probe.generate(self.seed,self.base/"out")


class FragmentTests(unittest.TestCase):
    def test_trace_rejects_gaps_overlaps_empty_fragments_and_missing_tail(self):
        good=[dict(service="0x4c",offset=0,payloadBytes=100,status=6),
              dict(service="0x52",offset=100,payloadBytes=40,status=0)]
        self.assertEqual(measure.verify_trace(good,140),dict(packets=2,fragmented=True,bytes=140))
        for field,value in (("offset",99),("offset",101),("payloadBytes",0),("status",6)):
            bad=copy.deepcopy(good);bad[1][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                measure.verify_trace(bad,140)
        with self.assertRaises(ValueError):measure.verify_trace(good,141)

    def test_trace_parses_native_payload_and_refuses_mutation_services(self):
        packet=bytes(46)+bytes([0xCC,0,0,0])+b"\xa0\x02\x34\x12"+bytes(8)
        comm=SimpleNamespace(conn=SimpleNamespace(send=lambda request:(0,packet)))
        original=comm.conn.send
        with measure.ReadTrace(comm) as trace:
            comm.conn.send(b"\x4c\x02\x91\x02AB\x01\x00")
            with self.assertRaisesRegex(ValueError,"non-read"):
                comm.conn.send(b"\x4d\x00")
        self.assertIs(comm.conn.send,original)
        self.assertEqual(trace[0]["payloadBytes"],8)
        self.assertEqual(measure.verify_trace(trace,8)["fragmented"],False)

    def test_all_size_bytes_including_middle_sentinel_are_checked(self):
        for blocks in (1,16,512):
            raw=bytearray(blocks*probe.BLOCK_BYTES)
            for index,value in zip((0,(blocks//2)*probe.BLOCK_WORDS+17,blocks*probe.BLOCK_WORDS-1),probe.SENTINELS):
                struct.pack_into("<i",raw,index*4,value)
            self.assertTrue(measure.check_size_bytes(raw,blocks))
            raw[123]^=1
            self.assertFalse(measure.check_size_bytes(raw,blocks))


class Fixture:
    def __init__(self, *, ro_child_writable=False, fail_after_write=False, valid=True):
        self.values=dict.fromkeys(probe.WRITE_PATHS,0)
        self.writes=[]
        self.ro_child_writable=ro_child_writable
        self.fail_after_write=fail_after_write
        self.valid=valid
    def GetDeviceProperties(self):
        return SimpleNamespace(Status="Success",Value=SimpleNamespace(SerialNumber="0x601fc87b",
            ProductName="Emulate 5580 Controller",ProductCode=288,Revision="38.11"))
    def Read(self,path):
        value=(probe.MAGIC if self.valid else 0) if path==probe.IDENTITY else self.values[path]
        return SimpleNamespace(Status="Success",Value=value)
    def Write(self,path,value,kind):
        if path not in probe.WRITE_PATHS or kind!=0xC4:
            raise AssertionError("out-of-scope write")
        self.writes.append(path)
        accepted=path.endswith(".HmiRequest") and ("AccessRW." in path or self.ro_child_writable)
        if accepted:
            self.values[path]=value
            if self.fail_after_write:
                self.fail_after_write=False
                raise OSError("response lost after applying the write")
        return SimpleNamespace(Status="Success" if accepted else "Privilege violation")


class AccessTests(unittest.TestCase):
    def test_both_parent_ro_outcomes_are_observations_and_all_values_restore(self):
        for behavior in (False,True):
            comm=Fixture(ro_child_writable=behavior)
            report=access.execute(comm)
            self.assertTrue(report["passed"],report)
            self.assertEqual(set(comm.values.values()),{0})
            self.assertLessEqual(len(comm.writes),8)

    def test_uncertain_success_is_restored_in_finally(self):
        comm=Fixture(fail_after_write=True)
        report=access.execute(comm)
        self.assertFalse(report["passed"])
        self.assertIn("response lost",report["error"])
        self.assertEqual(set(comm.values.values()),{0})
        self.assertTrue(all(row["restored"] for row in report["restoration"]))

    def test_wrong_image_prevents_every_write(self):
        comm=Fixture(valid=False)
        report=access.execute(comm)
        self.assertFalse(report["passed"])
        self.assertEqual(comm.writes,[])


if __name__=="__main__":
    unittest.main()

"""Collect successful gates without counting interrupted attempts."""
from pathlib import Path
import importlib.util,json,os,re,sys,xml.etree.ElementTree as ET
work=Path(__file__).resolve().parent;repo=Path("C:/Projects/Fraktal")
cases={
 "Manual alarm recovery":("13_recovery_probe.junit.xml","13_recovery_probe.jsonl"),
 "Closed history":("21_history_regression.junit.xml","21_history_regression.jsonl"),
 "Users and root policy":("22_access_persistence_regression.xml","22_access_persistence_regression.jsonl"),
 "Named config sets":("23_sets_regression.xml","23_sets_regression.jsonl"),
 "Station/model config":("38_config_regression.junit.xml","38_config_regression.jsonl"),
 "Access and sessions":("33_access_regression.junit.xml","33_access_regression.jsonl"),
 "State and alarm lifecycle":("35_state_alarm_regression.junit.xml","35_state_alarm_regression.jsonl"),
 "Operator decisions":("36_decision_regression.xml","36_decision_regression.jsonl")}
counts={}
for title,(xml,raw) in cases.items():
 suite=ET.parse(work/xml).getroot()
 assert int(suite.get("failures",0))==0 and int(suite.get("errors",0))==0
 assert not list(suite.iter("failure")) and not list(suite.iter("error"))
 rows=[json.loads(s) for s in (work/raw).read_text(encoding="utf-8").splitlines()]
 terminal=[r for r in rows if r.get("event") in ("complete","summary")]
 if title=="Operator decisions":
  assert rows[-1]["event"]=="final-simulator" and rows[-1]["status"]["state"]=="Run"
  observed=[r for r in rows if r.get("event")=="check"]
  assert len(observed)==int(suite.get("tests")) and all(r["passed"] for r in observed)
 else:
  end=terminal[-1]
  assert end.get("completed",True) is True and end.get("failures",end.get("failed",0))==0
 counts[title]=int(suite.get("tests"));assert counts[title]>0
compiles={}
for name in ("11_native_download.jsonl","04_press_compile.jsonl","14_press_final_compile.jsonl"):
 rows=[json.loads(s) for s in (work/name).read_text(encoding="utf-8").splitlines()]
 gates=[r for r in rows if r.get("event")=="compile"]
 assert gates and all(g["errors"]==0 and g["warnings"]==0 and g["state"]=="Success" for g in gates)
 compiles[name]=gates
parity=json.loads((work/"20_final_parity.json").read_bytes());assert parity["replayed_sources"]==110 and parity["wired"]
def log(name):
 data=(work/name).read_bytes();return data.decode("utf-16" if data.startswith(b"\xff\xfe") else "utf-8-sig")
assert re.search(r"Ran 158 tests.*?\bOK\b",log("16_tools_final.log"),re.S)
assert re.search(r"Ran 35 tests.*?\bOK\b",log("18_consistency_tests.log"),re.S)
assert "+574 ~8: All tests passed!" in log("08_hmi_tests.log")
spec=importlib.util.spec_from_file_location("guard",repo/"FraktalCore/PLC/Siemens/Tests/Unit/probe_web.py")
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
owner=guard.guard();assert owner["state"]=="Run"
keeper=json.loads((work/"39_keeper_status.json").read_text(encoding="utf-8-sig"));assert keeper["Id"]==12728
summary=dict(generator_version="0.13",recovery=counts["Manual alarm recovery"],native=counts,native_assertions=sum(counts.values()),tools=158,consistency=35,hmi=574,hmi_skips=8,native_compile=compiles,press_parity=parity,owner=owner,keeper_pid=keeper["Id"],raw_attempts_preserved=True)
assert not (work/"29_gate_summary.json").exists()
(work/"29_gate_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8",newline="\n")
print(json.dumps(summary,indent=2))

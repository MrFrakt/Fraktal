"""Validate the recorded S11 recovery run; GRAPH preservation stays unpassed."""
import argparse
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from plcsim_results import validate as baseline_validate


def events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def tags(path):
    result = {}
    for row in events(path):
        if row.get("event") == "tag":
            if row["name"] in result:
                raise ValueError("duplicate tag " + row["name"])
            result[row["name"]] = row["value"]
    return result


def require(snapshot, name, expected):
    if name not in snapshot:
        raise ValueError("missing tag " + name)
    actual = snapshot[name]
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError("%s: expected %r, read %r" % (name, expected, actual))


def recovery(snapshot, **values):
    for name, value in values.items():
        require(snapshot, "S11Recovery." + name, value)


def withdrawn(snapshot):
    recovery(snapshot, State=10, Arm=False, ErrGraph=False)
    for child in "AB":
        for leaf in ("Execute", "Busy", "Error"):
            require(snapshot, "S11Recovery.Root.Cyl" + child + "." + leaf, False)
        for leaf in ("Extend", "Retract"):
            require(snapshot, "S11Recovery.Hal.Cyl" + child + "." + leaf, False)


def idle(snapshot):
    withdrawn(snapshot)
    recovery(snapshot, StayedIdle=True, RestartDropped=True)
    if type(snapshot["S11Recovery.IdleScans"]) is not int or snapshot["S11Recovery.IdleScans"] <= 0:
        raise ValueError("no idle scan observed")


def busy(snapshot):
    recovery(snapshot, State=20, NativeActive=True, ErrGraph=False)
    require(snapshot, "S11Recovery.Seq.Record.StepNo", 100)
    require(snapshot, "S11Recovery.Root.CylA.Execute", True)
    require(snapshot, "S11Recovery.Root.CylA.Busy", True)
    require(snapshot, "S11Recovery.Root.CylA.Error", False)
    require(snapshot, "S11Recovery.Hal.CylA.Extend", True)


def successful_plan(path):
    rows = events(path)
    if not any(row.get("event") == "plan-complete" and row["tolerated-failures"] == 0 for row in rows):
        raise ValueError("plan incomplete: " + path.name)
    compiles = [row for row in rows if row.get("event") == "compile"]
    downloads = [row for row in rows if row.get("event") == "download"]
    if not compiles or len(downloads) != 1:
        raise ValueError("compile/download missing: " + path.name)
    for row in compiles + downloads:
        if row.get("state") != "Success" or row["errors"] != 0 or row["warnings"] != 0:
            raise ValueError("compile/download not clean: " + path.name)
    return rows


def verify(raw):
    suite = ET.Element("testsuite", name="Fraktal.TIA.S11.Recovery")
    outcomes = []

    def check(name, callback):
        case = ET.SubElement(suite, "testcase", name=name, classname="S11.Recovery")
        try:
            callback()
            outcomes.append({"name": name, "result": "pass"})
        except (ValueError, KeyError, AssertionError) as error:
            ET.SubElement(case, "failure", message=str(error))
            outcomes.append({"name": name, "result": "fail", "detail": str(error)})

    snapshots = {name: tags(raw / name) for name in (
        "08b_baseline_read.log", "10_active_before_code.log", "12_after_code.log",
        "14_after_chart.log", "16_after_reset.log", "18_before_warm.log",
        "21b_warm_completed.log", "23_active_after_warm.log", "25_complete.log",
        "29_after_permit_fix.log", "31_busy_with_permit.log", "33_completed_with_permit.log",
        "35_reset_completed_with_permit.log", "38_before_warm_fix.log", "41_after_warm_fix.log")}
    cold = snapshots["08b_baseline_read.log"]
    before = snapshots["10_active_before_code.log"]
    after = snapshots["12_after_code.log"]
    chart = snapshots["14_after_chart.log"]
    warm = snapshots["21b_warm_completed.log"]

    def baselines():
        for name, snapshot in snapshots.items():
            rows = baseline_validate((raw / name).read_text(encoding="utf-8-sig"), set(range(1, 29)))
            if len(rows) != 28 or not all(row[1] for row in rows):
                raise ValueError("baseline failed: " + name)
    check("all fifteen completed baseline harvests: 28/28", baselines)
    check("startup withdraws outputs and stays idle", lambda: (idle(cold), recovery(cold, SafeFirstScan=True, Marker=2101)))
    check("withheld feedback keeps command BUSY", lambda: busy(before))

    def code_delta():
        rows = successful_plan(raw / "11_code_delta.log")
        forbidden = {"StopModules", "StartModules", "TurnOffSequence", "DataBlockReinitialization"}
        if any(row.get("event") == "download-question" and row["type"] in forbidden for row in rows):
            raise ValueError("code delta requested stop/reinitialization")
        busy(after)
        recovery(after, Marker=2102)
        if after["S11Recovery.Calls"] <= before["S11Recovery.Calls"]:
            raise ValueError("scan counter did not advance")
        for name in ("StartupCalls", "ResetCount", "Seq.TraceCount", "Seq.Trace[0]", "Seq.Trace[1]"):
            require(after, "S11Recovery." + name, before["S11Recovery." + name])
    check("FC delta preserves observed active command and DB state", code_delta)

    def graph_delta():
        rows = successful_plan(raw / "13_chart_delta.log")
        types = {row["type"] for row in rows if row.get("event") == "download-question"}
        if not {"TurnOffSequence", "DataBlockReinitialization"} <= types:
            raise ValueError("expected GRAPH load boundary not recorded")
        busy(chart)
    check("GRAPH delta records required turn-off/reinitialization and BUSY endpoint", graph_delta)
    case = ET.SubElement(suite, "testcase", name="GRAPH delta preserves active native state without reinitialization", classname="S11.Recovery")
    detail = "NOT PASSED: TIA requested TurnOffSequence and DataBlockReinitialization; endpoint reads cannot prove uninterrupted execution."
    ET.SubElement(case, "skipped", message=detail)
    outcomes.append({"name": case.attrib["name"], "result": "not passed", "detail": detail})

    check("reset while BUSY withdraws and requires new Arm", lambda: (
        idle(snapshots["16_after_reset.log"]), recovery(snapshots["16_after_reset.log"], ResetBeforeExecute=True, ResetCount=1)))
    check("new Arm after reset issues a fresh BUSY command", lambda: busy(snapshots["18_before_warm.log"]))

    def warm_restart():
        for name, state in (("19_halt.log", "Stop"), ("20_run.log", "Run")):
            if not any(row.get("event") == "instance" and row["state"] == state for row in events(raw / name)):
                raise ValueError("native state change missing")
        idle(warm)
        recovery(warm, SafeFirstScan=True, Marker=2102, ResetCount=0)
        if warm["S11Recovery.Calls"] >= snapshots["18_before_warm.log"]["S11Recovery.Calls"]:
            raise ValueError("NON_RETAIN counter was not reinitialized")
    check("STOP/RUN while BUSY reinitializes NON_RETAIN and remains idle", warm_restart)
    check("new Arm after warm restart issues a fresh BUSY command", lambda: busy(snapshots["23_active_after_warm.log"]))

    def complete(name):
        snapshot = snapshots[name]
        require(snapshot, "S11Recovery.Seq.Record.StepNo", 999)
        require(snapshot, "S11Recovery.Seq.TraceCount", 3)
        for index, step in enumerate((0, 100, 999)):
            require(snapshot, "S11Recovery.Seq.Trace[%d]" % index, step)
        for leaf in ("Execute", "Busy", "Done", "Error"):
            require(snapshot, "S11Recovery.Root.CylA." + leaf, False)
    check("feedback completes the chart and releases the command handshake", lambda: complete("25_complete.log"))
    check("output permit fix compiles/downloads cleanly and withdraws idle coils", lambda: (
        successful_plan(raw / "28_output_permit_delta.log"), withdrawn(snapshots["29_after_permit_fix.log"]),
        recovery(snapshots["29_after_permit_fix.log"], StayedIdle=False, RestartDropped=False)))
    check("output permit retains commanded motion and completion", lambda: (
        busy(snapshots["31_busy_with_permit.log"]), complete("33_completed_with_permit.log")))
    check("reset after completion withdraws READY outputs", lambda: idle(snapshots["35_reset_completed_with_permit.log"]))
    check("fixed image restarts from BUSY to safe idle", lambda: (
        busy(snapshots["38_before_warm_fix.log"]), idle(snapshots["41_after_warm_fix.log"]),
        recovery(snapshots["41_after_warm_fix.log"], SafeFirstScan=True, Marker=2102)))
    def readback():
        result = json.loads((raw / "42_readback_comparison.json").read_text())
        if not all(value is True for group in result.values() for value in group.values()):
            raise ValueError("canonical GRAPH/interface comparison differs")
    check("generated GRAPH read-back and DB interfaces agree", readback)
    def guards():
        rows = json.loads((raw / "43_guard_results.json").read_text())
        if {row["case"] for row in rows} != {"wrong_target", "wrong_type"} or not all(row["refused_before_write"] is True for row in rows):
            raise ValueError("write guard refusal not proven")
    check("wrong target and type are refused before any write", guards)
    counts = {kind: sum(item["result"] == kind for item in outcomes) for kind in ("pass", "fail", "not passed")}
    suite.attrib.update(tests=str(len(outcomes)), failures=str(counts["fail"]), skipped=str(counts["not passed"]))
    ET.indent(suite)
    return outcomes, ET.tostring(suite, encoding="utf-8", xml_declaration=True) + b"\n", counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=pathlib.Path)
    args = parser.parse_args()
    results, xml, counts = verify(args.raw)
    with (args.raw / "recovery_junit.xml").open("xb") as stream:
        stream.write(xml)
    with (args.raw / "recovery_results.json").open("xb") as stream:
        stream.write((json.dumps({"counts": counts, "results": results}, indent=2) + "\n").encode("ascii"))
    print(json.dumps(counts))
    raise SystemExit(1 if counts["fail"] else 0)

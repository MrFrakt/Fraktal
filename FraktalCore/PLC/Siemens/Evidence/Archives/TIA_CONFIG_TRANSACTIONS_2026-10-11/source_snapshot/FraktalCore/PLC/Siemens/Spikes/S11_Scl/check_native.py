"""Validate the S11 native warm-restart and code-delta evidence, not just totals."""
import hashlib
import json
import pathlib
import sys
import xml.etree.ElementTree as ET


def snapshot(path):
    events = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    return next(event for event in events if event["event"] == "snapshot")


def stamp(values):
    return tuple(values['"S11Scl".StartupAt.' + field] for field in
                 ("YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND", "NANOSECOND"))


def db_interface(path):
    root = ET.fromstring(path.read_bytes())
    interface = root.find("SW.Blocks.GlobalDB/AttributeList/Interface")
    if interface is None:
        raise ValueError("S11 data-block interface absent")
    return ET.canonicalize(ET.tostring(interface, encoding="unicode"), strip_text=True)


def verify(raw, exports1101, exports1102):
    before_warm = snapshot(raw / "13_after_first_run.jsonl")
    after_warm = snapshot(raw / "16_after_warm_run.jsonl")
    if stamp(before_warm["values"]) == stamp(after_warm["values"]):
        raise ValueError("warm restart did not change the OB100 timestamp")
    before = snapshot(raw / "31_before_delta1102.jsonl")
    after = snapshot(raw / "34_after_delta1102.jsonl")
    for item in (before, after):
        values = item["values"]
        if item["mode"] != "run" or values['"S11Scl".State'] != 99:
            raise ValueError("code delta did not remain in completed RUN state")
        for flag in ("StartupSeen", "StartupSafe", "InitialCallSeen", "AfterError"):
            if values['"S11Scl".' + flag] is not True:
                raise ValueError("startup/error observation lost: " + flag)
        if values['"S11Scl".Samples[0]'] != 21265 or values['"S11Scl".LocalCode'] != 9506:
            raise ValueError("sentinel or error observation lost")
    a, b = before["values"], after["values"]
    if a['"S11Scl".ValueRead'] != 1101 or b['"S11Scl".ValueRead'] != 1102:
        raise ValueError("executing code revision did not change")
    if stamp(a) != stamp(b):
        raise ValueError("OB100 ran during the code delta")
    for field in ('"S11Scl".Samples[1]', '"FRK_Clock".Scans', '"FRK_Clock".NowMs'):
        if b[field] <= a[field]:
            raise ValueError("counter reset or stalled: " + field)
    for field in ('"SpikeUnit".HmiRequest.Sequence', '"SpikeUnit".HmiResponse.AckSequence'):
        if a[field] != b[field]:
            raise ValueError("mailbox sequence changed: " + field)
    interfaces = [db_interface(directory / "S11Scl.xml") for directory in (exports1101, exports1102)]
    if interfaces[0] != interfaces[1]:
        raise ValueError("data-block interface changed")
    for name in ("17_warm_results.xml", "27_delta1101_results.xml", "35_delta1102_results.xml"):
        suite = ET.parse(raw / name).getroot()
        if suite.get("tests") != "19" or suite.get("failures") != "0":
            raise ValueError("unexpected native result table: " + name)
        ids = {int(case.get("name").split()[0]) for case in suite.findall("testcase")}
        if ids != set(range(1, 18)) | {29, 30}:
            raise ValueError("wrong native case set: " + name)
    print(json.dumps({"warm_restart": "PASS", "code_delta": "PASS", "cases": "1-17,29,30",
                      "db_interface_sha256": hashlib.sha256(interfaces[0].encode("utf-8")).hexdigest(),
                      "counter_before": a['"S11Scl".Samples[1]'], "counter_after": b['"S11Scl".Samples[1]']}, indent=2))


if __name__ == "__main__":
    verify(*(pathlib.Path(arg) for arg in sys.argv[1:]))

"""Validate one PLCSIM read log against an exact case set, then emit JUnit.

The Runtime API tag harvest is read-only. A completed table, magic, counters,
all row leaves and the requested case IDs must agree before any green result.
    python plcsim_results.py read.log --cases 1-28 --junit run.xml
"""
import argparse
import json
import pathlib
import xml.etree.ElementTree as ET

from s7_probe import CASES, RESULT_MAGIC, RESULT_ROWS


def case_set(text):
    cases = set()
    for item in text.split(","):
        ends = [int(x) for x in item.split("-")]
        if len(ends) == 1:
            values = [ends[0]]
        elif len(ends) == 2 and 1 <= ends[0] <= ends[1] <= RESULT_ROWS:
            values = range(ends[0], ends[1] + 1)
        else:
            raise ValueError("invalid case range " + item)
        for value in values:
            if not 1 <= value <= RESULT_ROWS or value in cases:
                raise ValueError("invalid or duplicate case " + str(value))
            cases.add(value)
    return cases


def validate(log, expected_cases):
    tags = {}
    for line in log.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event") == "tag" and event["name"].startswith("SpkResults.T."):
            name = event["name"]
            if name in tags:
                raise ValueError("multiple reads of " + name)
            tags[name] = event["value"]
    def read(leaf):
        key = "SpkResults.T." + leaf
        if key not in tags:
            raise ValueError("missing result leaf " + key)
        return tags[key]
    if read("Magic") != RESULT_MAGIC or read("Done") is not True:
        raise ValueError("result table is not initialized and complete")
    count = read("RowCount")
    if type(count) is not int or not 1 <= count <= RESULT_ROWS:
        raise ValueError("invalid row count")
    rows = []
    for index in range(1, count + 1):
        row = [read("Rows[%d].%s" % (index, field)) for field in ("CaseId", "Pass", "Expected", "Actual")]
        if type(row[0]) is not int or type(row[1]) is not bool or any(type(x) is not int for x in row[2:]):
            raise ValueError("invalid row types")
        rows.append(tuple(row))
    ids = [r[0] for r in rows]
    if len(set(ids)) != len(ids) or set(ids) != expected_cases:
        raise ValueError("case IDs differ: expected %s, read %s" % (sorted(expected_cases), ids))
    passed = sum(row[1] for row in rows)
    if read("Passed") != passed or read("Failed") != count - passed:
        raise ValueError("result counters disagree with rows")
    return rows


def junit(rows):
    suite = ET.Element("testsuite", name="Fraktal.TIA.S11", tests=str(len(rows)),
                       failures=str(sum(not row[1] for row in rows)))
    for case_id, passed, expected, actual in rows:
        case = ET.SubElement(suite, "testcase", classname="S11", name="%02d %s" % (case_id, CASES[case_id]))
        if not passed:
            ET.SubElement(case, "failure", message="expected %d actual %d" % (expected, actual))
    ET.indent(suite)
    return ET.tostring(suite, encoding="utf-8", xml_declaration=True) + b"\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--junit", type=pathlib.Path, required=True)
    args = parser.parse_args()
    rows = validate(args.log.read_text(encoding="utf-8-sig"), case_set(args.cases))
    args.junit.write_bytes(junit(rows))
    passed = sum(row[1] for row in rows)
    print("S11 %d/%d; %s" % (passed, len(rows), args.junit))
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print("invalid harvest:", error)
        raise SystemExit(1)

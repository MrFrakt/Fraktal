"""Verify independently harvested S12 scalar boundaries and timestamp encodings."""
import argparse
import datetime
import json
import pathlib

from probe import SCALARS

STAMP = datetime.datetime(2024, 2, 29, 23, 59, 58, tzinfo=datetime.timezone.utc)
DTL = {"YEAR": 2024, "MONTH": 2, "DAY": 29, "WEEKDAY": 5,
       "HOUR": 23, "MINUTE": 59, "SECOND": 58, "NANOSECOND": 123456789}


def packed_dt(value):
    """Runtime API exposes DATE_AND_TIME's eight BCD bytes as a UInt64."""
    raw = value.to_bytes(8, "little")

    def bcd(byte):
        high, low = byte >> 4, byte & 15
        if high > 9 or low > 9:
            raise ValueError("invalid BCD date byte")
        return high * 10 + low

    year = bcd(raw[0])
    year += 2000 if year < 90 else 1900
    milliseconds = bcd(raw[6]) * 10 + (raw[7] >> 4)
    if raw[7] >> 4 > 9 or not 1 <= (raw[7] & 15) <= 7:
        raise ValueError("invalid DATE_AND_TIME millisecond/weekday")
    result = datetime.datetime(year, bcd(raw[1]), bcd(raw[2]), bcd(raw[3]),
                               bcd(raw[4]), bcd(raw[5]), milliseconds * 1000,
                               tzinfo=datetime.timezone.utc)
    if (raw[7] & 15) != (result.weekday() + 1) % 7 + 1:
        raise ValueError("DATE_AND_TIME weekday disagrees with date")
    return result


def verify(raw, expected_enum=None):
    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8-sig").splitlines()]
    values = {}
    for row in rows:
        if row["event"] == "tag":
            if row["name"] in values:
                raise ValueError("duplicate scalar: " + row["name"])
            values[row["name"]] = row["value"]
    expected = {"S12Probe." + name: value for name, value in SCALARS.items()}
    expected.update({"S12Probe.LowerArray[%d]" % n: n * 100 + 7 for n in range(-2, 3)})
    expected.update({"S12Probe.StampDtl." + name: value for name, value in DTL.items()})
    expected["S12Probe.StampLdt"] = int(STAMP.timestamp()) * 1000000000 + DTL["NANOSECOND"]
    expected["S12Probe.ClockRc"] = 0
    if expected_enum is not None:
        expected["S12Probe.EnumWitness"] = expected_enum
    wrong = [name for name, wanted in expected.items()
             if name not in values or type(values[name]) is not type(wanted) or values[name] != wanted]
    if packed_dt(values["S12Probe.StampDt"]) != STAMP:
        wrong.append("S12Probe.StampDt")
    failed_leaves = [row["name"] for row in rows if row["event"] == "tag-failed"
                     and row["name"] != "S12Probe.LowerArray"]
    return {"checked": len(expected) + 1, "wrong": wrong, "failed_leaves": failed_leaves,
            "passed": not wrong and not failed_leaves,
            "scope": "PLCSIM SDK; Web API and HMI gate remains separate"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--enum-count", type=int)
    args = parser.parse_args()
    result = verify(args.raw, args.enum_count)
    with args.out.open("x", encoding="ascii", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result))
    raise SystemExit(0 if result["passed"] else 1)

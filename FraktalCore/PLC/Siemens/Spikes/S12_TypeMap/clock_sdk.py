"""Observe an uninterrupted S12 clock interval through the independent simulator SDK."""
import argparse
import json
import pathlib
import subprocess
import time

from probe import emit

HERE = pathlib.Path(__file__).resolve().parent
FIELDS = ("Ready", "Scans", "MonoSec", "BadDelta", "MaxDeltaSec")


def sample():
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(HERE / "simulator.ps1"), "-Action", "read", "-DataBlocks", "S12Probe",
               "-Match", r"^S12Probe\.(Ready|Scans|MonoSec|BadDelta|MaxDeltaSec)$"]
    before = time.monotonic()
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    after = time.monotonic()
    if result.returncode:
        raise ValueError(result.stdout.decode("utf-8-sig", errors="replace"))
    values = {}
    for line in result.stdout.decode("utf-8-sig").splitlines():
        row = json.loads(line)
        if row["event"] != "tag":
            raise ValueError("clock leaf failed: " + row.get("name", "unknown"))
        key = row["name"].split(".")[-1]
        if key in values:
            raise ValueError("duplicate clock leaf: " + key)
        values[key] = row["value"]
    if set(values) != set(FIELDS):
        raise ValueError("incomplete clock sample")
    return {"before": before, "after": after, "values": values}


def observe(out, minutes=60, period=30):
    with out.open("x", encoding="ascii", newline="\n") as stream:
        emit(stream, "criterion", transport="independent PLCSIM Runtime API; no Web API claim",
             minimum_seconds=minutes * 60, period_seconds=period,
             tolerance="max(1 second, 0.1 percent of host interval)",
             uncertainty="first and last SDK read spans bound elapsed host time",
             continuity="Ready, zero BadDelta, increasing scan/clock, sample gap below 60 seconds")
        first = previous = None
        try:
            while True:
                current = sample()
                values = current["values"]
                if values["Ready"] is not True or values["BadDelta"] != 0:
                    raise ValueError("PLC not ready or RUNTIME rejected a delta")
                if previous and (values["Scans"] <= previous["values"]["Scans"] or
                                 values["MonoSec"] <= previous["values"]["MonoSec"] or
                                 current["before"] - previous["after"] >= 60):
                    raise ValueError("clock reset, stopped scanning or observer interrupted")
                if first is None:
                    first = current
                host_low = current["before"] - first["after"]
                host_high = current["after"] - first["before"]
                plc_elapsed = values["MonoSec"] - first["values"]["MonoSec"]
                emit(stream, "clock", **current, host_elapsed_low=host_low,
                     host_elapsed_high=host_high, plc_elapsed=plc_elapsed)
                if host_low >= minutes * 60:
                    tolerance = max(1.0, (host_low + host_high) / 2 * 0.001)
                    drift_low, drift_high = plc_elapsed - host_high, plc_elapsed - host_low
                    # Both uncertainty endpoints must meet the prototype criterion.
                    passed = max(abs(drift_low), abs(drift_high)) <= tolerance
                    summary = {"host_elapsed_low": host_low, "host_elapsed_high": host_high,
                               "plc_elapsed": plc_elapsed, "drift_low": drift_low,
                               "drift_high": drift_high, "tolerance_seconds": tolerance,
                               "passed": passed}
                    emit(stream, "clock-summary", **summary)
                    print(json.dumps(summary), flush=True)
                    return passed
                previous = current
                time.sleep(min(period, max(0.01, first["after"] + minutes * 60 - current["after"])))
        except Exception as error:
            emit(stream, "clock-failed", message=str(error))
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--minutes", type=float, default=60)
    parser.add_argument("--period", type=float, default=30)
    args = parser.parse_args()
    if args.minutes <= 0 or not 0 < args.period < 40:
        parser.error("positive interval and period below 40 seconds required")
    raise SystemExit(0 if observe(args.out, args.minutes, args.period) else 1)

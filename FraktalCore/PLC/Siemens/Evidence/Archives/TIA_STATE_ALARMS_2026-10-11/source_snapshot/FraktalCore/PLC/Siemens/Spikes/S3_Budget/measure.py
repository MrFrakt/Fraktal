"""Read-only S3 bench memory and scan measurement; never prints credentials.

Requires the existing TLS pin and WEB/DIAG password environment variables.
Legacy memory sessions and API sessions are logged out in finally blocks.
"""
import argparse
import html
import json
import os
import pathlib
import re
import statistics
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "S11_Scl"))
from web_mode import NativePage
from tia_webapi import WebApi

HOST = "192.168.0.10"
MEMORY_PAGE = "/Portal/Portal.mwsl?PriNav=Online&SecNav=Memory"


def area(text, label):
    pattern = re.escape(label) + r" ([\d.]+)% in use Free: ([\d.]+) (KB|MB) / Total: ([\d.]+) (KB|MB)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError("authenticated memory area missing: " + label)
    free = float(match[2]) * (1024 if match[3] == "MB" else 1)
    total = float(match[4]) * (1024 if match[5] == "MB" else 1)
    return {"used_kb": round(total - free, 2), "free_kb": free,
            "total_kb": total, "percent": float(match[1])}


def measure(label, window, repeats, native_page=None):
    pin_file = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal/TiaStations/192.168.0.10.webapi.pin"
    page = native_page or NativePage(pin_file.read_text(encoding="ascii").strip())
    try:
        if native_page is None:
            page.login()
        try:
            code, body = page.request("GET", MEMORY_PAGE)
        except (ConnectionError, OSError):
            # Only this GET is retried; keep the cookie and pin the new socket.
            page.conn.close()
            code, body = page.request("GET", MEMORY_PAGE)
        if code != 200:
            raise ValueError("memory page refused")
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
        memory = {key: area(text, name) for key, name in
                  (("load", "Load memory"), ("work", "Work Memory"), ("retentive", "Retentive memory"))}
    finally:
        if native_page is None:
            page.close()
    print(json.dumps({"event": "memory", "label": label, "memory": memory}), flush=True)

    api = WebApi(HOST, pin_file, False, timeout=20)
    try:
        api.login("fraktal")
        calls = [("PlcProgram.Read", {"var": '"FRK_Clock".' + field}) for field in ("CycleMs", "Scans")]
        windows = []
        for repeat in range(repeats):
            first = last = None
            samples = []
            deadline = time.monotonic() + window
            while time.monotonic() < deadline:
                replies = api.bulk(calls)
                if any(error for _, error in replies):
                    raise ValueError("clock read refused")
                cycle, scans = (reply[0] for reply in replies)
                now = (time.monotonic(), int(scans))
                first = first or now
                last = now
                samples.append(float(cycle))
            if last[1] <= first[1] or len(samples) < 2:
                raise ValueError("clock reset/stalled during sample")
            mean = 1000 * (last[0] - first[0]) / (last[1] - first[1])
            result = {"mean_ms": round(mean, 6), "samples": len(samples),
                      "cycle_median_ms": statistics.median(samples), "cycle_max_ms": max(samples),
                      "scans_first": first[1], "scans_last": last[1]}
            windows.append(result)
            print(json.dumps({"event": "cycle-window", "label": label, "repeat": repeat, **result}), flush=True)
        print(json.dumps({"event": "measurement", "label": label, "memory": memory,
                          "mean_ms": statistics.median(item["mean_ms"] for item in windows), "windows": windows}), flush=True)
    finally:
        if api.token:
            try:
                api.call("Api.Logout")
            except (OSError, RuntimeError):
                pass
        api.conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("label")
    parser.add_argument("--window", type=float, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.window <= 0 or args.repeats < 1:
        parser.error("positive window/repeats required")
    measure(args.label, args.window, args.repeats)

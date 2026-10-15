"""Run one guarded S11 simulation action and append its raw log (never overwrite)."""
import argparse
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[5]
TOOLS = HERE.parents[2] / "tools"
SIM = TOOLS / "Invoke-PlcSimInstance.ps1"
DRIVER = TOOLS / "TiaCli/bin/candidate_s11_enumeration/Fraktal.Tia.Cli.exe"
LOCAL = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal"
MATCH = (r"^(SpkResults\.T\.|S11Recovery\.(InitialCall|Arm|ReleaseFeedback|ResetRequest|State|Marker|Calls|"
         r"StartupCalls|StartupAt\.|SafeFirstScan|StayedIdle|IdleScans|RestartDropped|ResetCount|ResetBeforeExecute|"
         r"ErrGraph|NativeStep|NativeActive|AutoMode|Seq\.(Trace\[|TraceCount|Record\.StepNo)|"
         r"Root\.Cyl[AB]\.(Execute|Busy|Done|Error|Aborted|ErrorID)|Hal\.Cyl[AB]\.(Extend|Retract))|"
         r"FRK_Registry\.(Count|Overflow|Rows\[[456]\]\.Parent)|S11Errors\.State|S11Semantics\.StartupCalls)")


def run(log, command):
    with log.open("xb") as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    print(json.dumps({"log": str(log), "exit_code": result.returncode}), flush=True)
    if result.returncode:
        print(log.read_text(encoding="utf-8", errors="replace")[-4000:])
        raise RuntimeError("simulation action failed; inspect its outcome before another mutation")


def ps(*args):
    return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SIM), *args]


def confirm(log):
    run(log, ps("-Action", "status"))
    instances = [json.loads(line) for line in log.read_text().splitlines() if line.startswith("{")]
    instance = next(row for row in instances if row["event"] == "instance" and row["name"] == "FrkS11")
    if instance["comm"] != "Softbus" or instance["cpu"] != "CPU1516" or "192.168.252.1" not in instance["addresses"]:
        raise ValueError("target is not the declared Softbus 1516")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("read", "write", "code", "chart", "output", "halt", "run"))
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument("--tag")
    parser.add_argument("--value", choices=("true", "false"))
    parser.add_argument("--generated", type=pathlib.Path, default=LOCAL / "TiaSpikes/S11_Recovery_20261010")
    args = parser.parse_args()
    if args.action == "read":
        run(args.log, ps("-Action", "read", "-DataBlocks", "SpkResults,S11Recovery,FRK_Registry,S11Errors,S11Semantics", "-Match", MATCH))
        return
    confirm(args.log.with_name(args.log.stem + "_status.log"))
    if args.action == "write":
        if not args.tag or not args.value:
            parser.error("write requires --tag and --value")
        run(args.log, ps("-Action", "write", "-ConfirmTarget", "192.168.252.1", "-Tag", args.tag,
                         "-ValueType", "Bool", "-Value", args.value))
    elif args.action in ("halt", "run"):
        run(args.log, ps("-Action", args.action, "-ConfirmTarget", "192.168.252.1"))
    else:
        export = LOCAL / ("TiaStations/FrkS11_Recovery_" + args.log.stem + "_export")
        run(args.log, [str(DRIVER), "plan", str(HERE / (args.action + "_delta.plan")),
                      "--set", "work=" + str(LOCAL / "TiaStations"),
                      "--set", "gen=" + str(args.generated), "--set", "export=" + str(export)])


if __name__ == "__main__":
    main()

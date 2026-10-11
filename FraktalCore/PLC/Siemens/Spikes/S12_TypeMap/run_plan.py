"""Run an approved driver plan once and preserve its raw output."""
import argparse
import json
import os
import pathlib
import re
import shlex
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / "tools"
DRIVER = TOOLS / "TiaCli/bin/candidate_s11_enumeration/Fraktal.Tia.Cli.exe"


def require_clean_compile(log):
    rows = [json.loads(line) for line in log.read_text(encoding='utf-8-sig').splitlines() if line.startswith('{')]
    compiles = [row for row in rows if row.get('event') == 'compile']
    if not compiles or any(row.get('errors') != 0 or row.get('warnings') != 0 for row in compiles):
        raise ValueError('compile gate requires every compile event to have zero errors and warnings')
    return len(compiles)


def guard_downloads(plan, substitutions, stream):
    expanded = plan.read_text(encoding="ascii")
    for item in substitutions:
        key, value = item.split("=", 1)
        expanded = expanded.replace("${" + key + "}", value)
    if "${" in expanded:
        raise ValueError("unresolved plan variable before simulator/driver execution")
    downloads = [shlex.split(line) for line in expanded.splitlines()
                 if re.match(r"^\s*download\b", line, re.I)]
    if not downloads:
        return
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(HERE / "simulator.ps1"), "-Action", "status"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stream.write(result.stdout)
    stream.flush()
    if result.returncode:
        raise ValueError("S12 simulator preflight failed")
    status = json.loads(result.stdout.decode("utf-8-sig").strip())
    if (status["name"] != "FrkS12" or status["cpu"] != "CPU1516" or status["comm"] != "TCPIP"
            or "169.254.212.49" not in status["addresses"]
            or any(status[key] != 0 for key in ("ie1", "ie2", "ie3"))):
        raise ValueError("S12 download target or physical adapter mappings differ")
    for command in downloads:
        def option(name):
            try:
                return command[command.index(name) + 1]
            except (ValueError, IndexError):
                return None
        if (option("--plc") != "PLC_1" or option("--confirm-target") != "169.254.212.49"
                or option("--pc-interface") != "Siemens PLCSIM Virtual Ethernet Adapter"
                or option("--pc-number") != "1" or option("--target") != "1 X1"):
            raise ValueError("download must explicitly select the isolated S12 virtual target")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=pathlib.Path)
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--download", action="store_true", help="insert the exact isolated S12 full-download command")
    parser.add_argument("--trust-plc", choices=("PLC_1",), help="explicit logged trust for this newly registered virtual target")
    parser.add_argument('--require-clean-compile', action='store_true', help='fail unless every compiler result explicitly has zero errors and warnings')
    args = parser.parse_args()
    if args.download:
        args.set.append('download=download --plc PLC_1 --pc-interface "Siemens PLCSIM Virtual Ethernet Adapter" --pc-number 1 --target "1 X1" --confirm-target 169.254.212.49 --user-management keep')
    command = [str(DRIVER), "plan", str(args.plan)]
    for value in args.set:
        command.extend(["--set", value])
    if args.trust_plc:
        command.extend(["--trust-plc", args.trust_plc])
    with args.log.open("xb") as stream:
        guard_downloads(args.plan, args.set, stream)
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    print("%s: exit %d" % (args.log, result.returncode), flush=True)
    if result.returncode == 0 and args.require_clean_compile:
        print(json.dumps({'clean_compile_results': require_clean_compile(args.log)}), flush=True)
    raise SystemExit(result.returncode)

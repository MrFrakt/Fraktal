"""Independent Runtime API witness harvest; never substitutes for Web API proof."""
import argparse
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent


def harvest(manifest, out):
    expected = json.loads(manifest.read_text())["witnesses"]
    blocks = sorted({name.split(".")[0] for name in expected})
    rows = []
    with out.open("x", encoding="ascii", newline="\n") as stream:
        for offset in range(0, len(blocks), 6):
            group = blocks[offset:offset+6]
            names = [name for name in expected if name.split(".")[0] in group]
            match = "^(?:" + "|".join(re.escape(name) for name in names) + ")$"
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                       str(HERE / "simulator.ps1"), "-Action", "read", "-DataBlocks", ",".join(group), "-Match", match]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = result.stdout.decode("utf-8-sig", errors="replace")
            if result.returncode:
                raise ValueError(output)
            for line in output.splitlines():
                row = json.loads(line)
                stream.write(json.dumps(row) + "\n")
                rows.append(row)
            stream.flush()
            print("SDK %d/%d DBs" % (min(offset+6, len(blocks)), len(blocks)), flush=True)
        values = {}
        for row in rows:
            if row["event"] == "tag":
                if row["name"] in values:
                    raise ValueError("duplicate witness " + row["name"])
                values[row["name"]] = row["value"]
        missing = set(expected) - set(values)
        wrong = [name for name in expected if name in values and (type(values[name]) is not type(expected[name]) or values[name] != expected[name])]
        summary = {"event": "summary", "expected": len(expected), "read": len(values), "missing": sorted(missing), "wrong": wrong}
        stream.write(json.dumps(summary) + "\n")
        print(json.dumps(summary))
        return not missing and not wrong


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    args = parser.parse_args()
    raise SystemExit(0 if harvest(args.manifest, args.out) else 1)

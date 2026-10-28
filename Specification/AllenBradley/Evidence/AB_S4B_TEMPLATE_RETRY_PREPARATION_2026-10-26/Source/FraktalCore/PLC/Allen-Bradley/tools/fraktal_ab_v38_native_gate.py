#!/usr/bin/env python3
"""Compile/read back selected generated v38 probes; no controller operations.

Only the repository's offline SDK probe is invoked, with import/export and
Build arguments. Outputs are new files in a new directory. A negative control
must reach the compiler and produce a compiler diagnostic, not a license or
service failure. Results retain both successful and rejected candidates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from fraktal_ab_phase0_fixture import sha256
from fraktal_ab_phase0_gate import default_probe
from fraktal_ab_sdk_log_gate import audit_log
from fraktal_ab_v38_native_probe import SCHEMA, PROFILE


TARGETS = ("EchoController", "PhysicalController")


def project_model(path: Path) -> dict[str, object]:
    """Read back the actual type widths, executable ST and task binding."""
    root = ET.parse(path).getroot().find("Controller")
    return {
        "Controller": root.get("ProcessorType"), "MajorRevision": root.get("MajorRev"),
        "Members": [(m.get("Name"), m.get("DataType"), m.get("Dimension"),
                     m.get("ExternalAccess"))
                    for m in root.findall("DataTypes/DataType/Members/Member")],
        "Tags": sorted((t.get("Name"), t.get("DataType"), t.get("ExternalAccess"))
                       for t in root.findall("Tags/Tag")),
        "Tasks": [(t.get("Name"), t.get("Type"), t.get("Rate"),
                   t.get("DisableUpdateOutputs"),
                   [p.get("Name") for p in t.findall("ScheduledPrograms/ScheduledProgram")])
                  for t in root.findall("Tasks/Task")],
        "Logic": re.sub(r"\s+", "", "\n".join(
            line.text or "" for line in root.findall(
                "Programs/Program/Routines/Routine/STContent/Line"))).casefold(),
    }


def build_result(returncode: int, output: str) -> dict[str, object]:
    audit = audit_log(output, ("Build",))
    accepted = returncode == 0 and audit["Clean"]
    # A failed process launch, missing activation or connection to the SDK does
    # not prove an intentionally invalid instruction was checked.
    rejected = (not accepted and "] Build started" in output
                and "] Build succeeded" not in output
                and re.search(r"Rx(?:STX|CMP)_[A-Z_]+", output) is not None)
    return {"Accepted": accepted, "CompilerRejected": rejected,
            "ReturnCode": returncode, "SdkAudit": audit}


def readback_evidence(output: str) -> dict:
    for match in re.finditer(r'(?m)^\{\s*"Schema"\s*:\s*"fraktal.ab.offline-probe-build-readback"', output):
        report, _ = json.JSONDecoder().raw_decode(output[match.start():])
        return report
    return {}


def compile_cases(generation: dict, directory: Path, case_names: tuple[str, ...],
                  targets: tuple[str, ...] = TARGETS, sdk: Path | None = None,
                  *, expected_schema=SCHEMA, expected_profile=PROFILE.key) -> dict:
    if (generation.get("Schema") != expected_schema
            or generation.get("Profile") != expected_profile):
        raise ValueError("not the generated v38 native probe profile")
    cases = {case["Case"]: case for case in generation["Cases"]}
    if not case_names or len(set(case_names)) != len(case_names) or set(case_names) - cases.keys():
        raise ValueError("select distinct generated case names")
    if not targets or len(set(targets)) != len(targets) or set(targets) - set(TARGETS):
        raise ValueError("select distinct offline build targets")
    sdk = (sdk or default_probe()).resolve()
    if not sdk.is_file() or sdk.name != "Fraktal.Ab.OfflineProbe.exe":
        raise ValueError("built repository offline probe is required")
    # Validate every input before creating outputs or starting the SDK.
    for name in case_names:
        case = cases[name]
        if case.get("ExpectedBuild") not in ("pass", "fail", "observe"):
            raise ValueError(f"invalid compiler expectation: {name}")
        source = Path(case["Output"])
        if source.suffix.lower() != ".l5x" or sha256(source) != case["OutputSha256"]:
            raise ValueError(f"generated source changed: {name}")
    directory.mkdir(parents=True, exist_ok=False)

    def run(arguments: list[str], label: str) -> tuple[int, str]:
        result = subprocess.run([str(sdk), *arguments], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=300)
        output = (result.stdout or "") + (result.stderr or "")
        (directory / f"{label}.log").write_text(output, encoding="utf-8")
        return result.returncode, output

    rows = []
    for name in case_names:
        print(f"stage=native-compile case={name}", flush=True)
        case = cases[name]
        source = Path(case["Output"]).resolve()
        row = {"Case": name, "ExpectedBuild": case["ExpectedBuild"],
               "Imported": True, "Builds": {}, "ReadbackEqual": True,
               "ReadbackSha256": {}, "ImportSummaries": {}}
        for target in targets:
            export = directory / f"{name}_{target}_readback.L5X"
            code, output = run(["--build-readback", str(source), str(export), target],
                               f"{name}_{target}")
            audit = audit_log(output, ("Open project", "Save As"), require_clean_import=True)
            # A deliberate Build rejection emits an SDK error too. Assess the
            # import summary independently, then require the compiler witness.
            imported = (not audit["MissingOperations"] and bool(audit["ImportSummaries"])
                        and all(not s["Warnings"] and not s["Errors"]
                                for s in audit["ImportSummaries"]))
            row["Imported"] = row["Imported"] and imported
            row["ImportSummaries"][target] = audit["ImportSummaries"]
            result = build_result(code, output)
            row["Builds"][target] = result
            evidence = readback_evidence(output)
            from fraktal_ab_readback import compare as compare_readback
            complete_readback = compare_readback(source, export) if export.is_file() else None
            result['Readback'] = complete_readback
            intact = (evidence.get("InputUnchanged") is True
                      and evidence.get("InputSha256") == case["OutputSha256"]
                      and evidence.get("BuildTarget") == target
                      and evidence.get("BuildAccepted") is result["Accepted"]
                      and export.is_file()
                      and evidence.get("ExportSha256") == sha256(export)
                      and project_model(source) == project_model(export)
                      and complete_readback is not None and complete_readback['Equivalent'])
            row["ReadbackEqual"] = row["ReadbackEqual"] and intact
            row["ReadbackSha256"][target] = sha256(export) if export.exists() else None
        row["SourceSha256"] = sha256(source)
        builds = list(row["Builds"].values())
        row["ConformsToExpectation"] = bool(row["Imported"] and row["ReadbackEqual"] and builds
            and sha256(source) == case["OutputSha256"] and all(
                (b["Accepted"] if case["ExpectedBuild"] == "pass" else
                 b["CompilerRejected"] if case["ExpectedBuild"] == "fail" else
                 b["Accepted"] or b["CompilerRejected"]) for b in builds))
        rows.append(row)
        (directory / "result.json").write_text(json.dumps({
            "Schema": "fraktal.ab.v38-native-compile", "SchemaVersion": 1,
            "SdkSha256": sha256(sdk), "RuntimeAccepted": False,
            "SdkAssemblySha256": (sha256(sdk.with_suffix(".dll"))
                                  if sdk.with_suffix(".dll").is_file() else None),
            "Cases": rows, "Complete": len(rows) == len(case_names),
            "ConformsToExpectations": len(rows) == len(case_names)
                and all(r["ConformsToExpectation"] for r in rows),
        }, indent=2), encoding="utf-8")
    return json.loads((directory / "result.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generation", type=Path)
    parser.add_argument("directory", type=Path, help="new output directory")
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--target", action="append", choices=TARGETS)
    args = parser.parse_args()
    report = compile_cases(json.loads(args.generation.read_text(encoding="utf-8")),
                           args.directory.resolve(), tuple(args.case),
                           tuple(args.target) if args.target else TARGETS)
    print(json.dumps(report, indent=2))
    return 0 if report["ConformsToExpectations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

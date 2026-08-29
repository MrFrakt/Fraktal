#!/usr/bin/env python3
"""Regenerate and re-verify every Fraktal/AB Phase 0 artifact from a clean checkout.

R4 requires automated L5X regeneration and lint plus controller Verify/Build and
import checks that run from a clean checkout. Until the offline probe grew
``--create-seed`` that was impossible: every generator consumed an empty v33
project that had been produced by hand and only ever existed in a temporary
directory. This gate starts from nothing but the repository and the installed
Rockwell toolchain.

Stages:

1. create the empty v33 seed through the SDK and record its canonical hash;
2. regenerate the S1 data-path, S2 nested-AOI, S11 sequence-execution and S12
   type-probe fixtures from that seed;
3. import each full fixture through the SDK, requiring a clean import summary
   and no SDK error event;
4. export, re-import and re-export each, requiring canonical equality; and
5. for the S11 fixture, additionally require ID-independent chart equality.

Studio **Verify Controller** is opt-in through ``--verify``. That is not
squeamishness: Verify is only reachable through UI Automation on a logged-in
desktop, so a gate that always required it could not run on an unattended
agent. S15 owns that limitation; this tool reports honestly which checks ran.

Exit status: 0 when every executed stage passed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import fraktal_ab_l5x_compare
import fraktal_ab_l5x_inventory
import fraktal_ab_phase0_fixture
import fraktal_ab_s2_fixture
import fraktal_ab_s4_matrix_fixture
import fraktal_ab_s7_manifest_fixture
import fraktal_ab_s9_coherence_fixture
import fraktal_ab_s11_fixture
import fraktal_ab_s12_fixture
import fraktal_ab_s12_type_probe
import fraktal_ab_sfc_roundtrip_compare
from fraktal_ab_sdk_log_gate import audit_log


SCHEMA = "fraktal.ab.phase0-gate"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = 33
SEED_NAME = "FraktalPhase0"

TOOLS = Path(__file__).resolve().parent
DEFAULT_PROBE = (
    TOOLS / "Fraktal.Ab.OfflineProbe" / "bin" / "Debug" / "net10.0" / "win-x86"
    / "Fraktal.Ab.OfflineProbe.exe"
)
DEFAULT_VERIFY = TOOLS / "fraktal_ab_studio_verify.ps1"


@dataclass
class Stage:
    name: str
    passed: bool
    detail: dict[str, object] = field(default_factory=dict)


class GateError(RuntimeError):
    """A stage could not be executed, so no result is claimed for it."""


def run_probe(probe: Path, arguments: list[str]) -> str:
    completed = subprocess.run(
        [str(probe), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise GateError(
            f"offline probe failed ({completed.returncode}): "
            f"{output.strip().splitlines()[-1] if output.strip() else 'no output'}"
        )
    return output


def import_and_roundtrip(
    probe: Path, source: Path, workspace: Path, label: str
) -> Stage:
    """Import a generated L5X, then require a canonical export round trip."""
    acd = workspace / f"{label}.ACD"
    first = workspace / f"{label}_pass1.L5X"
    second_acd = workspace / f"{label}_roundtrip.ACD"
    second = workspace / f"{label}_pass2.L5X"

    import_log = run_probe(probe, [str(source), "--export", str(acd)])
    audit = audit_log(import_log, ("SaveAsAsync",), require_clean_import=True)
    if not audit["Clean"]:
        return Stage(f"{label}:import", False, {"findings": audit["Findings"]})

    run_probe(probe, [str(acd), "--export", str(first)])
    run_probe(probe, [str(first), "--export", str(second_acd)])
    run_probe(probe, [str(second_acd), "--export", str(second)])

    comparison = fraktal_ab_l5x_compare.compare(first, second)
    # The canonical comparison is export-against-export, so it cannot see a
    # construct Studio dropped during the *first* import - that construct would
    # be equally absent from both passes. The census closes exactly that hole by
    # comparing the generated declaration against the first export.
    census = fraktal_ab_l5x_inventory.compare(source, first)
    detail: dict[str, object] = {
        "acd": str(acd),
        "importSummaries": audit["ImportSummaries"],
        "canonicalSha256": comparison["FirstCanonicalSha256"],
        "canonicalRoundTrip": comparison["Equivalent"],
        "constructCensus": census["Counts"],
        "constructsSurvived": census["Equivalent"],
        "constructDifferences": census["Differences"],
    }
    passed = bool(comparison["Equivalent"]) and bool(census["Equivalent"])

    # Charts legitimately renumber on export, so the canonical comparator alone
    # cannot show the declaration survived. Only compare when one is present.
    chart_model = fraktal_ab_sfc_roundtrip_compare.chart_model(source)
    if chart_model["Charts"]:
        chart = fraktal_ab_sfc_roundtrip_compare.compare(source, first)
        detail["chartsCompared"] = chart["ChartsCompared"]
        detail["chartEquivalent"] = chart["Equivalent"]
        detail["chartDifferences"] = chart["Differences"]
        passed = passed and bool(chart["Equivalent"])

    return Stage(f"{label}:roundtrip", passed, detail)


def studio_verify(verify_script: Path, acd: Path, timeout: int) -> Stage:
    completed = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(verify_script), "-Revision", str(REVISION),
            "-Project", str(acd), "-ExpectedErrors", "0",
            "-ExpectedWarnings", "0", "-TimeoutSeconds", str(timeout),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    detail: dict[str, object] = {"exitCode": completed.returncode}
    try:
        detail["result"] = json.loads(completed.stdout)
    except (ValueError, TypeError):
        detail["output"] = (completed.stdout or completed.stderr or "").strip()
    return Stage(f"{acd.stem}:verify", completed.returncode == 0, detail)


def run_gate(
    workspace: Path,
    probe: Path,
    verify_script: Path | None = None,
    verify_timeout: int = 240,
) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    stages: list[Stage] = []

    seed_acd = workspace / "seed_v33.ACD"
    seed_l5x = workspace / "seed_v33.L5X"
    run_probe(
        probe,
        [
            "--create-seed", CONTROLLER, str(REVISION), SEED_NAME,
            str(seed_acd), "--export", str(seed_l5x),
        ],
    )
    seed_canonical = fraktal_ab_l5x_compare.canonical_sha256(seed_l5x)
    stages.append(Stage("seed", True, {
        "seed": str(seed_l5x), "canonicalSha256": seed_canonical,
    }))

    generated: list[tuple[str, Path]] = []
    for label, generator in (
        ("s1", fraktal_ab_phase0_fixture.generate),
        ("s2", fraktal_ab_s2_fixture.generate),
        ("s11", fraktal_ab_s11_fixture.generate),
        ("s12", fraktal_ab_s12_fixture.generate),
        ("s4matrix", fraktal_ab_s4_matrix_fixture.generate),
        ("s7manifest", fraktal_ab_s7_manifest_fixture.generate),
        ("s9coherence", fraktal_ab_s9_coherence_fixture.generate),
    ):
        output = workspace / f"{label}_fixture.L5X"
        evidence = generator(seed_l5x, output)
        stages.append(Stage(f"{label}:generate", True, {
            "output": str(output), "sha256": evidence["OutputSha256"],
        }))
        generated.append((label, output))

    probes = fraktal_ab_s12_type_probe.generate_all(
        seed_l5x, workspace / "s12_typeprobe"
    )
    stages.append(Stage("s12:typeprobe", True, {"cases": len(probes)}))

    for label, source in generated:
        stages.append(import_and_roundtrip(probe, source, workspace, label))

    if verify_script is not None:
        for label, _ in generated:
            acd = workspace / f"{label}.ACD"
            if acd.is_file():
                stages.append(studio_verify(verify_script, acd, verify_timeout))

    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "Workspace": str(workspace),
        "Controller": CONTROLLER,
        "MajorRevision": REVISION,
        "SeedCanonicalSha256": seed_canonical,
        "StudioVerifyRequested": verify_script is not None,
        "Stages": [
            {"name": stage.name, "passed": stage.passed, **stage.detail}
            for stage in stages
        ],
        "Failed": [stage.name for stage in stages if not stage.passed],
        "Passed": all(stage.passed for stage in stages),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace", type=Path,
        help="directory for disposable artifacts; a temporary one is used if omitted",
    )
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument(
        "--verify", action="store_true",
        help="also run Studio Verify Controller; needs a logged-in desktop session",
    )
    parser.add_argument("--verify-timeout", type=int, default=240)
    args = parser.parse_args(argv)

    if not args.probe.is_file():
        print(
            f"ERROR [phase0-gate] offline probe not built: {args.probe}",
            file=sys.stderr,
        )
        return 2
    verify_script = DEFAULT_VERIFY if args.verify else None
    if verify_script is not None and not verify_script.is_file():
        print(
            f"ERROR [phase0-gate] verify script missing: {verify_script}",
            file=sys.stderr,
        )
        return 2

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if args.workspace is None:
        temporary = tempfile.TemporaryDirectory(prefix="FraktalAbGate-")
        workspace = Path(temporary.name)
    else:
        workspace = args.workspace

    try:
        report = run_gate(workspace, args.probe, verify_script, args.verify_timeout)
    except (GateError, OSError, ValueError) as exc:
        print(f"ERROR [phase0-gate] {exc}", file=sys.stderr)
        return 2
    finally:
        if temporary is not None and args.workspace is None:
            # keep artifacts only when the caller named a workspace
            pass

    print(json.dumps(report, indent=2))
    if temporary is not None:
        temporary.cleanup()
    return 0 if report["Passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

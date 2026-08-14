#!/usr/bin/env python3
"""Machine-check the Fraktal/AB pre-implementation specification gates.

This is intentionally a specification/host-tooling check. It does not parse,
generate, import, or validate production L5X and it cannot close R2-R6. It keeps
the draft's readiness table, open/settled spike register, Phase 2 logical
contracts, and transport-neutral HMI wording internally consistent while those
gates remain open.

Usage:
    python tools/check_ab_spec.py

Exit status: 0 clean, 1 findings.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


PART_PATH = Path("Specification/Fraktal_AB_Part_III.md")
HMI_PATH = Path("Specification/HMI_CONTRACT.md")
R1_EVIDENCE_PATH = Path("Specification/AB_R1_PLATFORM_BASELINE_EVIDENCE.md")
S1_EVIDENCE_PATH = Path("Specification/AB_S1_CIP_DATA_PATH_EVIDENCE.md")
S2_EVIDENCE_PATH = Path("Specification/AB_S2_AOI_PARAMETER_EVIDENCE.md")
S4_S15_EVIDENCE_PATH = Path(
    "Specification/AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md"
)
OFFLINE_PROBE_PATH = Path(
    "FraktalCore/PLC/Allen-Bradley/tools/"
    "Fraktal.Ab.OfflineProbe/Program.cs"
)
SYMBOLIC_READ_PROBE_PATH = Path(
    "FraktalCore/PLC/Allen-Bradley/tools/"
    "fraktal_ab_symbolic_read_probe.py"
)
EIP_READ_PROBE_PATH = Path(
    "FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_eip_probe.py"
)
STUDIO_VERIFY_PROBE_PATH = Path(
    "FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_studio_verify.ps1"
)
INTERFACE_CATALOG_PATH = Path(
    "Specification/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md"
)

LOGICAL_CONTRACT_MARKERS = (
    "Logical registry schema, version 1",
    "manifest logical schema version 1",
    "logical value envelope, version 1",
    "mailbox logical schema version 1",
    "Repository negotiation schema, version 1",
    "HostEvents logical schema, version 1",
)

# These exact phrases were the measured mechanism leaks in the pre-R0 HMI
# contract. OPC UA remains valid when explicitly qualified as the TC3 mapping.
FORBIDDEN_HMI_PHRASES = (
    "desktop/mobile bind OPC UA directly",
    "OPC UA clients shall issue those operations",
    "The fixed bounded `HostEvents` OPC UA projection",
    "root Unit browse paths",
)

FORBIDDEN_OFFLINE_PROBE_APIS = (
    "DownloadAsync",
    "UploadAsync",
    "UploadToNewProjectAsync",
    "GoOnlineAsync",
    "SetControllerModeAsync",
    "SetCommunicationsPathAsync",
    "SetTagValueAsync",
    "controller.Write(",
    "SetPLCTime(",
    "CIP_SET_ATTRIBUTE",
    "CIP_RESET",
    "CIP_WRITE",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def audit_texts(
    part: str,
    hmi: str,
    r1_evidence_exists: bool = True,
    s1_evidence_exists: bool = True,
    s2_evidence_exists: bool = True,
    s4_s15_evidence_exists: bool = True,
    offline_probe: str | None = None,
    symbolic_read_probe: str | None = None,
    eip_read_probe: str | None = None,
    studio_verify_probe: str | None = None,
) -> list[str]:
    """Return human-readable findings for supplied document text."""
    findings: list[str] = []

    readiness = re.findall(
        r"^\|\s*R([0-6])\s+[^|]*\|\s*\*\*(PASS|OPEN)\*\*\s*\|",
        part,
        re.MULTILINE,
    )
    # R2 closed once S1/S2/S4/S11/S12 all recorded PASS; R3 closed when the six
    # logical contracts were frozen and gated. R4-R6 remain open.
    expected_readiness = [(str(index), "PASS" if index <= 3 else "OPEN")
                          for index in range(7)]
    if readiness != expected_readiness:
        findings.append(
            "readiness table must contain exactly R0-R3 PASS then R4-R6 OPEN; "
            f"found {readiness}"
        )

    readiness_section = part.partition("A failed gate changes this binding")[0]
    if "AB_R1_PLATFORM_BASELINE_EVIDENCE.md" not in readiness_section:
        findings.append("R1 readiness row does not link the platform evidence")
    if not r1_evidence_exists:
        findings.append("linked R1 platform evidence file is missing")
    if "AB_S1_CIP_DATA_PATH_EVIDENCE.md" not in readiness_section:
        findings.append("R2 readiness row does not link the S1 evidence")
    if not s1_evidence_exists:
        findings.append("linked S1 CIP data-path evidence file is missing")
    if "AB_S2_AOI_PARAMETER_EVIDENCE.md" not in readiness_section:
        findings.append("R2 readiness row does not link the S2 evidence")
    if not s2_evidence_exists:
        findings.append("linked S2 AOI-parameter evidence file is missing")
    if "AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md" not in readiness_section:
        findings.append("readiness table does not link the partial S4/S15 evidence")
    if not s4_s15_evidence_exists:
        findings.append("linked S4/S15 offline evidence file is missing")

    before_register, separator, register = part.partition(
        "## AB §12 — Spike register"
    )
    if not separator:
        findings.append("AB §12 spike-register heading is missing")
        register = ""

    body_spikes = {int(value) for value in re.findall(
        r"\[PROVISIONAL S(\d+)\]", before_register
    )}
    # S1, S2 and S7 are settled outright, so their normative clauses carry no
    # provisional marker at all. S4, S11 and S12 passed their main claim but
    # keep a marker for the part still owed, which is why they stay in this set
    # alongside the spikes that have not run.
    fully_settled = {1, 2, 7}
    expected_open_spikes = set(range(1, 16)) - fully_settled
    if body_spikes != expected_open_spikes:
        findings.append(
            "provisional clauses before AB §12 must reference exactly S3-S15; "
            f"missing={sorted(expected_open_spikes - body_spikes)} "
            f"extra={sorted(body_spikes - expected_open_spikes)}"
        )

    registered_spikes = {int(value) for value in re.findall(
        r"\|\s*S(\d+)(?:/S\d+)?\s*\|", register
    )}
    # Register rows such as S4/S11 contain two spike identifiers. Read every
    # S-number in the register table, not only the first column token.
    register_table = register.partition("---")[2].partition("\n\n")[0]
    registered_spikes |= {int(value) for value in re.findall(
        r"\bS(\d+)\b", register_table
    )}
    expected_registered_spikes = set(range(1, 16))
    if registered_spikes != expected_registered_spikes:
        findings.append(
            "AB §12 must register exactly S1-S15; "
            f"missing={sorted(expected_registered_spikes - registered_spikes)} "
            f"extra={sorted(registered_spikes - expected_registered_spikes)}"
        )

    if "| AB §2.7 | S1 | **PASS** |" not in register:
        findings.append("AB §12 must record S1 as PASS")
    if "| AB §2.2 | S2 | **PASS** |" not in register or \
            "| AB §3.3 | S2 | **PASS** |" not in register:
        findings.append("AB §12 must record both S2 rows as PASS")
    if "| AB §2.8, §3.5, §4.1 | S11 | **PASS** |" not in register:
        findings.append("AB §12 must record S11 as PASS")
    if "| AB §3.8 | S12 | **PASS** |" not in register:
        findings.append("AB §12 must record S12 as PASS")
    if "| AB §3.10 | S7 | **PASS** |" not in register:
        findings.append("AB §12 must record S7 as PASS")
    if "| AB §3.5 native SFC | S4 | **PASS** |" not in register:
        findings.append("AB §12 must record the S4 native-SFC row as PASS")
    if "| AB §2.5 | S4 | **PASS** |" not in register:
        findings.append("AB §12 must record the general S4 round-trip row as PASS")
    # S15 is the automated build gate and is still open; it must not be
    # promoted just because S4's source fidelity passed.
    if "| AB §5.4 | S15 | OPEN |" not in register:
        findings.append("AB §12 must keep S15 OPEN")

    for marker in LOGICAL_CONTRACT_MARKERS:
        if part.count(marker) != 1:
            findings.append(
                f"logical contract marker {marker!r} must occur exactly once"
            )

    for phrase in FORBIDDEN_HMI_PHRASES:
        if phrase in hmi:
            findings.append(
                f"HMI contract retains transport-specific base wording: {phrase!r}"
            )

    if offline_probe is None:
        findings.append("read-only AB offline probe is missing")
    if symbolic_read_probe is None:
        findings.append("read-only AB symbolic probe is missing")
    if eip_read_probe is None:
        findings.append("read-only AB EtherNet/IP probe is missing")
    if studio_verify_probe is None:
        findings.append("offline AB Studio Verify probe is missing")
    for probe_name, probe in (
        ("offline", offline_probe),
        ("symbolic", symbolic_read_probe),
        ("EtherNet/IP", eip_read_probe),
        ("Studio Verify", studio_verify_probe),
    ):
        if probe is None:
            continue
        for api in FORBIDDEN_OFFLINE_PROBE_APIS:
            if api in probe:
                findings.append(
                    f"read-only AB {probe_name} probe exposes forbidden API: {api}"
                )

    return findings


def audit_repo(root: Path = Path(".")) -> list[str]:
    part_path = root / PART_PATH
    hmi_path = root / HMI_PATH
    evidence_path = root / R1_EVIDENCE_PATH
    s1_evidence_path = root / S1_EVIDENCE_PATH
    s2_evidence_path = root / S2_EVIDENCE_PATH
    s4_s15_evidence_path = root / S4_S15_EVIDENCE_PATH
    offline_probe_path = root / OFFLINE_PROBE_PATH
    symbolic_read_probe_path = root / SYMBOLIC_READ_PROBE_PATH
    eip_read_probe_path = root / EIP_READ_PROBE_PATH
    studio_verify_probe_path = root / STUDIO_VERIFY_PROBE_PATH
    interface_catalog_path = root / INTERFACE_CATALOG_PATH
    missing = [str(path) for path in (
        part_path,
        hmi_path,
        interface_catalog_path,
    ) if not path.is_file()]
    if missing:
        return [f"required file missing: {path}" for path in missing]
    return audit_texts(
        _read(part_path),
        _read(hmi_path),
        r1_evidence_exists=evidence_path.is_file(),
        s1_evidence_exists=s1_evidence_path.is_file(),
        s2_evidence_exists=s2_evidence_path.is_file(),
        s4_s15_evidence_exists=s4_s15_evidence_path.is_file(),
        offline_probe=_read(offline_probe_path)
        if offline_probe_path.is_file() else None,
        symbolic_read_probe=_read(symbolic_read_probe_path)
        if symbolic_read_probe_path.is_file() else None,
        eip_read_probe=_read(eip_read_probe_path)
        if eip_read_probe_path.is_file() else None,
        studio_verify_probe=_read(studio_verify_probe_path)
        if studio_verify_probe_path.is_file() else None,
    )


def main() -> int:
    findings = audit_repo()
    if findings:
        for finding in findings:
            print(f"ERROR [ab-spec] {finding}")
        print(f"Fraktal/AB specification gate: {len(findings)} error(s).")
        return 1
    print("Fraktal/AB specification gate: clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

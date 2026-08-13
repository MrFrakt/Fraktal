#!/usr/bin/env python3
"""Cross-artifact consistency checks — the rules `plc_lint.py` cannot see.

`plc_lint.py` checks what is decidable from ONE source tree. These checks are
about agreement BETWEEN artifacts, which is where the defects that survive a
clean compile live:

  localization  every operator-facing key the PLC emits resolves in a shipped
                catalogue. A key with no entry renders on the HMI as the raw
                key - visible only to whoever is standing at the machine.

  inventory     the TcUnit runners instantiate every suite, and the counts a
                document claims match what the source actually contains. A
                suite that exists but is not in the runner's VAR block silently
                does not run, and the log's own totals still agree with
                themselves, so the gate passes while testing less.

  parity        a chain carried in more than one language says the same thing
                in each. Carrying N renditions is duplication §1.1 O9 forbids
                unless something enforces that they ARE the same chain; a
                ladder rendition once shipped two rungs whose gates read
                `EQ(215, 0)` - constantly FALSE, and compiled perfectly.

Severity: `error` fails the run, `warning` reports. Localization is a warning
today because the catalogue has a real backlog (see `--emit`); making it fail on
day one would just train everyone to skip the gate.

Usage
  python tools/check_consistency.py                 # all checks
  python tools/check_consistency.py localization    # one check
  python tools/check_consistency.py --strict        # warnings fail too
  python tools/check_consistency.py --emit          # Dart stubs for missing keys
Exit status: 0 clean, 1 findings, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Run as a script (`python tools/check_consistency.py`) the repo root is not on
# the path, so `tools.ld_dump` would not import; run as a module it already is.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PLC_ROOT = Path("FraktalCore/PLC/TwinCAT")
HMI_L10N = Path("FraktalCore/HMI/lib/localization")
WORKFLOW_DOC = Path("Specification/TWINCAT_XAE_WORKFLOW.md")

# A localization key literal in IEC source: 'project.step.foo' / 'std.error.bar'.
KEY_LITERAL = re.compile(r"'((?:project|std)\.[A-Za-z0-9_.]+)'")
# A catalogue entry in Dart: 'key': '…' or "key": "…".
CATALOGUE_ENTRY = re.compile(r"""["']([A-Za-z0-9_.]+)["']\s*:""")
CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)


@dataclass
class Finding:
    check: str
    severity: str          # "error" | "warning"
    where: str
    message: str

    def __str__(self) -> str:
        mark = "ERROR" if self.severity == "error" else "warn "
        return f"{mark} [{self.check}] {self.where}: {self.message}"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _sources(root: Path) -> list[Path]:
    """Authored PLC objects. Build output and installed libraries are not ours."""
    return [p for p in root.rglob("*.Tc*")
            if "_Libraries" not in p.parts and "_CompileInfo" not in str(p)
            and p.suffix in (".TcPOU", ".TcDUT", ".TcGVL", ".TcIO")]


def _is_test_source(path: Path) -> bool:
    """Test fixtures may use throwaway keys; shipping code may not."""
    return "_Tests" in path.name or path.name.startswith("FB_Probe") \
        or "scaffold" in str(path) or "Tests" in path.parts


# ---------------------------------------------------------------------------


def check_localization(root: Path) -> tuple[list[Finding], dict[str, set[str]]]:
    """Every key shipping PLC source emits resolves in a shipped catalogue."""
    findings: list[Finding] = []
    referenced: dict[str, set[str]] = {}
    for path in _sources(root):
        if _is_test_source(path):
            continue
        for match in KEY_LITERAL.finditer(_read(path)):
            referenced.setdefault(match.group(1), set()).add(path.name)

    catalogues = sorted(HMI_L10N.glob("*.dart")) if HMI_L10N.is_dir() else []
    if not catalogues:
        findings.append(Finding("localization", "error", str(HMI_L10N),
                                "no catalogue sources found"))
        return findings, {}
    known: set[str] = set()
    for catalogue in catalogues:
        known |= set(CATALOGUE_ENTRY.findall(_read(catalogue)))

    missing = {key: files for key, files in referenced.items() if key not in known}
    for key in sorted(missing):
        findings.append(Finding(
            "localization", "warning", sorted(missing[key])[0],
            f"key '{key}' has no catalogue entry; the HMI renders it verbatim"))
    return findings, missing


def check_inventory(root: Path) -> list[Finding]:
    """Runners instantiate every suite, and documented counts match source."""
    findings: list[Finding] = []
    suites: dict[str, int] = {}          # suite type -> TEST() count
    runners: dict[str, tuple[Path, list[str]]] = {}

    for path in _sources(root):
        text = _read(path)
        if "EXTENDS TcUnit.FB_TestSuite" in text and "scaffold" not in str(path):
            # The scaffold's suite is a copy-template: deliberately in no
            # manifest and born RED (§6.1), so "no runner instantiates it" is
            # the correct state, not a finding.
            suites[path.stem] = len(re.findall(r"\bTEST\('", text))
        declaration = re.search(r"PROGRAM\s+(PRG_\w*(?:Runner|TestRunner))(.*?)END_VAR",
                                text, re.S)
        if declaration:
            members = re.findall(r"^\s*\w+\s*:\s*(FB_\w+)\s*;",
                                 declaration.group(2), re.M)
            runners[declaration.group(1)] = (path, members)

    if not runners:
        findings.append(Finding("inventory", "error", str(root),
                                "no TcUnit runner found"))
        return findings

    registered: set[str] = set()
    for runner, (path, members) in sorted(runners.items()):
        for member in members:
            if member not in suites:
                findings.append(Finding(
                    "inventory", "error", path.name,
                    f"{runner} instantiates {member}, which is not a test suite"))
            registered.add(member)

    # A suite nobody instantiates does not run, and nothing says so.
    for suite in sorted(set(suites) - registered):
        findings.append(Finding(
            "inventory", "error", f"{suite}.TcPOU",
            f"{suite} is a test suite but no runner instantiates it; "
            f"its {suites[suite]} test(s) never execute"))

    # The counts a document promises must be the counts source can deliver.
    for runner, (_, members) in sorted(runners.items()):
        live = [m for m in members if m in suites]
        totals = (len(live), sum(suites[m] for m in live))
        findings += _check_documented_counts(runner, totals)
    return findings


def _check_documented_counts(runner: str, totals: tuple[int, int]) -> list[Finding]:
    """`TWINCAT_XAE_WORKFLOW.md` §6.3 grades a run against these numbers."""
    if not WORKFLOW_DOC.is_file():
        return []
    suites, tests = totals
    text = _read(WORKFLOW_DOC)
    # The document deliberately keeps the ARCHIVED baseline beside the current
    # expectation, so grade only the table whose header says which is which.
    current = text.split("Expected from current source")
    if len(current) > 1:
        text = current[1]
    # Rows read "| … | `PRG_X` | 94 tests / 29 suites / 0 failed |".
    rows = re.findall(r"`" + re.escape(runner) + r"`[^|]*\|\s*(\d+) tests / (\d+) suites",
                      text)
    if not rows:
        return [Finding("inventory", "warning", WORKFLOW_DOC.name,
                        f"{runner} has {tests} tests / {suites} suites in source "
                        f"but no expected-count row")]
    findings = []
    for stated_tests, stated_suites in rows:
        if (int(stated_tests), int(stated_suites)) != (tests, suites):
            findings.append(Finding(
                "inventory", "error", WORKFLOW_DOC.name,
                f"{runner}: document expects {stated_tests} tests / "
                f"{stated_suites} suites, source has {tests} / {suites}"))
    return findings


def check_parity(root: Path) -> list[Finding]:
    """A chain in several languages is the same chain in each.

    Compares the ST twin against every `FB_<LANG>_<Name>` rendition beside it:
    which steps exist, and where each one can go. Both are read from the
    artifact - the ST `CASE` labels and `M_Advance` targets, the ladder's
    `EQ(_step, N)` gates and `MOVE … -> _step` targets - so a rendition that
    quietly stopped agreeing is a finding rather than a surprise.
    """
    findings: list[Finding] = []
    try:
        from tools.ld_dump import gate_step          # noqa: F401  (import check)
        import xml.etree.ElementTree as ET
        from tools.ld_rung_gen import split_networks
    except Exception as error:                        # pragma: no cover
        return [Finding("parity", "error", "tools", f"cannot load LD reader: {error}")]

    for path in _sources(root):
        prefix = re.match(r"FB_(LD)_(\w+)$", path.stem)
        if not prefix or path.suffix != ".TcPOU":
            continue
        twin = path.with_name(f"FB_{prefix.group(2)}.TcPOU")
        if not twin.is_file():
            findings.append(Finding("parity", "warning", path.name,
                                    f"no ST twin {twin.name} to compare against"))
            continue
        st = _st_chain(_read(twin))
        ld = _ld_chain(_read(path), split_networks, ET)
        for step in sorted(set(st) - set(ld)):
            findings.append(Finding("parity", "error", path.name,
                                    f"step {step} exists in {twin.name} but not here"))
        for step in sorted(set(ld) - set(st)):
            findings.append(Finding("parity", "error", path.name,
                                    f"step {step} exists here but not in {twin.name}"))
        for step in sorted(set(st) & set(ld)):
            if st[step] != ld[step]:
                findings.append(Finding(
                    "parity", "error", path.name,
                    f"step {step} goes to {sorted(ld[step])} here but "
                    f"{sorted(st[step])} in {twin.name}"))
        findings += _check_step_effects(path, twin, split_networks, ET)
    return findings


def _check_step_effects(path: Path, twin: Path, split_networks, ET
                        ) -> list[Finding]:
    """Every step writes the same SHARED state in both renditions.

    Same steps and same transitions is not the same chain: `FB_LD_PressDemoAuto`
    step 190 matched its ST twin on both and still dropped
    `_startLatched := FALSE`, so the two-hand abort returned to the wait step
    with the start still latched and the cycle ran again, forever. Nothing
    caught it - which is why this compares what each step DOES, not just where
    it goes.

    Only state that escapes the chain is compared: the roots the ST twin
    declares `REFERENCE TO` (child modules, published outputs, the Unit's
    latch). A rendition's own locals are excluded on purpose - `_partProcessed`
    in ST is `_processed` in ladder, and naming scratch differently is not a
    divergence.

    A PLAIN ladder coil is exempt everywhere: it writes its rail's value every
    scan, so it already drives the symbol FALSE in every other step and the ST
    twin's explicit clears have no ladder counterpart to find. Set/Reset coils
    latch, so those ARE compared step by step.
    """
    from tools.ld_dump import _value

    st_text, ld_text = _read(twin), _read(path)
    roots = _reference_roots(st_text)
    if not roots:
        return []
    st_writes = _st_step_writes(st_text, roots)
    ld_writes, continuous = _ld_step_writes(ld_text, split_networks, ET, _value)

    findings: list[Finding] = []
    for step in sorted(set(st_writes) & set(ld_writes)):
        for name in sorted(st_writes[step] - ld_writes[step]):
            if name.split(".")[0] in continuous:
                continue
            findings.append(Finding(
                "parity", "error", path.name,
                f"step {step} assigns {name} in {twin.name} but no coil here "
                f"writes it - the ladder rung silently drops that effect"))
    return findings


def _reference_roots(text: str) -> set[str]:
    """Names the ST chain declares `REFERENCE TO`: the state that outlives it."""
    declaration = re.search(r"FUNCTION_BLOCK.*?END_VAR\]\]", text, re.S)
    if not declaration:
        return set()
    roots: set[str] = set()
    for line in declaration.group(0).splitlines():
        line = re.sub(r"//.*", "", line)
        if "REFERENCE TO" not in line:
            continue
        names = line.partition(":")[0]
        roots.update(name.strip() for name in names.split(",") if name.strip())
    return roots


def _st_step_writes(text: str, roots: set[str]) -> dict[int, set[str]]:
    """`CASE _step OF` label -> the shared symbols that branch assigns."""
    body = re.search(r"CASE _step OF(.*?)\nELSE", text, re.S)
    if not body:
        return {}
    parts = re.split(r"\n    (\d+):", body.group(1))[1:]
    writes: dict[int, set[str]] = {}
    for number, branch in zip(parts[0::2], parts[1::2]):
        branch = re.sub(r"//[^\n]*", "", branch)
        # A statement lvalue, never a named argument: `Foo(Bar := x)` binds a
        # parameter and assigns nothing.
        lvalues = set(re.findall(
            r"(?:^|;|\bTHEN\b|\bELSE\b|\bDO\b)\s*([A-Za-z_][\w.]*)\s*:=",
            branch, re.M))
        writes[int(number)] = {n for n in lvalues if n.split(".")[0] in roots}
    return writes


def _ld_step_writes(text: str, split_networks, ET, _value
                    ) -> tuple[dict[int, set[str]], set[str]]:
    """(`EQ(_step, N)` gate -> symbols its rung writes, continuously-driven roots)."""
    from tools.ld_dump import gate_step

    per_step: dict[int, set[str]] = {}
    continuous: set[str] = set()
    _, networks, _, _ = split_networks(text)
    for raw in networks:
        network = ET.fromstring(raw)
        written: set[str] = set()
        for node in network.iter("o"):
            for slot in node.findall(
                    "./o[@n='OutputItems']/l2[@n='OutputItems']/o"):
                name = (_value(slot, "Operand") or "").strip('"')
                if not name:
                    continue
                written.add(name)
                flags = slot.find("./o[@n='Flags']")
                if (node.get("t") == "BoxTreeAssign" and flags is not None
                        and (_value(flags, "Flags") or "0") == "0"):
                    continuous.add(name.split(".")[0])
            # A box output bound to a variable (`M_TryIssue` -> `_doStep`).
            for slot in node.findall("./l2[@n='OutputItems']/o"):
                operand = slot.find("./o[@n='Operand']")
                if operand is None:
                    continue
                name = (_value(operand, "Operand") or "").strip('"')
                if name:
                    written.add(name)
        step = gate_step(network)
        if step is not None:
            per_step[step] = written
    return per_step, continuous


def _st_chain(text: str) -> dict[int, set[int]]:
    """`CASE _step OF` label -> the set of steps `M_Advance` can reach."""
    body = re.search(r"CASE _step OF(.*?)\nELSE", text, re.S)
    if not body:
        return {}
    parts = re.split(r"\n    (\d+):", body.group(1))[1:]
    chain: dict[int, set[int]] = {}
    for number, branch in zip(parts[0::2], parts[1::2]):
        advance = re.search(r"M_Advance\((.*?)\);", branch, re.S)
        chain[int(number)] = ({int(n) for n in re.findall(r":=\s*(\d+)", advance.group(1))}
                              if advance else set())
    return chain


def _ld_chain(text: str, split_networks, ET) -> dict[int, set[int]]:
    """`EQ(_step, N)` gate -> the set of steps its `MOVE … -> _step` can write."""
    chain: dict[int, set[int]] = {}
    _, networks, _, _ = split_networks(text)
    for raw in networks:
        root = ET.fromstring(raw)
        gate, targets = None, set()
        for box in root.iter("o"):
            # A box is a node carrying a BoxType; testing t="BoxTreeBox" misses
            # every one a `<l2 … cet="BoxTreeBox">` typed collectively.
            kind = box.find("./v[@n='BoxType']")
            if kind is None:
                continue
            operands = [(o.find("./o[@n='Operand']/v[@n='Operand']").text or "").strip('"')
                        for o in box.findall("./l2[@n='InputItems']/o")
                        if o.get("t") == "BoxTreeOperand"]
            if kind.text == '"EQ"' and len(operands) == 2 and operands[0] == "_step":
                gate = int(operands[1])
            elif kind.text == '"MOVE"':
                written = [o.find("./v[@n='Operand']") for o in
                           box.findall("./o[@n='OutputItems']/l2[@n='OutputItems']/o")]
                if any(w is not None and w.text == '"_step"' for w in written):
                    targets.add(int(operands[-1]))
        if gate is not None:
            chain[gate] = targets
    return chain


# ---------------------------------------------------------------------------


def emit_stubs(missing: dict[str, set[str]]) -> str:
    """Dart map entries for the missing keys, so filling the catalogue is paste."""
    lines = ["  // Generated by tools/check_consistency.py --emit.",
             "  // Replace every TODO with operator-facing English before shipping."]
    for key in sorted(missing):
        origin = sorted(missing[key])[0]
        lines.append(f"  '{key}': 'TODO',  // {origin}")
    return "\n".join(lines)


CHECKS = {"localization": None, "inventory": check_inventory, "parity": check_parity}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checks", nargs="*", choices=sorted(CHECKS) + [], default=[],
                        help="checks to run (default: all)")
    parser.add_argument("--root", default=str(PLC_ROOT), type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as failures")
    parser.add_argument("--emit", action="store_true",
                        help="print Dart stubs for missing localization keys")
    parser.add_argument("--quiet", action="store_true", help="only findings")
    args = parser.parse_args(argv[1:])

    selected = args.checks or sorted(CHECKS)
    findings: list[Finding] = []
    missing: dict[str, set[str]] = {}

    if "localization" in selected:
        local_findings, missing = check_localization(args.root)
        findings += local_findings
    for name in selected:
        if name != "localization":
            findings += CHECKS[name](args.root)

    if args.emit:
        print(emit_stubs(missing))
        return 0

    for finding in findings:
        print(finding)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    if not args.quiet:
        print(f"\ncheck_consistency: {len(errors)} error(s), {len(warnings)} warning(s) "
              f"across {', '.join(selected)}")
        if warnings and not args.strict:
            print("  warnings do not fail this run; use --strict to require them, "
                  "and --emit to generate the missing catalogue entries")
    return 1 if errors or (warnings and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

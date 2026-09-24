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

  readsurface   every node the generic HMI reads is published by the AB
                projection or declared absent with a reason. The HMI renders a
                missing node as a default, so a projection can stop publishing
                something and every screen keeps working, slightly wrong.

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

# The ladder/chart readers ship inside the binding they parse
# (FraktalCore/PLC/TwinCAT/tools). This gate stays at the repository root
# because it spans PLC, HMI and Specification, so it reaches across for them.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                       / "FraktalCore/PLC/TwinCAT/tools"))

PLC_ROOT = Path("FraktalCore/PLC/TwinCAT")
HMI_L10N = Path("FraktalCore/HMI/lib/localization")
WORKFLOW_DOC = Path("Specification/Guides/TWINCAT_XAE_WORKFLOW.md")
CI_WORKFLOW = Path(".github/workflows/ci.yml")

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
        findings += _check_ci_counts(runner, totals)
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


def _check_ci_counts(runner: str, totals: tuple[int, int]) -> list[Finding]:
    """`ci.yml` grades the TcUnit gate against these numbers too.

    The counts live in three places - this workflow, the guide's S6.3 table, and
    every evidence record - and only the guide was checked. That is not
    hypothetical: the robot planner suite landed with the guide updated to
    126/34 while `ci.yml` stayed at 116/33, so the gate would have failed on
    counts rather than on tests, and nothing would have said why until someone
    read the job log. A pin no gate reads is a pin that drifts.
    """
    if not CI_WORKFLOW.is_file():
        return []
    suites, tests = totals
    text = _read(CI_WORKFLOW)
    # Rows read "--expected-tests 126 --expected-suites 34 --expected-runner PRG_X".
    rows = re.findall(
        r"--expected-tests\s+(\d+)\s+--expected-suites\s+(\d+)\s+"
        r"--expected-runner\s+" + re.escape(runner) + r"",
        text)
    if not rows:
        return [Finding("inventory", "warning", CI_WORKFLOW.name,
                        f"{runner} has {tests} tests / {suites} suites in source "
                        f"but no --expected-tests row")]
    findings = []
    for stated_tests, stated_suites in rows:
        if (int(stated_tests), int(stated_suites)) != (tests, suites):
            findings.append(Finding(
                "inventory", "error", CI_WORKFLOW.name,
                f"{runner}: workflow expects {stated_tests} tests / "
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
        from ld_dump import gate_step                # noqa: F401  (import check)
        import xml.etree.ElementTree as ET
        from ld_rung_gen import split_networks
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
    from ld_dump import _value

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
    from ld_dump import gate_step

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


# --------------------------------------------------------------- read surface

HMI_MAPPER = Path("FraktalCore/HMI/lib/data/opcua_snapshot_mapper.dart")
AB_TOOLS = Path("FraktalCore/PLC/Allen-Bradley/tools")

# Two reasons, not fifty opinions. Anything outside the Phase 4 projection is
# absent for the same reason, and saying so once keeps this table a statement
# of fact rather than a place to invent a roadmap.
_DEFERRED = ("a recorded deferral in FraktalCore/PLC/Allen-Bradley/README.md")
_NOT_PROJECTED = ("outside the Phase 4 projection, which publishes the "
                  "manifest, module status and the command mailbox")
_REASON_ONLY = "the AB diagnostic record is a reason code and nothing else"

# What the AB binding does not publish, one entry per absent CAPABILITY rather
# than per field. Enumerating the 200-odd suffixes would be a list nobody
# reads; naming the record is a claim someone can check. An entry matches a
# read suffix that equals it, or continues with '/' or '['.
AB_ABSENT = {
    "Access": _NOT_PROJECTED,
    "ActiveSteps": _NOT_PROJECTED,
    "AlarmLog": _NOT_PROJECTED,
    "AvailableModelCount": _DEFERRED,
    "AvailableModels": _DEFERRED,
    "Blocked": _NOT_PROJECTED,
    "Catalog": _NOT_PROJECTED,
    "CatalogCount": _NOT_PROJECTED,
    "ControlPower": _DEFERRED,
    "CurrentStep/AwaitingLabel": _NOT_PROJECTED,
    "CurrentStep/Class": _NOT_PROJECTED,
    "CurrentStep/Conds": _DEFERRED,
    "CurrentStep/ExpectedTime": _NOT_PROJECTED,
    "CurrentStep/StepName": ("the manifest carries step names, so the HMI "
                             "resolves them from it, not from a live tag"),
    "CurrentStep/TimeClass": _NOT_PROJECTED,
    "Decision/Options": _NOT_PROJECTED,
    "Decision/Prompt": _NOT_PROJECTED,
    "HostEvents": _NOT_PROJECTED,
    "MachineState": _NOT_PROJECTED,
    "Model": _DEFERRED,
    "Nameplate": _NOT_PROJECTED,
    "Oee": _NOT_PROJECTED,
    "OeeTrend": _NOT_PROJECTED,
    "OeeTrendHead": _NOT_PROJECTED,
    "Part": _DEFERRED,
    "Profiler": _NOT_PROJECTED,
    "ReworkCount": "the unit context carries Good and Scrap only",
    "RunStyle": _NOT_PROJECTED,
    "RunningPublished": ("the projection derives Status/State from the "
                         "context's Running rather than republishing it"),
    "Safety": _DEFERRED,
    "SequenceAnnotationCount": _NOT_PROJECTED,
    "SequenceAnnotations": _NOT_PROJECTED,
    "SequenceStepCount": _NOT_PROJECTED,
    "SequenceSteps": _NOT_PROJECTED,
    "SequenceViewEnabled": _NOT_PROJECTED,
    "SignalTower": "the bench press has no signal tower",
    "Starved": _NOT_PROJECTED,
    "StateFlagCount": _NOT_PROJECTED,
    "StateFlags": _NOT_PROJECTED,
    "Status/Diagnostic/Description": ("Logix v33 ST cannot assign a string "
                                      "literal, so the controller answers "
                                      "with a numeric key"),
    "Status/Diagnostic/IoAddress": _REASON_ONLY,
    "Status/Diagnostic/IoTag": _REASON_ONLY,
    "Status/Diagnostic/Since": _REASON_ONLY,
    "Status/Diagnostic/TimeSynchronized": _REASON_ONLY,
    "Status/ControlDomainId": _DEFERRED,
    "Status/DescriptionKey": ("the manifest carries the display name key, "
                              "which is what the projection publishes"),
    "Status/TileEnable": _NOT_PROJECTED,
    "StopPendingPublished": _NOT_PROJECTED,
    "SupportedRunStylesPublished": _NOT_PROJECTED,
    "SystemHealth": _NOT_PROJECTED,
    "Timing": _NOT_PROJECTED,
    "Topology": "physical I/O is a recorded deferral; no fieldbus root",
}

# Published for `opcua_repository.dart`, which writes the request and polls the
# response. The snapshot mapper never reads it, and that is correct.
AB_PUBLISHED_FOR_REPOSITORY = ("HmiRequest/", "HmiResponse/")


def _mapper_surface(text: str) -> tuple[set[str], set[str], list[str]]:
    """Every node path `opcua_snapshot_mapper.dart` reads, resolved.

    The mapper names most of what it reads through a prefix variable rebound in
    each loop, so a position-blind scan attributes every read to the last
    binding in the file. Resolution here is positional, and anything that does
    not resolve is RETURNED as unresolved rather than dropped - a reader that
    quietly reports less than it read is the defect this gate exists to catch,
    and the reader that found the last one had shipped it twice.
    """
    bind_indexed = re.compile(r"final\s+(\w+)\s*=\s*"
                              r"_(?:indexedPrefix|arrayElement)\("
                              r"\s*values\s*,\s*'([^']*)'")
    bind_literal = re.compile(r"final\s+(\w+)\s*=\s*'([^']*)'\s*;")
    array_read = re.compile(r"_arrayElement\(\s*values\s*,\s*'([^']*)'")
    direct = re.compile(r"values\[\s*'([^']*)'\s*\]")
    scan = re.compile(r"\.endsWith\('/([^']*)'\)")
    alarm_call = re.compile(r"_alarmEvent\(\s*values\s*,\s*(\w+)")

    # `_alarmEvent` reads through a parameter, so its reads belong to whatever
    # each call site passed. Lift its body out and expand it per call site.
    alarm_suffixes: list[str] = []
    body = re.search(r"AlarmEvent\?\s+_alarmEvent\(.*?\n\}", text, re.S)
    if body:
        token = "$prefix/"
        alarm_suffixes = [hit.group(1)[len(token):]
                          for hit in direct.finditer(body.group(0))
                          if hit.group(1).startswith(token)]

    events: list[tuple[int, str, str, str]] = []
    for hit in bind_indexed.finditer(text):
        events.append((hit.start(), "bind", hit.group(1),
                       hit.group(2).rstrip("/") + "[*]"))
    for hit in bind_literal.finditer(text):
        events.append((hit.start(), "bind", hit.group(1), hit.group(2)))
    for hit in direct.finditer(text):
        events.append((hit.start(), "read", "", hit.group(1)))
    for hit in array_read.finditer(text):
        events.append((hit.start(), "read", "", hit.group(1) + "[*]"))
    for hit in scan.finditer(text):
        events.append((hit.start(), "read", "", "$base/" + hit.group(1)))
    for hit in alarm_call.finditer(text):
        for suffix in alarm_suffixes:
            events.append((hit.start(), "read", "",
                           "$" + hit.group(1) + "/" + suffix))
    events.sort(key=lambda event: event[0])

    def resolve(key: str, env: dict[str, str], depth: int = 0) -> str:
        if depth > 8:
            return key
        head = re.match(r"\$(\w+)(.*)$", key)
        if not head:
            return key
        name, rest = head.group(1), head.group(2)
        if name == "base":
            return rest.lstrip("/")
        if name not in env:
            return key
        joiner = "" if not rest or rest.startswith("/") else "/"
        return resolve(env[name].rstrip("/") + joiner + rest, env, depth + 1)

    env: dict[str, str] = {}
    modules: set[str] = set()
    topology: set[str] = set()
    unresolved: list[str] = []
    for _, kind, name, value in events:
        if kind == "bind":
            env[name] = value
            continue
        resolved = re.sub(r"\[\$?\w+\]", "[*]", resolve(value, env))
        if resolved.startswith("$topology/"):
            topology.add(resolved[len("$topology/"):])
        elif "$" in resolved:
            unresolved.append(resolved)
        elif resolved:
            modules.add(resolved)
    return modules, topology, sorted(set(unresolved))


def _ab_published() -> set[str]:
    """Suffixes the AB projection publishes, from the offline projector.

    Built through the projection's own test fixture rather than a second copy
    of the header/context construction: duplicating that here would make this
    gate agree with a stale snapshot of the projector instead of with the
    projector (§1.1 O9).

    Paths are relative to the repository root, like `HMI_L10N`, and NOT to
    `--root`, which points at the TwinCAT tree. This function raises rather
    than returning empty on a missing or unimportable fixture: the first cut of
    this gate swallowed both and reported a clean run while checking nothing,
    which is the exact failure it was written to catch.
    """
    fixture_path = AB_TOOLS / "test_fraktal_ab_projection.py"
    if not fixture_path.is_file():
        raise FileNotFoundError(f"{fixture_path} is missing")
    sys.path.insert(0, str(AB_TOOLS))
    try:
        import test_fraktal_ab_projection as fixture
    finally:
        sys.path.remove(str(AB_TOOLS))
    document = fixture.build(mailbox_state={
        "response": {"AckSequence": 0, "Accepted": 0, "DiagnosticKey": 0},
        "requestSequence": 0,
    })
    values = document["values"]
    marker = "/Status/Name"
    bases = sorted({key[: -len(marker)] for key in values
                    if key.endswith(marker)}, key=len, reverse=True)
    published: set[str] = set()
    for key in values:
        for base in bases:
            if key.startswith(base + "/"):
                published.add(re.sub(r"\[\d+\]", "[*]", key[len(base) + 1:]))
                break
    return published


def _absent_reason(suffix: str) -> str | None:
    for prefix, reason in AB_ABSENT.items():
        if suffix == prefix or suffix.startswith(prefix + "/") \
                or suffix.startswith(prefix + "["):
            return reason
    return None


def check_read_surface(root: Path) -> list[Finding]:
    """Every node the HMI reads is published by AB, or declared absent here.

    The HMI is generic: it reads what a conforming station publishes, and a
    node that is simply missing renders as a default. That is the right runtime
    behaviour and a terrible development one - a projection can stop publishing
    something and every screen keeps working, slightly wrong.
    `SupportedModesPublished` went missing exactly that way, and the symptom
    was a mode bar offering one mode, three layers from the cause.
    """
    findings: list[Finding] = []
    where = str(HMI_MAPPER)
    gate = Path(__file__).name
    if not HMI_MAPPER.is_file():
        return [Finding("readsurface", "error", where,
                        "the HMI snapshot mapper is missing - this gate reads "
                        "it from the repository root, not from --root")]
    modules, topology, unresolved = _mapper_surface(_read(HMI_MAPPER))

    for key in unresolved:
        findings.append(Finding(
            "readsurface", "error", where,
            f"cannot resolve which node this reads: {key!r}. Teach "
            "_mapper_surface the binding rather than letting the gate check "
            "less than the mapper reads"))

    try:
        published = _ab_published()
    except Exception as exc:
        return findings + [Finding(
            "readsurface", "error", str(AB_TOOLS),
            f"cannot build the AB projection offline ({type(exc).__name__}: "
            f"{exc}), so nothing was compared. Fix the import rather than "
            "letting the gate pass by checking nothing")]

    # The fieldbus topology hangs off its own root, not off a module, so it is
    # checked as one capability rather than suffix by suffix.
    if topology and not _absent_reason("Topology"):
        findings.append(Finding(
            "readsurface", "error", where,
            f"the HMI reads {len(topology)} fieldbus topology nodes and the "
            "AB projection neither publishes a topology root nor declares one "
            "absent"))

    for suffix in sorted(modules):
        if suffix in published or _absent_reason(suffix):
            continue
        findings.append(Finding(
            "readsurface", "error", where,
            f"the HMI reads '<module>/{suffix}' and the AB projection neither "
            "publishes it nor declares it absent - publish it, or add it to "
            "AB_ABSENT with the reason"))

    for prefix, reason in sorted(AB_ABSENT.items()):
        covered = {s for s in modules
                   if s == prefix or s.startswith(prefix + "/")
                   or s.startswith(prefix + "[")}
        if not covered and prefix != "Topology":
            findings.append(Finding(
                "readsurface", "error", gate,
                f"AB_ABSENT declares '{prefix}' absent ({reason}) but the HMI "
                "no longer reads it - delete the entry"))
        conflict = sorted(covered & published)
        if conflict:
            findings.append(Finding(
                "readsurface", "error", gate,
                f"AB_ABSENT declares '{prefix}' absent but the projection "
                f"publishes {conflict[0]!r} - the reason is stale"))

    for suffix in sorted(published - modules):
        if suffix.startswith(AB_PUBLISHED_FOR_REPOSITORY):
            continue
        findings.append(Finding(
            "readsurface", "warning", "fraktal_ab_projection.py",
            f"the AB projection publishes '<module>/{suffix}' and no HMI "
            "client reads it - either something is meant to and does not, or "
            "it is surface nobody pays for"))
    return findings


CHECKS = {"localization": None, "inventory": check_inventory,
          "parity": check_parity, "readsurface": check_read_surface}


def build_parser() -> argparse.ArgumentParser:
    """Separate from main() so the CLI itself is testable.

    The one bug this gate has ever shipped was in argument parsing, not in a
    check, and no test could reach it while the parser was a local.
    """
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    # No `choices=` here on purpose. With nargs="*", argparse in Python <= 3.12
    # validates the DEFAULT against choices, so an empty default makes the
    # no-argument form - the documented "run everything" invocation - die with
    # "invalid choice: '[]'" and exit 2. Python 3.13+ stopped doing that, which
    # is why this survived: every caller either passed all three check names
    # explicitly or ran a newer interpreter. Validate by hand instead, and keep
    # the same message argparse would have produced.
    parser.add_argument("checks", nargs="*", default=[],
                        metavar="{" + ",".join(sorted(CHECKS)) + "}",
                        help="checks to run (default: all)")
    parser.add_argument("--root", default=str(PLC_ROOT), type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as failures")
    parser.add_argument("--emit", action="store_true",
                        help="print Dart stubs for missing localization keys")
    parser.add_argument("--quiet", action="store_true", help="only findings")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    unknown = [c for c in args.checks if c not in CHECKS]
    if unknown:
        parser.error(f"argument checks: invalid choice: {unknown[0]!r} "
                     f"(choose from {', '.join(sorted(CHECKS))})")
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

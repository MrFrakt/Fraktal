#!/usr/bin/env python3
"""Fraktal PLC lint — the machine-verifiable rules of Core §1.5 / §5.5 / §6.8.

Core §1.5 makes a CI/lint gate a **shall**: "A CI/lint gate (§5.5, §6.8) shall
check the machine-verifiable requirements — naming, step records, condition
records, and contract usage — on every commit."

This checks the rules that are decidable from source text alone. It is not a
compiler: it cannot resolve library symbols, so it deliberately does not attempt
type checking (that is the XAE/CI compile step, tracked separately).

Rules
  N1  POU/DUT/GVL file basename matches its declared object name.
  N2  Declared objects carry a Fraktal/PLCopen prefix:
        FB_ function block · E_ enum · ST_ struct · I_ interface
        PL_ parameter list · GVL_ global var list · F_ function
  C1  Defaulted METHOD VAR_INPUT (`x : T := v;`) must be guarded by a
        `{IF defined (FRAKTAL_TC3_4024)}` conditional pragma. Defaulted method
        inputs need TwinCAT >= 3.1.4026; the library targets modern TwinCAT and
        supports 4024 as a legacy profile, so the feature is allowed but the
        legacy form must exist alongside it (see Params/PL_FraktalCompat.TcGVL).
        With `--profile 4024`, ANY defaulted input is reported — guarded or not —
        because that build must contain no 4026-only construct at all.
  C2  No IEC/TwinCAT reserved word as a variable or enumeration identifier.
        These desync the parser and produce a cascade of misleading errors.
  C3  Balanced <Method> open/close tags (guards hand-edited .TcPOU XML).
  C4  Unique GUIDs within a file (a duplicated Id silently shadows an object).
  D1  Shipping concrete modules declare the four physical contract members;
        every `ST_*ParCfg` record starts with `SchemaVersion : UINT`.
  E1  PLC enum ordinals/names match the generic HMI Dart transport enums.
  H1  Concrete module bodies contain only inherited `Cyclic();`; lifecycle-hook
        overrides call `SUPER^` first (except staged `OnModeExit`).
  C5  Every authored ST `CASE` has an `ELSE` safe reaction.
  C6  `CASE` labels are integral/enum labels, never string literals.
  C7  A guard never dereferences or indexes the symbol it is testing against 0
        in the same condition — TwinCAT does not short-circuit AND/OR, so the
        protected operand is evaluated anyway.
  S1  Every multi-step sequence extends `FB_SequenceBase` and carries the shared
        step/result/advance skeleton.
  A1  An EquipmentModule declaration never contains a Unit instance.
  R1  Type reason constants are >=10000 and collision-free repository-wide.
  P1  Project compile inputs resolve, authored sources are listed, XAE system
        projects do not load the same source object through two PLC projects,
        and deployed roots carry an instance-level `OPC.UA.DA := '1'`.

Usage
  python tools/plc_lint.py [root ...]        # default: FraktalCore/PLC/TwinCAT
  python tools/plc_lint.py --quiet           # only failures
  python tools/plc_lint.py --profile 4024    # legacy build: no 4026-only feature
Exit status: 0 clean, 1 violations found, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_ROOTS = [Path("FraktalCore/PLC/TwinCAT")]

# Generated/vendored trees that are not authored source.
SKIP_PARTS = {
    "_Boot", "_ScopeConfig", "_Libraries", "Dependancies", "Release",
    "third_party", ".git",
}

OBJECT_TAG = re.compile(r"<(POU|DUT|GVL|Itf)\s+Name=\"([^\"]+)\"", re.I)
METHOD_BLOCK = re.compile(r"<Method\s+Name=\"([^\"]+)\"[^>]*>(.*?)</Method>", re.S | re.I)
VAR_INPUT_BLOCK = re.compile(r"VAR_INPUT(.*?)END_VAR", re.S | re.I)
GUID_ATTR = re.compile(r"\bId=\"(\{[0-9a-fA-F-]+\})\"")
DECL_WITH_DEFAULT = re.compile(r"^\s*([A-Za-z_]\w*)\s*:\s*[^;:=]*:=")
# Conditional pragmas. The legacy switch is one define (PL_FraktalCompat).
LEGACY_DEFINE = "FRAKTAL_TC3_4024"
COMPAT_IF = re.compile(
    r"^\{\s*IF\s+defined\s*\(\s*" + LEGACY_DEFINE + r"\s*\)\s*\}", re.I)
PRAGMA_ELSE = re.compile(r"^\{\s*ELSE\s*\}", re.I)
PRAGMA_END = re.compile(r"^\{\s*END_IF\s*\}", re.I)
# Identifier declarations inside any VAR block (name : TYPE).
DECL_ANY = re.compile(r"^\s*([A-Za-z_]\w*)\s*:\s*[A-Za-z_]")
# A FUNCTION_BLOCK may carry any combination of access/extension qualifiers, not
# just ABSTRACT. Tolerating only ABSTRACT made `FUNCTION_BLOCK INTERNAL FB_X
# EXTENDS FB_Y` parse as name="INTERNAL" with no base, so the object was
# registered under the wrong name and every inheritance-keyed rule (D1/H1/A1/S1)
# silently skipped it — a rule that does not apply is indistinguishable from a
# rule that passes.
FB_QUALIFIER = r"(?:ABSTRACT|FINAL|INTERNAL|PUBLIC|PRIVATE|PROTECTED)"
POU_DECL = re.compile(
    r"FUNCTION_BLOCK\s+((?:" + FB_QUALIFIER + r"\s+)*)([A-Za-z_]\w*)"
    r"(?:\s+EXTENDS\s+([A-Za-z_]\w*))?", re.I)
OUTER_IMPL = re.compile(
    r"</Declaration>\s*<Implementation>\s*<ST><!\[CDATA\[(.*?)\]\]></ST>"
    r"\s*</Implementation>", re.S | re.I)
METHOD_IMPL = re.compile(r"<Implementation>.*?<!\[CDATA\[(.*?)\]\]>.*?</Implementation>",
                         re.S | re.I)
CASE_BLOCK = re.compile(r"\bCASE\b.*?\bEND_CASE\b", re.S | re.I)
ENUM_BLOCK = re.compile(
    r"\bTYPE\s+[A-Za-z_]\w*\s*:\s*\((.*?)\)\s*[A-Za-z_]\w*\s*;",
    re.S | re.I)
TYPE_STRUCT = re.compile(r"\bTYPE\s+([A-Za-z_]\w*)\s*:\s*STRUCT(.*?)END_STRUCT",
                         re.S | re.I)
CONST_DINT = re.compile(
    r"^\s*([A-Z][A-Z0-9_]*)\s*:\s*DINT\s*:=\s*(\d+)", re.M)

MODULE_BASES = {"FB_ControlModuleBase", "FB_EquipmentModuleBase", "FB_UnitBase"}
LIFECYCLE_HOOKS = {
    "OnInit", "OnCyclic", "OnCommandStart", "OnModeChanged", "OnAbort",
    "OnAbortInError", "OnManRelease", "OnChainAbort", "OnChainError",
    "OnChainStart", "OnChainDone",
}

# PLC enum -> (Dart file, Dart enum). Names normalize across snake/camel case;
# MED is the one intentional vocabulary alias for Dart's `medium`.
ENUM_BINDINGS = {
    "E_ExecState": ("types.dart", "ExecState"),
    "E_ModuleType": ("types.dart", "ModuleType"),
    "E_Severity": ("types.dart", "Severity"),
    "E_Category": ("types.dart", "AlarmCategory"),
    "E_ResetClass": ("types.dart", "ResetClass"),
    "E_AlarmState": ("types.dart", "AlarmState"),
    "E_HostEventKind": ("types.dart", "HostEventKind"),
    "E_AccessLevel": ("types.dart", "AccessLevel"),
    "E_GatedAction": ("types.dart", "GatedAction"),
    "E_Mode": ("types.dart", "UnitMode"),
    "E_RunStyle": ("types.dart", "RunStyle"),
    "E_ModeSwitchShield": ("types.dart", "ModeSwitchShield"),
    "E_ModeSwitchStyle": ("types.dart", "ModeSwitchStyle"),
    "E_ConfigKind": ("types.dart", "CfgKind"),
    "E_ConfigValueType": ("types.dart", "CfgType"),
    "E_SafetyDeviceKind": ("types.dart", "SafetyDeviceKind"),
    "E_SafetyState": ("types.dart", "SafetyState"),
    "E_PowerState": ("types.dart", "PowerState"),
    "E_PowerGroupKind": ("types.dart", "PowerGroupKind"),
    "E_FieldbusLossReaction": ("types.dart", "FieldbusLossReaction"),
    "E_Verdict": ("types.dart", "Verdict"),
    "E_PackMLState": ("types.dart", "PackMLState"),
    "E_TimeClass": ("types.dart", "TimeClass"),
    "E_MachineState": ("types.dart", "MachineState"),
    "E_ReleaseKind": ("types.dart", "ReleaseKind"),
    "E_HmiRequestKind": ("../data/opcua_repository.dart", "_HmiRequestKind"),
    "E_NodeState": ("fieldbus.dart", "NodeState"),
    "E_ChannelDir": ("fieldbus.dart", "ChannelDir"),
    "E_ChannelKind": ("fieldbus.dart", "ChannelKind"),
}

PREFIX_BY_TAG = {
    "pou": ("FB_", "F_", "PRG_", "MAIN"),
    "dut": ("E_", "ST_", "T_", "U_"),
    "gvl": ("GVL_", "PL_"),
    "itf": ("I_",),
}

# Reserved in IEC 61131-3 / TwinCAT. Using one as an identifier desyncs the
# parser; the reported errors then point at unrelated lines.
RESERVED = {
    "action", "and", "array", "at", "by", "case", "class", "constant", "do", "dt",
    "else", "elsif", "end_case", "end_for", "end_if", "end_repeat",
    "end_struct", "end_type", "end_var", "end_while", "exit", "false", "for",
    "function", "if", "log", "max", "min", "mod", "not", "of", "or", "r",
    "repeat", "return", "s", "st", "step", "struct", "then", "time", "to",
    "true", "type", "until", "var", "while", "xor",
}


# IEC 61131-3 standard functions and operators. Reserved for VARIABLE
# identifiers only: a qualified enum member does not collide with them
# (E_CylinderPosition.MID compiles), but `Sub : REFERENCE TO ...` parses as
# the subtraction operator and cascades ~40 syntax errors onto innocent
# lines. The keyword list above had been inconsistent - MOD/MAX/MIN were
# present while ADD/SUB/DIV were not.
RESERVED_FUNCTIONS = {
    "abs", "acos", "add", "adr", "asin", "atan", "bitadr", "concat", "cos",
    "delete", "div", "eq", "exp", "expt", "find", "ge", "gt", "indexof",
    "insert", "le", "left", "len", "limit", "ln", "lt", "mid", "move", "mul",
    "mux", "ne", "replace", "right", "rol", "ror", "sel", "shl", "shr",
    "sin", "sizeof", "sqrt", "sub", "tan", "trunc",
}


class Finding:
    __slots__ = ("path", "line", "rule", "message")

    def __init__(self, path: Path, line: int, rule: str, message: str) -> None:
        self.path, self.line, self.rule, self.message = path, line, rule, message

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.message}"


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _strip_comment(line: str) -> str:
    return line.split("//", 1)[0]


def lint_file(path: Path, legacy_4024: bool = False) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:  # unreadable file is a real failure, not a skip
        return [Finding(path, 0, "IO", f"cannot read: {error}")]

    findings: list[Finding] = []
    stem = path.stem

    # N1/N2 — declared object name matches the filename and carries a prefix.
    for match in OBJECT_TAG.finditer(text):
        tag, name = match.group(1).lower(), match.group(2)
        line = _line_of(text, match.start())
        if name != stem:
            findings.append(Finding(
                path, line, "N1",
                f"<{tag} Name=\"{name}\"> does not match filename '{stem}'"))
        allowed = PREFIX_BY_TAG.get(tag, ())
        if allowed and not name.startswith(allowed):
            findings.append(Finding(
                path, line, "N2",
                f"'{name}' lacks a §4.4 prefix (expected one of "
                f"{', '.join(allowed)})"))

    # C1 — defaulted METHOD inputs are 4026+; they must be pragma-guarded so the
    # legacy 4024 profile still has a compilable declaration.
    for method in METHOD_BLOCK.finditer(text):
        method_name, body = method.group(1), method.group(2)
        var_input = VAR_INPUT_BLOCK.search(body)
        if not var_input:
            continue
        base = _line_of(text, method.start(2) + var_input.start(1))
        block = var_input.group(1)
        # Track which conditional-pragma branch each line sits in. A default is
        # acceptable only in a branch that is compiled OUT when the legacy define
        # is set, i.e. the {ELSE} of `{IF defined (FRAKTAL_TC3_4024)}`.
        legacy_guarded = False
        in_legacy_if = False
        for offset, raw in enumerate(block.splitlines()):
            stripped = raw.strip()
            if COMPAT_IF.match(stripped):
                in_legacy_if, legacy_guarded = True, False
                continue
            if in_legacy_if and PRAGMA_ELSE.match(stripped):
                legacy_guarded = True
                continue
            if PRAGMA_END.match(stripped):
                in_legacy_if, legacy_guarded = False, False
                continue
            hit = DECL_WITH_DEFAULT.match(_strip_comment(raw))
            if not hit:
                continue
            if legacy_guarded:
                # Inside the {ELSE} of the legacy guard: the 4024 compiler never
                # sees this line, so it is correct for BOTH profiles.
                continue
            if legacy_4024:
                findings.append(Finding(
                    path, base + offset, "C1",
                    f"METHOD {method_name}: input '{hit.group(1)}' has an "
                    "unguarded default; the --profile 4024 build would compile a "
                    "4026-only construct (wrap it in "
                    "'{IF defined (FRAKTAL_TC3_4024)}' / '{ELSE}')"))
            else:
                findings.append(Finding(
                    path, base + offset, "C1",
                    f"METHOD {method_name}: input '{hit.group(1)}' has a default "
                    "but is not inside the {ELSE} of "
                    "'{IF defined (FRAKTAL_TC3_4024)}'; defaulted method inputs "
                    "require TwinCAT >= 3.1.4026, so the legacy branch must "
                    "declare it without a default "
                    "(see Params/PL_FraktalCompat.TcGVL)"))

    # C2 — reserved words as identifiers.
    for offset, raw in enumerate(text.splitlines(), start=1):
        code = _strip_comment(raw)
        hit = DECL_ANY.match(code)
        if hit and hit.group(1).lower() in (RESERVED | RESERVED_FUNCTIONS):
            findings.append(Finding(
                path, offset, "C2",
                f"'{hit.group(1)}' is a reserved word; as an identifier it "
                "desyncs the parser and cascades misleading errors"))
    code = _without_comments(text)
    for enum_block in ENUM_BLOCK.finditer(code):
        for member in re.finditer(r"\b([A-Za-z_]\w*)\s*:=", enum_block.group(1)):
            if member.group(1).lower() not in RESERVED:
                continue
            findings.append(Finding(
                path, _line_of(code, enum_block.start(1) + member.start()), "C2",
                f"'{member.group(1)}' is a reserved word; as an enumeration "
                "member it desyncs the parser and cascades misleading errors"))

    # C3 — balanced Method tags.
    opens = len(re.findall(r"<Method\s+Name=", text, re.I))
    closes = len(re.findall(r"</Method>", text, re.I))
    if opens != closes:
        findings.append(Finding(
            path, 1, "C3",
            f"unbalanced <Method> tags: {opens} open vs {closes} close"))

    # C4 — duplicate GUIDs within the file.
    seen: dict[str, int] = {}
    for match in GUID_ATTR.finditer(text):
        guid = match.group(1).lower()
        line = _line_of(text, match.start())
        if guid in seen:
            findings.append(Finding(
                path, line, "C4",
                f"duplicate Id {match.group(1)} (first seen line {seen[guid]})"))
        else:
            seen[guid] = line

    return findings


def _skipped(path: Path) -> bool:
    return any(part in SKIP_PARTS or part.startswith("_CompileInfo")
               for part in path.parts)


def _without_comments(text: str) -> str:
    text = re.sub(r"\(\*.*?\*\)", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _first_declaration(text: str) -> str:
    hit = re.search(r"<Declaration><!\[CDATA\[(.*?)\]\]></Declaration>",
                    text, re.S | re.I)
    return hit.group(1) if hit else ""


def _has_default_then_guard(code: str, block: re.Match[str]) -> bool:
    """A CASE that is fail-safe by construction rather than by an ELSE branch.

    The pattern the standard actually requires (§5.6) is a *defined safe
    reaction*, not empty `ELSE` boilerplate. The idiomatic form is:

        target := -1;                 // safe default BEFORE the CASE
        CASE _retVal OF ... END_CASE  // branches only ever raise it
        IF target >= 0 THEN ...       // guard AFTER: unmatched input does nothing

    An unmatched selector then falls through to the default and the guard
    rejects it — strictly safer than an `ELSE` that must be written correctly.
    Recognised only when BOTH halves are present: a variable assigned a literal
    immediately before the CASE, and that same variable tested in an `IF`
    immediately after. A CASE with neither is still reported.
    """
    before = code[:block.start()]
    after = code[block.end():]
    # Last assignment before the CASE, e.g. `target := -1;`
    default = None
    for match in re.finditer(r"(\w+)\s*:=\s*[^;]+;", before):
        default = match
    if default is None:
        return False
    variable = default.group(1)
    # The default must be adjacent to the CASE, not anywhere earlier in the POU.
    if _without_comments(before[default.end():]).strip():
        return False
    # ...and every branch must write that same variable, so the default is the
    # value an unmatched selector actually keeps.
    branches = re.findall(rf"\b{re.escape(variable)}\s*:=", block.group(0))
    if not branches:
        return False
    # A guard on that variable must follow the CASE.
    guard = re.match(r"\s*IF\b[^;]*?\b" + re.escape(variable) + r"\b",
                     after, re.I | re.S)
    return guard is not None


def _shipping(path: Path) -> bool:
    parts = set(path.parts)
    if "scaffold" in parts or "Fraktal_Tests" in parts:
        return False
    return "Framework" in parts or "Fraktal_Press_Demo" in parts


def _normalize_enum_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _parse_plc_enum(text: str, enum_name: str) -> list[tuple[str, int]] | None:
    hit = re.search(
        rf"\bTYPE\s+{re.escape(enum_name)}\s*:\s*\((.*?)\)\s*DINT\s*;",
        _without_comments(text), re.S | re.I)
    if not hit:
        return None
    rows: list[tuple[str, int]] = []
    for item in hit.group(1).split(","):
        parsed = re.match(r"\s*([A-Za-z_]\w*)\s*:=\s*(-?\d+)\s*$", item)
        if not parsed:
            return None
        rows.append((parsed.group(1), int(parsed.group(2))))
    return rows


def _parse_dart_enum(text: str, enum_name: str) -> list[str] | None:
    hit = re.search(rf"\benum\s+{re.escape(enum_name)}\s*\{{(.*?)\}}",
                    _without_comments(text), re.S)
    if not hit:
        return None
    names: list[str] = []
    for item in hit.group(1).split(","):
        parsed = re.match(r"\s*([A-Za-z_]\w*)", item)
        if parsed:
            names.append(parsed.group(1))
    return names


def _resolve_compile(project: Path, include: str, boundary: Path) -> Path | None:
    relative = Path(include.replace("\\", "/"))
    for base in (project.parent, *project.parents):
        try:
            base.relative_to(boundary)
        except ValueError:
            continue
        candidate = base / relative
        if candidate.is_file():
            return candidate.resolve()
    return None


def lint_repository(roots: list[Path]) -> list[Finding]:
    """Cross-file conformance checks. Kept separate for deterministic fixtures."""
    source_paths = sorted({path for path in iter_sources(roots)})
    texts: dict[Path, str] = {}
    findings: list[Finding] = []
    for path in source_paths:
        try:
            texts[path] = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            findings.append(Finding(path, 0, "IO", f"cannot read: {error}"))

    inheritance: dict[str, str] = {}
    declarations: dict[str, tuple[Path, str, bool]] = {}
    for path, text in texts.items():
        declaration = _first_declaration(text)
        match = POU_DECL.search(declaration)
        if not match:
            continue
        qualifiers = (match.group(1) or "").upper().split()
        abstract, name, base = "ABSTRACT" in qualifiers, match.group(2), match.group(3)
        declarations[name] = (path, declaration, abstract)
        if base:
            inheritance[name] = base

    def derives(name: str, target: str) -> bool:
        seen: set[str] = set()
        while name and name not in seen:
            if name == target:
                return True
            seen.add(name)
            name = inheritance.get(name, "")
        return False

    # D1 + H1: physical contract and inheritance-owned lifecycle/body.
    for name, (path, declaration, abstract) in declarations.items():
        base = inheritance.get(name, "")
        text = texts[path]
        if (_shipping(path) and not abstract
                and any(derives(name, module_base) for module_base in MODULE_BASES)):
            # The four-structure contract may be declared on this type OR on any
            # ancestor: §2.2 writes behaviour once at the owning level and
            # inherits it, so a device variant that only overrides _M_Dispatch
            # (e.g. FB_Iv3VisionCM EXTENDS FB_TcpVisionCM) legitimately declares
            # none of the four itself. Walking the chain is what makes this rule
            # agree with the framework instead of forbidding inheritance.
            # Collect this type's declaration plus every ANCESTOR declaration we
            # can see. The tier bases (FB_ControlModuleBase etc.) deliberately do
            # not declare the four — a concrete type must obtain them somewhere
            # in its own chain — so an unresolvable ancestor is simply skipped
            # rather than treated as proof either way.
            inherited_decls = [declaration]
            ancestor = base
            seen_bases: set[str] = set()
            while (ancestor and ancestor not in seen_bases
                   and ancestor not in MODULE_BASES):
                seen_bases.add(ancestor)
                ancestor_entry = declarations.get(ancestor)
                if ancestor_entry is None:
                    break
                inherited_decls.append(ancestor_entry[1])
                ancestor = inheritance.get(ancestor, "")
            missing = [field for field in ("ParCfg", "ParCmd", "OutCmd", "OutImm")
                       if not any(re.search(rf"\b{field}\b", decl)
                                  for decl in inherited_decls)]
            if missing:
                findings.append(Finding(
                    path, 1, "D1",
                    f"shipping module {name} lacks physical contract member(s): "
                    f"{', '.join(missing)}"))
            outer = OUTER_IMPL.search(text)
            body = _without_comments(outer.group(1) if outer else "")
            normalized = re.sub(r"\s+", "", body)
            if normalized != "Cyclic();":
                findings.append(Finding(
                    path, 1, "H1",
                    f"concrete module {name} body must be exactly inherited Cyclic();"))

        if base:
            for method in METHOD_BLOCK.finditer(text):
                method_name = method.group(1)
                if method_name not in LIFECYCLE_HOOKS:
                    continue
                # The tier base owns a few hooks (notably OnModeChanged) that do
                # not exist on its parent.  Those are definitions, not overrides;
                # SUPER is mandatory only when an ancestor actually declares the
                # same hook.  This also makes the rule correct for future
                # intermediate abstract bases.
                ancestor = base
                inherited_hook = False
                seen: set[str] = set()
                while ancestor and ancestor not in seen:
                    seen.add(ancestor)
                    ancestor_decl = declarations.get(ancestor)
                    if ancestor_decl and re.search(
                            rf'<Method\s+Name="{re.escape(method_name)}"',
                            texts[ancestor_decl[0]], re.I):
                        inherited_hook = True
                        break
                    ancestor = inheritance.get(ancestor, "")
                if not inherited_hook:
                    continue
                implementation = METHOD_IMPL.search(method.group(2))
                code = _without_comments(implementation.group(1) if implementation else "")
                statements = [part.strip() for part in code.split(";") if part.strip()]
                if not statements or f"SUPER^.{method_name}" not in statements[0]:
                    findings.append(Finding(
                        path, _line_of(text, method.start()), "H1",
                        f"{name}.{method_name} must call SUPER^.{method_name} first"))

    for path, text in texts.items():
        for type_name, body in TYPE_STRUCT.findall(text):
            if not type_name.lower().endswith("parcfg"):
                continue
            code = _without_comments(body).strip()
            first = re.match(r"([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)", code)
            if not first or first.group(1) != "SchemaVersion" or first.group(2).upper() != "UINT":
                findings.append(Finding(
                    path, 1, "D1",
                    f"{type_name} must start with SchemaVersion : UINT"))

    # C5: CASE must own an explicit safe default. IF guard-return patterns are
    # intentionally not policed; the standard requires semantics, not empty ELSE.
    for path, text in texts.items():
        if not _shipping(path):
            continue
        code = _without_comments(text)
        for block in CASE_BLOCK.finditer(code):
            if re.search(r"\bELSE\b", block.group(0), re.I):
                continue
            if _has_default_then_guard(code, block):
                continue
            findings.append(Finding(
                path, _line_of(code, block.start()), "C5",
                "CASE has no ELSE fail-safe reaction"))

    # C6: IEC/TwinCAT CASE selectors and labels are ordinal. A quoted label is
    # a reliable source-level indication that a STRING was incorrectly used as
    # the selector; use IF/ELSIF for string comparisons.
    for path, text in texts.items():
        if not _shipping(path):
            continue
        code = _without_comments(text)
        for block in CASE_BLOCK.finditer(code):
            if not re.search(r"(?m)^\s*'[^'\r\n]*'\s*:", block.group(0)):
                continue
            findings.append(Finding(
                path, _line_of(code, block.start()), "C6",
                "CASE has a string-literal label; use IF/ELSIF for STRING values"))

    # C7: a guard must not rely on short-circuit evaluation. IEC 61131-3 does
    # not mandate it and TwinCAT's compile option for it is off by default, so
    # in `IF (p = 0) OR (p^.x <> y)` or `IF (i > 0) AND (arr[i] = z)` the second
    # operand is evaluated anyway: a null dereference, or index 0 of a 1-based
    # ARRAY. Both are ordinary not-found paths, so this faults in the field
    # rather than in test. Split the sentinel test into its own statement.
    for path, text in texts.items():
        if not _shipping(path):
            continue
        code = _without_comments(text)
        one_based = {
            match.group(1)
            for match in re.finditer(
                r"(\w+)\s*:\s*ARRAY\s*\[\s*1\s*\.\.", code, re.I)
        }
        for statement in re.finditer(r"\bIF\b(.+?)\bTHEN\b", code, re.S):
            condition = " ".join(statement.group(1).split())
            if len(condition) > 400:
                continue
            for guard in re.finditer(r"\b(\w+)\s*(?:=|<>|>|<=)\s*0\b", condition):
                symbol = guard.group(1)
                unsafe = re.search(
                    r"\b" + re.escape(symbol) + r"\s*(?:\^|\.\w+\s*\()", condition)
                indexed = [
                    array for array in re.findall(
                        r"\b(\w+)\s*\[\s*" + re.escape(symbol) + r"\s*\]", condition)
                    if array in one_based
                ]
                if not unsafe and not indexed:
                    continue
                detail = (f"dereferences {symbol}" if unsafe
                          else f"indexes 1-based {indexed[0]}[{symbol}]")
                findings.append(Finding(
                    path, _line_of(code, statement.start()), "C7",
                    f"guard {detail} in the same condition that tests it against 0; "
                    "TwinCAT does not short-circuit — split into separate statements"))
                break

    # S1: the shipped ST sequence skeleton is deliberately small and testable.
    for name, (path, declaration, is_abstract) in declarations.items():
        # Follow the chain: FB_SequenceBaseLd sits between the ladder chains and
        # FB_SequenceBase, and a direct-equality test skipped every POU behind it.
        # An ABSTRACT base is scaffolding, not a chain, so it carries no steps.
        if is_abstract or not derives(name, "FB_SequenceBase") or name == "FB_SequenceBase":
            continue
        if not _shipping(path):
            continue
        text = texts[path]
        # A chart-language body (SFC/LD/FBD) is not the ST skeleton: its runtime
        # owns the transition, so `CASE _step OF` and M_Advance are the wrong
        # things to demand. It still has to honour the §6.10 contract — carry the
        # shared result and record its steps — and it must clear the result once
        # per scan, which only M_BeginScan or a M_ClearTransition exit action does.
        # TwinCAT writes a Ladder body as <LADDER>, not <LD>. Missing that one
        # spelling made S1 demand the ST skeleton of every ladder chain — the
        # rule applied, but to the wrong contract.
        if re.search(r"<SFC\b|<NWL\b|<LADDER\b|<LD\b|<FBD\b|<CFC\b", text, re.I):
            # The per-scan clear (§6.8) is the OWNER's obligation - it calls
            # M_BeginScan() before executing the chart - or a step exit action
            # wired in the chart editor. Neither is visible in this file, so the
            # linter checks only what a chart object can prove about itself:
            # it carries the shared result and records its steps.
            #
            # LADDER is the integer-state-machine form: its rungs dispatch on
            # _step but do not evaluate transitions, so unlike SFC its actions
            # still commit their own result through M_Advance.
            # In a network list a call is a BoxType string ("M_Step"), never the
            # ST call syntax, so match the names rather than "M_Step(".
            required = ["_retVal", "M_Step"]
            if re.search(r"<NWL\b|<LADDER\b", text, re.I):
                required.append("M_Advance")
            missing = [token for token in required
                       if not re.search(r"\b" + token + r"\b", text)]
            if missing:
                findings.append(Finding(
                    path, 1, "S1",
                    f"chart sequence {name} lacks chart-contract token(s): "
                    f"{', '.join(missing)}"))
            continue
        required = ("_step", "_retVal", "CASE _step OF", "M_Step(", "M_Advance(")
        missing = [token for token in required if token not in text]
        if missing:
            findings.append(Finding(
                path, 1, "S1",
                f"sequence {name} lacks skeleton token(s): {', '.join(missing)}"))
        case = re.search(r"\bCASE\s+_step\s+OF(.*?)\bEND_CASE\b", text, re.S | re.I)
        if case:
            body = case.group(1)
            # Split into per-step branches so a TERMINAL step can be excused.
            # A terminal step must NOT advance — it ends the chain via
            # M_Complete() (finite chains) or Done := TRUE (sub-sequences).
            # Requiring M_Advance there would demand the opposite of §6.8.
            starts = [m.start() for m in re.finditer(r"(?m)^\s*-?\d+\s*:", body)]
            advancing_required = 0
            advances_found = 0
            for index, start in enumerate(starts):
                end = starts[index + 1] if index + 1 < len(starts) else len(body)
                branch = body[start:end]
                terminal = ("M_Complete(" in branch
                            or re.search(r"\bDone\s*:=\s*TRUE", branch, re.I))
                if terminal:
                    continue
                advancing_required += 1
                if re.search(r"\bM_Advance\s*\(", branch):
                    advances_found += 1
            if advances_found < advancing_required:
                findings.append(Finding(
                    path, _line_of(text, case.start()), "S1",
                    f"sequence {name} has {advancing_required} non-terminal step "
                    f"branches but only {advances_found} M_Advance calls"))

    # A1: direct or derived Unit types cannot be members of an EM declaration.
    unit_types = {name for name in declarations if derives(name, "FB_UnitBase")}
    for name, (path, declaration, _) in declarations.items():
        if not derives(name, "FB_EquipmentModuleBase"):
            continue
        for member_type in re.findall(r":\s*(FB_[A-Za-z_]\w*)", declaration):
            if member_type in unit_types:
                findings.append(Finding(
                    path, 1, "A1",
                    f"EquipmentModule {name} contains Unit type {member_type}"))

    # R1: the type-owned reason registry is one collision domain.
    reasons: dict[int, tuple[Path, str]] = {}
    for path, text in texts.items():
        if not path.stem.startswith("PL_") or "Reasons" not in path.stem:
            continue
        for match in CONST_DINT.finditer(_without_comments(text)):
            reason_name, value = match.group(1), int(match.group(2))
            if value < 10000:
                findings.append(Finding(
                    path, _line_of(text, match.start()), "R1",
                    f"type reason {reason_name}={value} is below 10000"))
            prior = reasons.get(value)
            if prior:
                findings.append(Finding(
                    path, _line_of(text, match.start()), "R1",
                    f"reason {value} collides with {prior[1]} in {prior[0]}"))
            else:
                reasons[value] = (path, reason_name)

    # E1: compare every transport enum the HMI mirrors.
    workspace = Path.cwd()
    dart_root = workspace / "FraktalCore/HMI/lib/domain"
    by_stem = {path.stem: path for path in source_paths}
    for plc_name, (dart_file, dart_name) in ENUM_BINDINGS.items():
        plc_path = by_stem.get(plc_name)
        dart_path = dart_root / dart_file
        if plc_path is None or not dart_path.is_file():
            continue  # partial fixture/root; full repository supplies both sides
        plc_rows = _parse_plc_enum(texts[plc_path], plc_name)
        dart_rows = _parse_dart_enum(
            dart_path.read_text(encoding="utf-8", errors="replace"), dart_name)
        if plc_rows is None or dart_rows is None:
            findings.append(Finding(
                plc_path, 1, "E1", f"cannot parse {plc_name}/{dart_name} enum"))
            continue
        plc_ordinals = [value for _, value in plc_rows]
        if plc_ordinals != list(range(len(plc_rows))):
            findings.append(Finding(
                plc_path, 1, "E1", f"{plc_name} ordinals are not contiguous from 0"))
        plc_names = [_normalize_enum_name(name) for name, _ in plc_rows]
        plc_names = ["medium" if plc_name == "E_Severity" and name == "med" else name
                     for name in plc_names]
        plc_names = ["time" if plc_name == "E_ConfigValueType" and name == "duration"
                     else name for name in plc_names]
        dart_names = [_normalize_enum_name(name) for name in dart_rows]
        if plc_names != dart_names:
            findings.append(Finding(
                plc_path, 1, "E1",
                f"{plc_name} != Dart {dart_name}: {plc_names} vs {dart_names}"))

    # P1: project includes are resolvable/complete, then deployment markers are
    # checked for the two shipping application fixtures (never the test runtime).
    for root in roots:
        if not root.exists():
            continue
        boundary = root.resolve()
        projects = sorted(root.rglob("*.plcproj"))
        for project in projects:
            if _skipped(project):
                continue
            project_text = project.read_text(encoding="utf-8", errors="replace")
            includes = re.findall(r'<Compile\s+Include="([^"]+)"', project_text, re.I)
            resolved: set[Path] = set()
            for include in includes:
                if ".." in Path(include.replace("\\", "/")).parts:
                    findings.append(Finding(
                        project, 1, "P1",
                        f"Compile Include contains TwinCAT-invalid '..' segment: {include}"))
                source = _resolve_compile(project.resolve(), include, boundary)
                if source is None:
                    findings.append(Finding(
                        project, 1, "P1", f"Compile Include does not resolve: {include}"))
                else:
                    resolved.add(source)
            # A TwinCAT aggregate may keep its manifest at the nearest common
            # ancestor because PLC Control rejects raw '..' Include segments.
            # Its authored ownership root is then the same-named source
            # directory, which need not sit directly beside the manifest -
            # Fraktal_Tests.plcproj lives at TwinCAT/ but owns
            # TwinCAT/Tests/Fraktal_Tests/. Locate it rather than assume a
            # depth, so a folder re-layout does not silently turn every sibling
            # source into a violation. Sibling application sources may still be
            # explicit linked inputs, but are checked for completeness by their
            # own manifests.
            candidates = sorted(
                (path for path in project.parent.rglob(project.stem)
                 if path.is_dir() and not _skipped(path)),
                key=lambda path: len(path.relative_to(project.parent).parts))
            if candidates:
                owned_root = candidates[0]
            elif (project.parent / project.stem).is_dir():
                owned_root = project.parent / project.stem
            else:
                owned_root = project.parent
            owned = {
                path.resolve() for path in owned_root.rglob("*")
                if path.is_file() and path.suffix in {".TcPOU", ".TcDUT", ".TcGVL", ".TcIO", ".TcTTO"}
                and not _skipped(path)
            }
            missing = sorted(owned - resolved)
            for source in missing:
                findings.append(Finding(
                    project, 1, "P1",
                    f"authored source is absent from project compile list: {source}"))

            if project.stem not in {"Fraktal_Demo", "Fraktal_Press_Demo"}:
                continue
            for source in resolved:
                if source.suffix != ".TcPOU":
                    continue
                source_text = source.read_text(encoding="utf-8", errors="replace")
                if not re.search(r"\bPROGRAM\s+MAIN\b", source_text, re.I):
                    continue
                declaration = _first_declaration(source_text)
                for match in re.finditer(r"(?m)^\s*([A-Za-z_]\w*)\s*:\s*(FB_[A-Za-z_]\w*)\s*;",
                                         declaration):
                    variable, type_name = match.group(1), match.group(2)
                    if not derives(type_name, "FB_UnitBase"):
                        continue
                    prefix = declaration[max(0, match.start() - 160):match.start()]
                    if not re.search(r"\{attribute\s+'OPC\.UA\.DA'\s*:=\s*'1'\}\s*$",
                                     prefix, re.I):
                        findings.append(Finding(
                            source, _line_of(declaration, match.start()), "P1",
                            f"deployed root {variable} : {type_name} lacks immediate "
                            "OPC.UA.DA := '1' marker"))

        # TwinCAT identifies every PLC object and child method by the GUID in
        # its source XML. Loading one physical source through two PLC projects
        # in the same XAE system project makes PLC Control rewrite those GUIDs
        # repeatedly. Aggregate tests that link application fixtures therefore
        # belong in a separate XAE solution/runtime from the deployed fixture.
        for system_project in sorted(root.rglob("*.tsproj")):
            if _skipped(system_project):
                continue
            system_text = system_project.read_text(
                encoding="utf-8", errors="replace")
            references = re.findall(
                r'PrjFilePath="([^"]+\.plcproj)"', system_text, re.I)
            loaded: list[tuple[Path, set[Path]]] = []
            for reference in references:
                manifest = (system_project.parent /
                            Path(reference.replace("\\", "/"))).resolve()
                if not manifest.is_file():
                    findings.append(Finding(
                        system_project, 1, "P1",
                        f"XAE PLC project reference does not resolve: {reference}"))
                    continue
                manifest_text = manifest.read_text(
                    encoding="utf-8", errors="replace")
                manifest_sources: set[Path] = set()
                for include in re.findall(
                        r'<Compile\s+Include="([^"]+)"', manifest_text, re.I):
                    source = _resolve_compile(manifest, include, boundary)
                    if source is not None:
                        manifest_sources.add(source)
                loaded.append((manifest, manifest_sources))
            for index, (left, left_sources) in enumerate(loaded):
                for right, right_sources in loaded[index + 1:]:
                    overlap = sorted(left_sources & right_sources)
                    if overlap:
                        findings.append(Finding(
                            system_project, 1, "P1",
                            f"XAE loads {len(overlap)} source object(s) through both "
                            f"{left.name} and {right.name}; first duplicate: "
                            f"{overlap[0]}"))

    return findings


def iter_sources(roots: list[Path]):
    patterns = ("*.TcPOU", "*.TcDUT", "*.TcGVL", "*.TcIO")
    for root in roots:
        if not root.exists():
            print(f"plc_lint: no such path: {root}", file=sys.stderr)
            continue
        for pattern in patterns:
            for path in sorted(root.rglob(pattern)):
                if not _skipped(path):
                    yield path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Lint Fraktal TwinCAT sources (Core §1.5/§5.5/§6.8).")
    parser.add_argument("roots", nargs="*", type=Path, default=None,
                        help="paths to scan (default: FraktalCore/PLC/TwinCAT)")
    parser.add_argument("--quiet", action="store_true",
                        help="print only violations")
    parser.add_argument("--profile", choices=["modern", "4024"],
                        default="modern",
                        help="build profile to verify (default: modern). '4024' rejects any 4026-only construct, guarded or not.")
    args = parser.parse_args(argv)

    roots = args.roots or DEFAULT_ROOTS
    legacy = args.profile == "4024"
    findings: list[Finding] = []
    scanned = 0
    for path in iter_sources(list(roots)):
        scanned += 1
        findings.extend(lint_file(path, legacy_4024=legacy))

    findings.extend(lint_repository(list(roots)))

    if not scanned:
        print("plc_lint: no PLC sources found — check the path.", file=sys.stderr)
        return 2

    for finding in findings:
        print(finding)

    if findings:
        rules = ", ".join(sorted({f.rule for f in findings}))
        print(f"\nplc_lint: {len(findings)} violation(s) in {scanned} file(s) "
              f"[{rules}]")
        return 1
    if not args.quiet:
        print(f"plc_lint: {scanned} file(s) clean "
              f"(profile: {args.profile}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

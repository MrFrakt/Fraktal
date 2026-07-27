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
  C2  No IEC/TwinCAT reserved word as a variable identifier. These do not error
        where they are declared — they desync the parser and produce a cascade of
        misleading errors elsewhere in the file.
  C3  Balanced <Method> open/close tags (guards hand-edited .TcPOU XML).
  C4  Unique GUIDs within a file (a duplicated Id silently shadows an object).

Usage
  python tools/plc_lint.py [root ...]        # default: FraktalCore/PLC
  python tools/plc_lint.py --quiet           # only failures
  python tools/plc_lint.py --profile 4024    # legacy build: no 4026-only feature
Exit status: 0 clean, 1 violations found, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_ROOTS = [Path("FraktalCore/PLC")]

# Generated/vendored trees that are not authored source.
SKIP_PARTS = {"_CompileInfo", "_Boot", "_ScopeConfig", "third_party", ".git"}

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

PREFIX_BY_TAG = {
    "pou": ("FB_", "F_", "PRG_", "MAIN"),
    "dut": ("E_", "ST_", "T_", "U_"),
    "gvl": ("GVL_", "PL_"),
    "itf": ("I_",),
}

# Reserved in IEC 61131-3 / TwinCAT. Using one as an identifier desyncs the
# parser; the reported errors then point at unrelated lines.
RESERVED = {
    "action", "and", "array", "at", "by", "case", "constant", "do", "dt",
    "else", "elsif", "end_case", "end_for", "end_if", "end_repeat",
    "end_struct", "end_type", "end_var", "end_while", "exit", "false", "for",
    "function", "if", "log", "max", "min", "mod", "not", "of", "or", "r",
    "repeat", "return", "s", "st", "step", "struct", "then", "time", "to",
    "true", "type", "until", "var", "while", "xor",
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
        if hit and hit.group(1).lower() in RESERVED:
            findings.append(Finding(
                path, offset, "C2",
                f"'{hit.group(1)}' is a reserved word; as an identifier it "
                "desyncs the parser and cascades misleading errors"))

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


def iter_sources(roots: list[Path]):
    patterns = ("*.TcPOU", "*.TcDUT", "*.TcGVL", "*.TcIO")
    for root in roots:
        if not root.exists():
            print(f"plc_lint: no such path: {root}", file=sys.stderr)
            continue
        for pattern in patterns:
            for path in sorted(root.rglob(pattern)):
                if SKIP_PARTS.isdisjoint(path.parts):
                    yield path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Lint Fraktal TwinCAT sources (Core §1.5/§5.5/§6.8).")
    parser.add_argument("roots", nargs="*", type=Path, default=None,
                        help="paths to scan (default: FraktalCore/PLC)")
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

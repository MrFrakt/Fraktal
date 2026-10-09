"""Fraktal/TIA structural gate (Part IV §5.3) over SCL external sources, without
TIA. One rule id per invariant; a violation prints `path:line: RULE message` and
the exit code is the number of violations (capped at 1 for shells that want 0/1
use --exit-one).

    python tia_lint.py [paths...]        (default: FraktalCore/PLC/Siemens/Spikes)

Rules that need the generator's declaration model (T-TIER, T-IO, T-WIDTH, T-GEN)
are reported as PENDING, never as passed.
"""

from __future__ import annotations

import pathlib
import re
import sys
from dataclasses import dataclass, field

SOURCE_SUFFIXES = {".scl", ".udt", ".db"}
ASCII_SUFFIXES = SOURCE_SUFFIXES | {".plan"}
PENDING = ("T-TIER", "T-IO", "T-WIDTH", "T-GEN")

# Header keywords of an SCL source block: an unquoted member with one of these
# names is silently dropped by STEP 7 (measured for Name, Part IV §5.3).
HEADER_KEYWORDS = {"name", "title", "author", "family", "version"}
# Names STEP 7 refuses as identifiers (types and literals prefixes; measured: dt).
RESERVED = {"dt", "tod", "date", "time", "ltime", "s5time", "ldt", "ltod", "dtl", "int", "dint", "sint",
            "lint", "uint", "udint", "usint", "ulint", "real", "lreal", "bool", "byte", "word", "dword",
            "lword", "char", "wchar", "string", "wstring", "array", "struct", "void", "and", "or", "xor",
            "not", "mod", "div", "true", "false", "if", "then", "else", "elsif", "case", "of", "for", "to",
            "by", "do", "while", "repeat", "until", "exit", "return", "continue", "goto", "begin", "region"}
# The quiescent guard of the generated frame (Part IV §3.14), normalized.
QUIET_GUARD = ("NOT (#Core.Initialized AND #Core.Exec = #EXEC_READY AND NOT #Execute AND NOT #Abort "
               "AND NOT #Core.ExecPrev AND NOT #Core.AbortPrev AND #Core.HoldReason = 0 AND NOT #Core.EvInit)")
# Members the lifecycle FCs own: authored regions never write them (T-CORE).
LIFECYCLE = {"exec", "execprev", "abortprev", "initialized", "evinit", "evcommandstart", "evabort",
             "evabortinerror", "dispatch", "held", "holdreq", "holdreason", "faultreq", "completereq",
             "regindex", "named", "moduletype", "parentindex", "startms", "lastcmdms"}
# Published contract members of a module FB (Core §3.12, Part IV §3.3) - every
# other non-FB static must carry ExternalAccessible := 'False' (T-EXT).
CONTRACT = {"status", "hmirequest", "hmiresponse", "parcfg", "parcmd", "outcmd", "outimm",
            "currentstep", "mode"}


@dataclass
class Finding:
    path: pathlib.Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return "%s:%d: %s %s" % (self.path, self.line, self.rule, self.message)


@dataclass
class Decl:
    name: str
    quoted: bool
    type_text: str
    attrs: str
    section: str
    line: int


@dataclass
class Block:
    kind: str                      # FUNCTION_BLOCK, FUNCTION, ORGANIZATION_BLOCK, DATA_BLOCK, TYPE
    name: str
    line: int                      # 1-based line of the header
    decls: list[Decl] = field(default_factory=list)
    constants: list[Decl] = field(default_factory=list)
    body: str = ""                 # code with comments/strings blanked, positions preserved
    body_line: int = 0             # 1-based line where body text starts
    raw_body: str = ""


def strip_comments(text: str) -> str:
    """Blanks comments and string literals, keeping offsets and newlines, so
    regexes see code only and line numbers survive."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        two = text[i:i + 2]
        if two == "//":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif two == "(*":
            j = text.find("*)", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j])); i = j
        elif c == "'":
            j = i + 1
            while j < n and text[j] != "'":
                j += 2 if text[j] == "$" else 1
            j = min(j + 1, n)
            out.append("'" + " " * (j - i - 2) + "'" if j - i >= 2 else " "); i = j
        else:
            out.append(c); i += 1
    return "".join(out)


HEADER_RE = re.compile(r'^(FUNCTION_BLOCK|FUNCTION|ORGANIZATION_BLOCK|DATA_BLOCK|TYPE)\s+"([^"]+)"', re.M)
END_RE = {"FUNCTION_BLOCK": "END_FUNCTION_BLOCK", "FUNCTION": "END_FUNCTION",
          "ORGANIZATION_BLOCK": "END_ORGANIZATION_BLOCK", "DATA_BLOCK": "END_DATA_BLOCK", "TYPE": "END_TYPE"}
DECL_RE = re.compile(r'^\s*("?)([A-Za-z_][A-Za-z0-9_]*)\1\s*(\{[^}]*\})?\s*:\s*([^;]+);', re.M)


def parse_blocks(text: str) -> list[Block]:
    code = strip_comments(text)
    blocks = []
    for m in HEADER_RE.finditer(code):
        kind, name = m.group(1), m.group(2)
        end = re.compile(r"^\s*%s\b" % END_RE[kind], re.M).search(code, m.end())
        stop = end.start() if end else len(code)
        segment = code[m.start():stop]
        block = Block(kind, name, code.count("\n", 0, m.start()) + 1)
        begin = re.search(r"^\s*BEGIN\b", segment, re.M)
        head = segment[:begin.start()] if begin else segment
        if begin:
            block.body = segment[begin.end():]
            block.raw_body = text[m.start() + begin.end():stop]
            block.body_line = block.line + segment.count("\n", 0, begin.end())
        section = None
        # declarations are read from the RAW text: attribute values are string
        # literals ('False'), which the code view blanks
        raw_head = text[m.start():m.start() + len(head)]
        for line_no, line in enumerate(raw_head.splitlines(), start=block.line):
            line = re.sub(r"//.*$", "", line)
            s = line.strip()
            sec = re.match(r"(VAR_INPUT|VAR_OUTPUT|VAR_IN_OUT|VAR_TEMP|VAR\s+CONSTANT|VAR\s+DB_SPECIFIC|VAR|STRUCT)\b", s)
            if sec:
                section = re.sub(r"\s+", " ", sec.group(1))
                continue
            if re.match(r"END_(VAR|STRUCT)\b", s):
                section = None
                continue
            if section is None:
                continue
            d = DECL_RE.match(line)
            if d:
                decl = Decl(d.group(2), d.group(1) == '"', d.group(4).strip(), d.group(3) or "", section, line_no)
                (block.constants if section == "VAR CONSTANT" else block.decls).append(decl)
        blocks.append(block)
    return blocks


def line_of(block: Block, offset: int) -> int:
    return block.body_line + block.body.count("\n", 0, offset)


# ---------------------------------------------------------------- the rules

def check_ascii(path: pathlib.Path, data: bytes) -> list[Finding]:
    out = []
    for no, line in enumerate(data.split(b"\n"), start=1):
        if any(b > 0x7F for b in line):
            out.append(Finding(path, no, "T-ASCII", "non-ASCII byte: TIA reads a BOM-less source as ANSI"))
            break
    return out


def check_typefile(path: pathlib.Path, text: str) -> list[Finding]:
    out = []
    count = len(re.findall(r'^\s*TYPE\s+"', text, re.M))
    if count != 1:
        out.append(Finding(path, 1, "T-TYPEFILE", "%d TYPE blocks; one TYPE per .udt" % count))
    first = next((i for i, ln in enumerate(text.splitlines(), 1) if ln.strip()), None)
    if first is not None and not text.splitlines()[first - 1].lstrip().startswith("TYPE"):
        out.append(Finding(path, first, "T-TYPEFILE", "text before the TYPE keyword"))
    return out


def check_case_else(path: pathlib.Path, block: Block) -> list[Finding]:
    """T-CASE: every CASE has an ELSE at its own nesting level."""
    out = []
    tokens = list(re.finditer(r"\b(CASE|END_CASE|ELSE|IF|END_IF)\b", block.body))
    stack = []  # entries: [kind, offset, has_else]
    for t in tokens:
        word = t.group(1)
        if word in ("CASE", "IF"):
            stack.append([word, t.start(), False])
        elif word == "ELSE" and stack:
            stack[-1][2] = True
        elif word in ("END_CASE", "END_IF") and stack:
            kind, off, has_else = stack.pop()
            if kind == "CASE" and not has_else:
                out.append(Finding(path, line_of(block, off), "T-CASE", "CASE without ELSE (Core §5.6)"))
    return out


def check_keyword_and_collide(path: pathlib.Path, block: Block) -> list[Finding]:
    out = []
    seen = {}
    for d in block.decls + block.constants:
        low = d.name.lower()
        if low in HEADER_KEYWORDS and not d.quoted and d.section != "VAR_TEMP":
            out.append(Finding(path, d.line, "T-KEYWORD", 'member "%s" must be declared quoted ("%s")' % (d.name, d.name)))
        if low in RESERVED:
            out.append(Finding(path, d.line, "T-COLLIDE", "reserved word used as a name: %s" % d.name))
        if low in seen and seen[low] != d.name:
            out.append(Finding(path, d.line, "T-COLLIDE", "%s differs only in case from %s" % (d.name, seen[low])))
        seen.setdefault(low, d.name)
    return out


def check_ext(path: pathlib.Path, block: Block, fb_names: set[str]) -> list[Finding]:
    out = []
    for d in block.decls:
        writable = re.search(r"ExternalWritable\s*:=\s*'True'", d.attrs, re.I)
        if writable and d.name.lower() != "hmirequest":
            out.append(Finding(path, d.line, "T-EXT", "only HmiRequest may be ExternalWritable (got %s)" % d.name))
        if block.kind != "FUNCTION_BLOCK" or not is_module_fb(block) or d.section != "VAR":
            continue
        is_fb = d.type_text.strip('"') in fb_names
        hidden = re.search(r"ExternalAccessible\s*:=\s*'False'", d.attrs, re.I)
        if not is_fb and d.name.lower() not in CONTRACT and not hidden:
            out.append(Finding(path, d.line, "T-EXT", "private static %s must be ExternalAccessible := 'False'" % d.name))
    return out


def is_module_fb(block: Block) -> bool:
    return '"FRK_Begin"' in block.body


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def check_frame(path: pathlib.Path, block: Block) -> list[Finding]:
    """T-FRAME: FRK_Begin once, FRK_End once after it; on a module that declares
    MODULE_CM / MODULE_EM both sit inside the one quiescent guard (§3.14)."""
    out = []
    begins = [m.start() for m in re.finditer(r'"FRK_Begin"\s*\(', block.body)]
    ends = [m.start() for m in re.finditer(r'"FRK_End"\s*\(', block.body)]
    if len(begins) != 1 or len(ends) != 1:
        out.append(Finding(path, block.body_line, "T-FRAME", "FRK_Begin x%d, FRK_End x%d: exactly one each" % (len(begins), len(ends))))
        return out
    if ends[0] < begins[0]:
        out.append(Finding(path, line_of(block, ends[0]), "T-FRAME", "FRK_End before FRK_Begin"))
    guarded = any(c.name in ("MODULE_CM", "MODULE_EM") for c in block.constants)
    depth_begin = nesting_depth(block.body, begins[0])
    depth_end = nesting_depth(block.body, ends[0])
    if guarded:
        guard = list(re.finditer(r"\bIF\s+(NOT\s*\(.*?\))\s+THEN\b", block.body[:begins[0]], re.S))
        if not guard or norm(guard[-1].group(1)) != norm(QUIET_GUARD):
            out.append(Finding(path, line_of(block, begins[0]), "T-FRAME", "the lifecycle is not inside the exact quiescent guard (Part IV §3.14)"))
        elif depth_begin != 1 or depth_end != 1:
            out.append(Finding(path, line_of(block, begins[0]), "T-FRAME", "FRK_Begin/FRK_End must sit directly inside the quiescent guard"))
    elif depth_begin != 0 or depth_end != 0:
        out.append(Finding(path, line_of(block, begins[0]), "T-FRAME", "FRK_Begin/FRK_End must be unconditional"))
    return out


OPEN_RE = re.compile(r"\b(IF|CASE|FOR|WHILE|REPEAT|REGION)\b")
CLOSE_RE = re.compile(r"\b(END_IF|END_CASE|END_FOR|END_WHILE|END_REPEAT|END_REGION)\b")


def nesting_depth(body: str, offset: int) -> int:
    prefix = body[:offset]
    opens = len(OPEN_RE.findall(prefix))
    closes = len(CLOSE_RE.findall(prefix))
    return opens - closes


def check_cyclic(path: pathlib.Path, block: Block, module_names: set[str]) -> list[Finding]:
    """T-CYCLIC: every child MODULE (an FB that runs the lifecycle) is called
    exactly once, unconditionally. A sequence instance is not a child module:
    its lifecycle-only adapter runs it per mode (Part IV §3.5)."""
    out = []
    for d in block.decls:
        if d.section != "VAR" or d.type_text.strip('"') not in module_names:
            continue
        calls = [m.start() for m in re.finditer(r"#%s\s*\(" % re.escape(d.name), block.body)]
        if len(calls) != 1:
            out.append(Finding(path, d.line, "T-CYCLIC", "child %s called %d times; exactly once" % (d.name, len(calls))))
        elif nesting_depth(block.body, calls[0]) != 0:
            out.append(Finding(path, line_of(block, calls[0]), "T-CYCLIC", "child %s called conditionally" % d.name))
    return out


def check_core(path: pathlib.Path, block: Block) -> list[Finding]:
    """T-CORE: an AUTHORED region never writes a lifecycle member of #Core."""
    out = []
    raw = block.raw_body
    markers = [(m.start(), "authored" in m.group(1).lower() and "generated:" not in m.group(1).lower())
               for m in re.finditer(r"//\s*----\s*([^\n]*)", raw)]
    for m in re.finditer(r"#Core\.(\w+)\s*:=", block.body):
        member = m.group(1).lower()
        region = [authored for pos, authored in markers if pos < m.start()]
        if region and region[-1] and member in LIFECYCLE:
            out.append(Finding(path, line_of(block, m.start()), "T-CORE", "authored code writes lifecycle member #Core.%s" % m.group(1)))
    return out


def check_ownio(path: pathlib.Path, block: Block) -> list[Finding]:
    """T-OWNIO: a block never reads its own output nor writes its own input."""
    out = []
    if block.kind not in ("FUNCTION_BLOCK", "FUNCTION"):
        return out
    outputs = {d.name for d in block.decls if d.section == "VAR_OUTPUT"}
    inputs = {d.name for d in block.decls if d.section == "VAR_INPUT"}
    for m in re.finditer(r"(=>\s*)?#(\w+)((?:\.\w+|\[[^\]]*\])*)\s*(:=)?", block.body):
        name, written_by_out, assigned = m.group(2), m.group(1), m.group(4)
        if name in outputs and not written_by_out and not assigned:
            out.append(Finding(path, line_of(block, m.start()), "T-OWNIO", "reads its own output #%s" % name))
        if name in inputs and assigned and not written_by_out:
            out.append(Finding(path, line_of(block, m.start()), "T-OWNIO", "writes its own input #%s" % name))
    return out


def check_seq(path: pathlib.Path, block: Block) -> list[Finding]:
    """T-SEQ: every non-ELSE branch of CASE #Seq.Step ends in FRK_Seq_Advance."""
    out = []
    m = re.search(r"\bCASE\s+#Seq\.Step\s+OF\b", block.body)
    if not m:
        return out
    end = re.search(r"\bEND_CASE\b", block.body[m.end():])
    region = block.body[m.end(): m.end() + (end.start() if end else len(block.body))]
    # labels and the ELSE of THIS case only, not of an IF/CASE nested in a branch
    labels = [lab for lab in re.finditer(r"^\s*(\d+)\s*:(?!=)", region, re.M)
              if nesting_depth(region, lab.start()) == 0]
    else_m = next((e for e in re.finditer(r"^\s*ELSE\b", region, re.M)
                   if nesting_depth(region, e.start()) == 0), None)
    for i, lab in enumerate(labels):
        stop = labels[i + 1].start() if i + 1 < len(labels) else (else_m.start() if else_m else len(region))
        branch = region[lab.end():stop].strip()
        statements = [s.strip() for s in branch.split(";") if s.strip()]
        if not statements or not statements[-1].startswith('"FRK_Seq_Advance"'):
            out.append(Finding(path, line_of(block, m.end() + lab.start()), "T-SEQ",
                               "step %s does not end in FRK_Seq_Advance" % lab.group(1)))
    return out


# ------------------------------------------------------------------- driver

def lint(paths: list[pathlib.Path]) -> list[Finding]:
    files = []
    for p in paths:
        files.extend(sorted(f for f in p.rglob("*") if f.suffix in ASCII_SUFFIXES) if p.is_dir() else [p])
    findings: list[Finding] = []
    parsed = []
    for f in files:
        data = f.read_bytes()
        findings += check_ascii(f, data)
        if f.suffix not in SOURCE_SUFFIXES:
            continue
        text = data.decode("ascii", errors="replace")
        if f.suffix == ".udt":
            findings += check_typefile(f, text)
        parsed.append((f, parse_blocks(text)))
    fb_names = {b.name for _, blocks in parsed for b in blocks if b.kind == "FUNCTION_BLOCK"}
    module_names = {b.name for _, blocks in parsed for b in blocks
                    if b.kind == "FUNCTION_BLOCK" and is_module_fb(b)}
    for f, blocks in parsed:
        for b in blocks:
            findings += check_keyword_and_collide(f, b)
            findings += check_ext(f, b, fb_names)
            if b.kind in ("FUNCTION_BLOCK", "FUNCTION", "ORGANIZATION_BLOCK"):
                findings += check_case_else(f, b)
                findings += check_ownio(f, b)
                findings += check_seq(f, b)
            if b.kind == "FUNCTION_BLOCK" and is_module_fb(b):
                findings += check_frame(f, b)
                findings += check_cyclic(f, b, module_names)
                findings += check_core(f, b)
    return findings


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    paths = [pathlib.Path(a) for a in argv if not a.startswith("--")] or [root / "Spikes"]
    findings = lint(paths)
    for f in findings:
        print(f)
    print("tia_lint: %d finding(s); pending (need the generator's declaration model): %s"
          % (len(findings), ", ".join(PENDING)))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

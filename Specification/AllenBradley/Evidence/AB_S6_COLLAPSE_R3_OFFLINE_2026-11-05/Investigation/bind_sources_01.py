"""Bind every source this checkpoint changes by SHA-256, and check each keeps its line endings.

The list is `git status --porcelain` itself, so no changed file escapes it.
Excluded: three files the owner is editing separately, this evidence
folder, and deletions (recorded by path). A file tracked at HEAD must keep
HEAD's convention (a renamed one, its old path's); a new file must be LF.
Writes the binding to the path given; exits 1 on any defect.
"""
from pathlib import Path
import hashlib, json, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
OWNER = {'.vscode/settings.json', 'FraktalCore/PLC/Siemens/Tests/Manifest/README.md', 'analysis_options.yaml'}
HERE = 'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_R3_OFFLINE_2026-11-05'


def convention(data):
    crlf, lf = data.count(b'\r\n'), data.count(b'\n')
    return 'CRLF' if crlf and crlf == lf else 'LF' if not crlf else 'MIXED'


status = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=R,
                        capture_output=True, text=True, check=True).stdout.splitlines()
rows, deleted, defects = [], [], []
for line in status:
    code, path = line[:2], line[3:]
    old = path
    if ' -> ' in path:
        old, path = path.split(' -> ')
    if path in OWNER or path.startswith(HERE):
        continue
    if 'D' in code:
        deleted.append(path)
        continue
    data = (R / path).read_bytes()
    at_head = subprocess.run(['git', 'show', 'HEAD:' + old], cwd=R, capture_output=True)
    expected = convention(at_head.stdout) if at_head.returncode == 0 else 'LF'
    actual = convention(data)
    if actual != expected or b'\r' in data.replace(b'\r\n', b''):
        defects.append(path)
    rows.append(dict(file=path, renamedFrom=old if old != path else None, status=code.strip(),
                     sha256=hashlib.sha256(data).hexdigest().upper(), lineEndings=actual, expected=expected))
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(dict(files=rows, deleted=sorted(deleted), defects=defects), stream, indent=2)
print(json.dumps(dict(files=len(rows), deleted=len(deleted), defects=defects)))
raise SystemExit(1 if defects else 0)

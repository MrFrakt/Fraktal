"""Bind this checkpoint's sources by SHA-256 and check each keeps its line endings.

A file tracked at HEAD must keep HEAD's convention; a new text file must be LF.
The two gzip fixtures are bound by hash only. Writes the binding to the path
given; exits 1 on any defect.
"""
from pathlib import Path
import hashlib, json, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = 'FraktalCore/PLC/Allen-Bradley/tools/'
FIXTURES = TOOLS + 'fixtures/schema_identity/'
GATED = ('fraktal_ab_genealogy_s6_host_demo', 'fraktal_ab_press_canonical_echo38')
FILES = [TOOLS + 'fraktal_ab_schema_identity.py', TOOLS + 'test_fraktal_ab_schema_identity.py',
         *(FIXTURES + d + '.declared.json' for d in GATED),
         'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md',
         'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md']
BINARY = [FIXTURES + d + '.json.gz' for d in GATED]


def convention(data):
    crlf, lf = data.count(b'\r\n'), data.count(b'\n')
    return 'CRLF' if crlf and crlf == lf else 'LF' if not crlf else 'MIXED'


rows, defects = [], []
for name in FILES:
    data = (R / name).read_bytes()
    at_head = subprocess.run(['git', 'show', 'HEAD:' + name], cwd=R, capture_output=True)
    expected = convention(at_head.stdout) if at_head.returncode == 0 else 'LF'
    actual = convention(data)
    if actual != expected or b'\r' in data.replace(b'\r\n', b''):
        defects.append(name)
    rows.append(dict(file=name, sha256=hashlib.sha256(data).hexdigest().upper(), lineEndings=actual,
                     expected=expected, trackedAtHead=at_head.returncode == 0))
for name in BINARY:
    data = (R / name).read_bytes()
    tracked = subprocess.run(['git', 'cat-file', '-e', 'HEAD:' + name], cwd=R, capture_output=True).returncode == 0
    if tracked:
        defects.append(name)  # a recorded baseline is written once, never replaced
    rows.append(dict(file=name, sha256=hashlib.sha256(data).hexdigest().upper(), lineEndings='binary',
                     trackedAtHead=tracked))
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(dict(files=rows, defects=defects), stream, indent=2)
print(json.dumps(dict(files=len(rows), defects=defects)))
raise SystemExit(1 if defects else 0)

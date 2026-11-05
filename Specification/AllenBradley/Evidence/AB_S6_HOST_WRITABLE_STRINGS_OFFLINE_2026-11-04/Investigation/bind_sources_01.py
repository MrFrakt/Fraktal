"""Bind this checkpoint's sources by SHA-256 and check each keeps its line endings.

A file tracked at HEAD must keep HEAD's convention; a new file must be LF.
Writes the binding to the path given; exits 1 on any defect.
"""
from pathlib import Path
import hashlib, json, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = 'FraktalCore/PLC/Allen-Bradley/tools/'
FILES = [TOOLS + n for n in (
    'fraktal_ab_host_services.py', 'fraktal_ab_canonical_publication.py', 'fraktal_ab_access_audit.py',
    'test_fraktal_ab_v611_image.py', 'test_fraktal_ab_st_bool_operands.py')]


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
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(dict(files=rows, defects=defects), stream, indent=2)
print(json.dumps(dict(files=len(rows), defects=defects)))
raise SystemExit(1 if defects else 0)

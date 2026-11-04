"""Bind this checkpoint's sources by SHA-256 and check each keeps its line endings.

A file tracked at HEAD must keep HEAD's convention (all-LF or all-CRLF); a new
file must be LF. Writes the binding to the path given; exits 1 on any defect.
"""
from pathlib import Path
import hashlib, json, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = 'FraktalCore/PLC/Allen-Bradley/tools/'
SPEC = 'Specification/AllenBradley/'
FILES = [TOOLS + n for n in (
    'fraktal_ab_host_sets.py', 'fraktal_ab_st_bench.py', 'test_fraktal_ab_host_sets.py',
    'fraktal_ab_host_services.py', 'fraktal_ab_canonical_commands.py', 'fraktal_ab_mailbox.py',
    'fraktal_ab_sets.py', 'fraktal_ab_canonical_publication.py', 'fraktal_ab_generate.py',
    'fraktal_ab_owner_read_bindings.py', 'fraktal_ab_canonical_traceability.py', 'fraktal_ab_declaration.py',
    'fraktal_ab_canonical_config.py', 'test_fraktal_ab_host_live.py')] + [
    SPEC + 'AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md',
    SPEC + 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    SPEC + 'AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md']


def convention(data):
    crlf, lf = data.count(b'\r\n'), data.count(b'\n')
    return 'CRLF' if crlf and crlf == lf else 'LF' if not crlf else 'MIXED'


rows, defects = [], []
for name in FILES:
    data = (R / name).read_bytes()
    head = subprocess.run(['git', 'show', 'HEAD:' + name], cwd=R, capture_output=True)
    expected = convention(head.stdout) if head.returncode == 0 else 'LF'
    actual = convention(data)
    if actual != expected or b'\r' in data.replace(b'\r\n', b''):
        defects.append(name)
    rows.append(dict(file=name, sha256=hashlib.sha256(data).hexdigest().upper(), lineEndings=actual,
                     expected=expected, trackedAtHead=head.returncode == 0))
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(dict(files=rows, defects=defects), stream, indent=2)
print(json.dumps(dict(files=len(rows), defects=defects)))
raise SystemExit(1 if defects else 0)

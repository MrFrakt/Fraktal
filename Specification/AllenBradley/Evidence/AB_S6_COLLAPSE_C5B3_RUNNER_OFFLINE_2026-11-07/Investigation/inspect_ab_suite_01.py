"""Extract the failure tracebacks and final summary from ab_full_suite_01.log."""
from __future__ import annotations

from pathlib import Path

W = Path(__file__).parent
text = (W / 'ab_full_suite_01.log').read_bytes().decode('utf-8', errors='replace')
lines = text.splitlines()
for idx, line in enumerate(lines):
    if line.startswith('======================================================================'):
        print('\n'.join(lines[idx:]))
        break
else:
    print('\n'.join(lines[-80:]))

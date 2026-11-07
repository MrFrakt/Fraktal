"""Extract failure tracebacks from ab_full_suite_01.log into ab_suite_01_failures.json."""
from __future__ import annotations

import json
from pathlib import Path

W = Path(__file__).parent
text = (W / 'ab_full_suite_01.log').read_bytes().decode('utf-8', errors='replace').replace('\x00', '')
lines = text.splitlines()
tail_start = next((i for i, l in enumerate(lines) if l.startswith('======================================================================')), max(0, len(lines) - 100))
out = {'totalLines': len(lines), 'tail': lines[tail_start:]}
with (W / 'ab_suite_01_failures.json').open('x', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(json.dumps({'tailLines': len(out['tail']), 'lastLine': lines[-1] if lines else ''}))

"""Extract passing test count and summary from ab_full_suite_02.log into ab_suite_02_summary.json."""
from __future__ import annotations

import json
from pathlib import Path
import re

W = Path(__file__).parent
text = (W / 'ab_full_suite_02.log').read_bytes().decode('utf-8', errors='replace').replace('\x00', '')
lines = text.splitlines()
ran_lines = [l for l in lines if re.match(r'^Ran \d+ tests in ', l)]
ok_lines = [l for l in lines if l.strip().startswith('OK')]
assert len(ran_lines) == 1 and ok_lines, f'Unexpected summary lines: {ran_lines} / {ok_lines}'
count = int(re.search(r'^Ran (\d+) tests', ran_lines[0]).group(1))
summary = {
    'passed': True,
    'testCount': count,
    'ranLine': ran_lines[0],
    'okLine': ok_lines[-1],
    'totalLogLines': len(lines),
}
with (W / 'ab_suite_02_summary.json').open('x', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(json.dumps({'passed': True, 'testCount': count}))

"""Record SHA-256 freeze 02 of Increment 2 modified/added AB tools and verify excluded owner files are unchanged."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

W = Path(__file__).parent
REPO = Path('C:/Users/SoftIndVM/Fraktal')

INCREMENT_FILES = (
    'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_press_canonical_execute.py',
    'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_press_launcher_canonical.py',
)


def main():
    before = json.loads((W / 'unrelated_before.json').read_text(encoding='utf-8'))
    unrelated_after = []
    for row in before:
        p = REPO / row['path']
        actual = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        assert actual == row['sha256'], f'Excluded file changed: {row["path"]}'
        unrelated_after.append({'path': row['path'], 'sha256': actual, 'unchanged': True})

    frozen = []
    for rel in INCREMENT_FILES:
        p = REPO / rel
        data = p.read_bytes()
        frozen.append({
            'path': rel,
            'sha256': hashlib.sha256(data).hexdigest().upper(),
            'bytes': len(data),
        })

    report = {
        'passed': True,
        'parentCommit': '0730d3feb4ee8877c0e63ad31710a73ad7c11644',
        'incrementFiles': frozen,
        'excludedOwnerEdits': unrelated_after,
    }
    with (W / 'tools_freeze_02.json').open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2)
    print(json.dumps({'passed': True, 'frozenCount': len(frozen)}))


if __name__ == '__main__':
    main()

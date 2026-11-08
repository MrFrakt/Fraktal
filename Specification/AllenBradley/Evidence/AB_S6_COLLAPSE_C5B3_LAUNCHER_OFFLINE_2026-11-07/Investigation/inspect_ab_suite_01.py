"""UTF-8/ASCII-safe inspector for ab_full_suite_01.log."""
from __future__ import annotations

import json
from pathlib import Path

W = Path(__file__).parent


def main():
    text = (W / 'ab_full_suite_01.log').read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines()
    tail = lines[-120:]
    report = {
        'lineCount': len(lines),
        'tail': tail,
    }
    with (W / 'ab_suite_inspect_01.json').open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2, ensure_ascii=True)
    print(json.dumps({'lineCount': len(lines), 'summary': lines[-5:]}, ensure_ascii=True))


if __name__ == '__main__':
    main()

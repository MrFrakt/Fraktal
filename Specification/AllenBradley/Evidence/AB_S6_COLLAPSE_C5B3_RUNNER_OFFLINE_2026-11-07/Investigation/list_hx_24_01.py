"""Read-only check of all 24 HX modules from hx_fact_accounting_02.json and their current collapsed-branch status."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = REPO / 'FraktalCore/PLC/Allen-Bradley/tools'
W = Path(__file__).parent


def main():
    hx = json.loads((REPO / 'Specification/AllenBradley/Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03/Investigation/hx_fact_accounting_02.json').read_text(encoding='utf-8'))
    rows = []
    for h in hx['harnesses']:
        mod = h['module']
        src = (TOOLS / f'{mod}.py').read_text(encoding='utf-8')
        has_collapse_ref = ('canonical_collapse' in src) or ('fraktal_ab_fixture_reads' in src) or ('fraktal_ab_canonical_reader' in src)
        rows.append({
            'module': mod,
            'hasCanonicalOrCollapseRef': has_collapse_ref,
            'runtimeApis20261103': h['runtimeApis'],
            'legacyCommandPaths20261103': h['legacyCommandPaths'],
            'subscriptFacts20261103': h['subscriptFacts'],
        })
    with (W / 'hx_24_status_01.json').open('x', encoding='utf-8') as out:
        json.dump({'count': len(rows), 'harnesses': rows}, out, indent=2)
    print(json.dumps({'count': len(rows), 'withoutCollapseRef': [r['module'] for r in rows if not r['hasCanonicalOrCollapseRef']]}))


if __name__ == '__main__':
    main()

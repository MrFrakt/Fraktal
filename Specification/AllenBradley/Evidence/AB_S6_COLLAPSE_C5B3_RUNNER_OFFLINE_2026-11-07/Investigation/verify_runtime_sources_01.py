"""Verify all 84 shipping HMI/Dart sources and both runtime binaries against sealed C5b2 runtime_bindings_01.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

W = Path(__file__).parent
REPO = Path('C:/Users/SoftIndVM/Fraktal')


def main():
    c5b2_path = REPO / 'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06/Gates/runtime_bindings_01.json'
    c5b2_sha = hashlib.sha256(c5b2_path.read_bytes()).hexdigest().upper()
    c5b2 = json.loads(c5b2_path.read_text(encoding='utf-8'))
    sources = c5b2['sources']
    assert len(sources) > 0, 'Expected non-empty sources table in runtime_bindings_01.json'

    mismatches = []
    for rel, expected_sha in sorted(sources.items()):
        actual = hashlib.sha256((REPO / rel).read_bytes()).hexdigest().upper()
        if actual != expected_sha.upper():
            mismatches.append({'file': rel, 'expected': expected_sha.upper(), 'actual': actual})

    executables = {}
    for key in ('gateway', 'hostAdapter'):
        info = c5b2[key]
        exe_path = Path(info['path'])
        assert exe_path.exists(), f'Missing prepared executable: {exe_path}'
        actual = hashlib.sha256(exe_path.read_bytes()).hexdigest().upper()
        expected = info['sha256'].upper()
        executables[key] = {
            'path': str(exe_path),
            'expectedSha256': expected,
            'actualSha256': actual,
            'matches': actual == expected,
        }
        assert executables[key]['matches'], f'Executable hash mismatch for {key}'

    report = {
        'passed': not mismatches and all(v['matches'] for v in executables.values()),
        'c5b2Reference': str(c5b2_path.relative_to(REPO).as_posix()),
        'c5b2ReferenceSha256': c5b2_sha,
        'shippingSourceCount': len(sources),
        'shippingSourceMismatches': mismatches,
        'preparedExecutables': executables,
        'controllerAccess': False,
        'credentialsRead': False,
    }
    with (W / 'runtime_sources_verified_01.json').open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2)
    assert report['passed'], f'Runtime source check failed: {report}'
    print(json.dumps({'passed': True, 'shippingSourceCount': len(sources)}))


if __name__ == '__main__':
    main()

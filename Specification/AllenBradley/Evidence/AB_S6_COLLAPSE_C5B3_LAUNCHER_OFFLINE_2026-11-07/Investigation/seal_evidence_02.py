"""Seal whitelisted C5b3 standalone press launcher qualification artifacts (including retained failed runs) and generate artifact_manifest.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

W = Path(__file__).parent
REPO = Path('C:/Users/SoftIndVM/Fraktal')
EVIDENCE_DIR = REPO / 'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_LAUNCHER_OFFLINE_2026-11-07'
FORBIDDEN_SUFFIXES = {'.l5x', '.acd', '.bak', '.exe', '.dll'}


def main():
    assert not EVIDENCE_DIR.exists(), f'Evidence directory already exists: {EVIDENCE_DIR}'
    ab_exit = W / 'ab_full_suite_02_exit.json'
    assert ab_exit.exists(), 'ab_full_suite_02_exit.json has not completed yet'
    exit_data = json.loads(ab_exit.read_text(encoding='utf-8'))
    assert exit_data['exitCode'] == 0, f'ab_full_suite_02 failed: {exit_data}'

    gates_dir = EVIDENCE_DIR / 'Gates'
    inv_dir = EVIDENCE_DIR / 'Investigation'
    gates_dir.mkdir(parents=True, exist_ok=False)
    inv_dir.mkdir(parents=True, exist_ok=False)

    for item in sorted(W.iterdir()):
        if item.is_dir():
            continue
        suffix = item.suffix.lower()
        assert suffix not in FORBIDDEN_SUFFIXES, f'Forbidden binary/project file in control root: {item}'
        if suffix in ('.log', '.json'):
            shutil.copy2(item, gates_dir / item.name)
        elif suffix == '.py':
            shutil.copy2(item, inv_dir / item.name)

    manifest_files = []
    for path in sorted(EVIDENCE_DIR.rglob('*')):
        if path.is_dir():
            continue
        assert path.suffix.lower() not in FORBIDDEN_SUFFIXES
        rel = path.relative_to(EVIDENCE_DIR).as_posix()
        data = path.read_bytes()
        manifest_files.append({
            'path': rel,
            'sha256': hashlib.sha256(data).hexdigest().upper(),
            'bytes': len(data),
        })

    manifest = {
        'schema': 'fraktal.evidence.artifacts',
        'schemaVersion': 1,
        'files': manifest_files,
    }
    manifest_path = EVIDENCE_DIR / 'artifact_manifest.json'
    with manifest_path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(manifest, out, indent=2)
        out.write('\n')

    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
    print(json.dumps({
        'sealedFiles': len(manifest_files),
        'manifestSha256': manifest_sha,
        'abFullSuiteExitCode': exit_data['exitCode'],
    }))


if __name__ == '__main__':
    main()

"""Relocate frozen payloads without changing bytes; resolve historical SHA paths."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[4]
DOCS = Path('Specification/Siemens/Evidence')
DATA = Path('FraktalCore/PLC/Siemens/Evidence')
INDEX = DATA / 'relocation.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(path, parent):
    path.resolve().relative_to(parent.resolve())
    return path


def resolve(relative, index):
    relative = relative.replace('\\', '/')
    if relative in index['reports']:
        return REPO / index['reports'][relative]
    for old, new in index['directories'].items():
        if relative == old or relative.startswith(old + '/'):
            return REPO / (new + relative[len(old):])
    return inside(REPO / relative, REPO)


def verify(index=None):
    index = index or json.loads((REPO / INDEX).read_bytes())
    for old, row in index['files'].items():
        assert digest(resolve(old, index)) == row['sha256'], old
    bindings = {}
    for old in index['files']:
        if Path(old).name != 'SHA256SUMS':
            continue
        count = 0
        for line in resolve(old, index).read_text('ascii').splitlines():
            expected, relative = line.split('  ', 1)
            assert digest(resolve(relative, index)) == expected, relative
            count += 1
        bindings[old] = count
    assert all(p.suffix == '.md' for p in (REPO / 'Specification/Siemens').rglob('*') if p.is_file())
    return {'preserved_files': len(index['files']), 'historical_sha_bindings': bindings,
            'specification_contains_only_markdown': True}


def relocate():
    assert not (REPO / INDEX).exists(), 'Relocation already recorded; use verify'
    source = inside(REPO / DOCS, REPO / 'Specification/Siemens')
    destination = inside(REPO / DATA, REPO / 'FraktalCore/PLC/Siemens')
    directories = {p.relative_to(REPO).as_posix():
                   (DATA / 'Archives' / p.name).as_posix()
                   for p in sorted(source.iterdir()) if p.is_dir()}
    reports = {p.relative_to(REPO).as_posix():
               (DATA / 'HistoricalReports' / p.name).as_posix()
               for p in sorted(source.glob('*.md'))}
    files = {}
    for relative in directories:
        for p in sorted((REPO / relative).rglob('*')):
            if p.is_file():
                files[p.relative_to(REPO).as_posix()] = {'sha256': digest(p), 'bytes': p.stat().st_size}
    for relative in reports:
        p = REPO / relative
        files[relative] = {'sha256': digest(p), 'bytes': p.stat().st_size}
    index = {'version': 1, 'directories': directories, 'reports': reports, 'files': files}
    destination.mkdir(parents=True, exist_ok=True)
    for old, new in reports.items():
        target = inside(REPO / new, destination)
        assert not target.exists(), target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / old, target)
    for old, new in directories.items():
        origin = inside(REPO / old, source)
        target = inside(REPO / new, destination)
        assert not target.exists(), target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origin), str(target))
    # Original reports and manifests stay immutable. Current document copies
    # receive corrected links; historical checksums resolve to the originals.
    paths = [REPO / 'AGENTS.md', REPO / 'Specification/README.md',
             REPO / 'Specification/Fraktal_TIA_Part_IV.md']
    paths += list((REPO / 'Specification/Siemens').rglob('*.md'))
    paths += [p for p in (REPO / 'FraktalCore/PLC/Siemens').rglob('*.md')
              if DATA not in p.relative_to(REPO).parents]
    replacements = []
    for p in paths:
        text = p.read_bytes().decode('utf-8')
        before = text
        def link(hit):
            raw = hit.group(1)
            if '://' in raw or raw.startswith('#'):
                return hit.group(0)
            address, sep, fragment = raw.partition('#')
            resolved = (p.parent / address).resolve()
            for old, new in directories.items():
                try:
                    suffix = resolved.relative_to(REPO / old)
                except ValueError:
                    continue
                corrected = os.path.relpath(REPO / new / suffix, p.parent).replace('\\', '/')
                return '](' + corrected + (sep + fragment if sep else '') + ')'
            return hit.group(0)
        text = re.sub(r'\]\(([^)]+)\)', link, text)
        if p.parent == source:
            for old, new in directories.items():
                label = Path(old).name + '/'
                target = os.path.relpath(REPO / new, p.parent).replace('\\', '/') + '/'
                text = text.replace('`' + label + '`', '`' + target + '`')
        if text != before:
            p.write_bytes(text.replace('\r\n', '\n').encode('utf-8'))
            replacements.append(p.relative_to(REPO).as_posix())
    index['updated_documents'] = replacements
    (REPO / INDEX).write_bytes((json.dumps(index, indent=2) + '\n').encode('ascii'))
    return verify(index)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('relocate', 'verify'))
    args = parser.parse_args()
    print(json.dumps(relocate() if args.action == 'relocate' else verify(), indent=2))


if __name__ == '__main__':
    main()

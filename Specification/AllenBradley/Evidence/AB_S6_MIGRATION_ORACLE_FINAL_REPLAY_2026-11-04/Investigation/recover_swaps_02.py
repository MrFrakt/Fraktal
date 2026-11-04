"""Recover from an interrupted run_replays_02: put every original back.

For each ``C:/work/<root>.wp63-original``: a marked copy at ``<root>`` is
removed, then the original is renamed back. A ``<root>`` without the marker is
never touched; the script stops and reports it instead. Clears read-only
attributes on restored originals listed in protected_originals_02.json.
"""
import json
import os
from pathlib import Path
import shutil
import stat

MARKER, SUFFIX = '.wp63-replay-copy', '.wp63-original'
for backup in sorted(Path('C:/work').glob('*' + SUFFIX)):
    root = Path(str(backup)[:-len(SUFFIX)])
    if root.exists():
        if not (root / MARKER).is_file():
            raise SystemExit(f'{root} exists without the copy marker; resolve by hand')
        shutil.rmtree(root, onexc=lambda f, p, e: (os.chmod(p, stat.S_IWRITE | stat.S_IREAD), f(p)))
    backup.rename(root)
    print('restored', root)
listing = Path(__file__).resolve().parents[1] / 'Gates/protected_originals_02.json'
if listing.is_file():
    for p in json.loads(listing.read_text(encoding='utf-8'))['files']:
        if os.path.exists(p):
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
print('done')

"""Locate each mismatched pin's sealed bytes and diff today's regeneration (read-only).

Searches stage evidence and session folders for an L5X (or .L5X.gz) whose
SHA-256 equals the pin, then prints every changed line between it and today's
output. Expectation under test: only the S5 write-revision assignments differ.
"""
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import sys

E = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence')
SEARCH = [*E.glob('AB_S3K_*'), *E.glob('AB_S4A_*'), *E.glob('AB_S4B_CANONICAL_PREPARATION*'),
          *E.glob('AB_S4B_COLD_DESKTOP_PREPARATION*'), *E.glob('AB_PRESS_S3_EXIT_*'),
          *E.glob('AB_S4B_OWNER_REVISION_OFFLINE*'), *E.glob('AB_S4B_Q_*'),
          *map(Path, ['C:/work/fraktal-ab-s4b-20261025', 'C:/work/fraktal-ab-s4b-cold-20261026',
                      'C:/work/fraktal-ab-s3k-20261025', 'C:/work/fraktal-ab-s4-20261025',
                      'C:/work/fraktal-ab-s3-exit-20261025', 'C:/work/fraktal-ab-s4b-owner-20261029'])]
pins = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
work = Path(sys.argv[2])
wanted = {s['pin']: s for s in pins['stages'] if s['pin'] != s['actual']}
found = {}
for folder in SEARCH:
    for path in folder.rglob('*'):
        if not path.is_file() or not path.name.lower().endswith(('.l5x', '.l5x.gz')):
            continue
        data = path.read_bytes()
        if path.name.lower().endswith('.gz'):
            try:
                data = gzip.decompress(data)
            except OSError:
                continue
        digest = hashlib.sha256(data).hexdigest().upper()
        if digest in wanted and digest not in found:
            found[digest] = (path, data)
    if len(found) == len(wanted):
        break
names = {'s3k': 'stages/compat_current_s3k.L5X', 's4a': 'stages/compat_current_s4a.L5X',
         'press': 'stages/compat_current_press.L5X', 's4b-v6.8': 's4b-v6.8.L5X'}
report = []
for pin, stage in wanted.items():
    entry = dict(stage=stage['stage'], pin=pin, today=stage['actual'])
    if pin not in found:
        entry['sealedSource'] = None
        report.append(entry)
        continue
    sealed_path, sealed = found[pin]
    today = (work / names[stage['stage']]).read_bytes()
    assert hashlib.sha256(today).hexdigest().upper() == stage['actual']
    a, b = sealed.decode('utf-8').splitlines(), today.decode('utf-8').splitlines()
    changed = [line for line in difflib.unified_diff(a, b, lineterm='', n=0)
               if line[:1] in '+-' and not line.startswith(('+++', '---'))]
    entry.update(sealedSource=str(sealed_path).replace('\\', '/'), sealedLines=len(a), todayLines=len(b),
                 changedLines=len(changed), changes=changed[:12])
    report.append(entry)
print(json.dumps(report, indent=1))

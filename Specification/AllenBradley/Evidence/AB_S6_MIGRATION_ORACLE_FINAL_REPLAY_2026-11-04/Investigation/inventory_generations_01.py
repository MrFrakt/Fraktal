"""WP6.3 inventory of recorded generator runs (read-only).

Every evidence exit record whose command runs ``fraktal_ab_generate.py`` (or a
declaration module's generate entry) is listed with its declaration, seed and
output path. When the output file still exists, its SHA-256 is recorded so
accepted source pins can be matched to the exact inputs that produced them.
Writes one create-only JSON file.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

R = Path(__file__).resolve().parents[5]
E = R / 'Specification/AllenBradley/Evidence'
rows = []
for record in sorted(E.rglob('*_exit.json')):
    relative = record.relative_to(E).as_posix()
    if '/Source/' in relative or '/Sources/' in relative:
        continue
    try:
        data = json.loads(record.read_text(encoding='utf-8'))
    except (ValueError, UnicodeDecodeError):
        continue
    command = [str(c).replace('\\', '/') for c in (data.get('command') or [])] \
        if isinstance(data, dict) and isinstance(data.get('command'), list) else []
    if not any(c.endswith('fraktal_ab_generate.py') for c in command):
        continue
    declaration = command[command.index('--declaration') + 1] if '--declaration' in command else None
    files = [c for c in command if c.lower().endswith('.l5x')]
    seed, output = (files + [None, None])[:2]
    digest = None
    if output and os.path.isfile(output):
        digest = hashlib.sha256(Path(output).read_bytes()).hexdigest().upper()
    rows.append(dict(exitRecord=relative, exitCode=data.get('exitCode'), declaration=declaration,
                     seed=seed, seedPresent=bool(seed and os.path.isfile(seed)), output=output,
                     outputSha256=digest))
with Path(sys.argv[1]).open('x', encoding='utf-8') as f:
    json.dump(dict(schema='fraktal.ab.s6-wp63-generation-inventory', schemaVersion=1, runs=rows), f, indent=2)
print(len(rows), 'recorded generator runs')
for r in rows:
    print(f"{r['exitRecord'][:70]:70s} {str(r['declaration'])[:40]:40s} seed={'ok' if r['seedPresent'] else '--'} "
          f"{(r['outputSha256'] or '-')[:16]}")

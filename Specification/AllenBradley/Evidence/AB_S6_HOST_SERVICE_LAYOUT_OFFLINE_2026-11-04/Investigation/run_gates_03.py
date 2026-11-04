"""Closing gates after the document corrections: rebind sources, rerun documents.

Writes create-only Gates/source_bindings_02.json and gate_summary_03.json.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
PY = sys.executable
exits = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


first = json.loads((G / 'source_bindings_01.json').read_text(encoding='utf-8'))
gated = json.loads((G / 'full_ab_source_bindings_before_01.json').read_text(encoding='utf-8'))['sources']
files = {f: digest(R / f) for f in first['files']}
changed = sorted(f for f in files if files[f] != first['files'][f])
binding = dict(files=files, changedSinceBinding01=changed,
               toolsUnchangedSinceGates={p.name: digest(p) for p in sorted(T.glob('*.py'))} == gated)
with (G / 'source_bindings_02.json').open('x', encoding='utf-8') as f:
    json.dump(binding, f, indent=2)
for label, args in (('ab_spec_03', ['tools/check_ab_spec.py']),
                    ('consistency_strict_03', ['tools/check_consistency.py', '--strict'])):
    exits[label] = subprocess.run([PY, str(I / 'run_logged.py'), label, PY, *args], cwd=R).returncode
# Only the draft's text may differ: no source or test changed after the gates.
expected = ['Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md']
summary = dict(passed=all(c == 0 for c in exits.values()) and binding['toolsUnchangedSinceGates']
               and changed == expected, exits=exits, changedSinceBinding01=changed,
               toolsUnchangedSinceGates=binding['toolsUnchangedSinceGates'], controllerAccess=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (G / 'gate_summary_03.json').open('x', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

"""Convert this session's script-edited sources from CRLF back to LF.

Python's Path.write_text on Windows wrote CRLF; the repository stores bytes
verbatim (`.gitattributes`: `* -text`) and these files were LF before. Each
file must first equal the bytes its gate run bound, and contain no lone CR;
afterwards its bytes must equal those bytes with CRLF replaced by LF. Nothing
else changes. Writes create-only Gates/normalization_01.json.
"""
from pathlib import Path
import hashlib, json

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
G.mkdir(exist_ok=True)
R = Path('C:/Users/SoftIndVM/Fraktal')
E = R / 'Specification/AllenBradley/Evidence/AB_S6_HOST_SERVICE_LAYOUT_OFFLINE_2026-11-04/Gates'
TOOLS = 'FraktalCore/PLC/Allen-Bradley/tools/'
bound = json.loads((E / 'source_bindings_02.json').read_text(encoding='utf-8'))['files']
suite = json.loads((E / 'full_ab_source_bindings_before_01.json').read_text(encoding='utf-8'))['sources']
FILES = [f for f in bound if f.endswith(('.py', '.dart'))] + [TOOLS + 'test_fraktal_ab_canonical_live.py']


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


rows = []
for name in FILES:
    path = R / name
    before = path.read_bytes()
    gated = bound.get(name) or suite[Path(name).name]
    assert digest(before) == gated, name + ' differs from the bytes its gates ran'
    assert b'\r\n' in before and b'\r' not in before.replace(b'\r\n', b''), name
    after = before.replace(b'\r\n', b'\n')
    path.write_bytes(after)
    assert path.read_bytes() == after and b'\r' not in after
    rows.append(dict(file=name, gatedCrlfSha256=gated, lfSha256=digest(after),
                     lines=after.count(b'\n'), onlyLineEndingsChanged=after == before.replace(b'\r\n', b'\n')))
with (G / 'normalization_01.json').open('x', encoding='utf-8', newline='\n') as f:
    json.dump(dict(files=rows, normalized=len(rows)), f, indent=2)
    f.write('\n')
print(json.dumps(dict(normalized=len(rows)), indent=2))

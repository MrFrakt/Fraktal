"""Byte comparison of every setup_retry copy against its original, path rebinding aside."""
from pathlib import Path
import json, sys

P = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/prepare_9af0ac9f71534d89b5be9645bdc6575f')
W = Path(__file__).parent
OLD, NEW = P.as_posix().encode(), W.as_posix().encode()
names = json.loads((W/'setup_retry_01.json').read_text())['pathOccurrencesRebound']
rows = []
for name in names:
    original, copy = (P/name).read_bytes(), (W/name).read_bytes()
    expected = original.replace(OLD, NEW)
    rows.append(dict(name=name, identical=copy == expected, crlfOriginal=b'\r\n' in original, crlfCopy=b'\r\n' in copy,
                     identicalIgnoringLineEnds=copy.replace(b'\r\n', b'\n') == expected.replace(b'\r\n', b'\n')))
output = Path(sys.argv[1])
with output.open('x') as out:
    json.dump(dict(rows=rows, differing=[r['name'] for r in rows if not r['identical']]), out, indent=2)
print(json.dumps(dict(differing=[r['name'] for r in rows if not r['identical']],
                      onlyLineEnds=all(r['identicalIgnoringLineEnds'] for r in rows))))

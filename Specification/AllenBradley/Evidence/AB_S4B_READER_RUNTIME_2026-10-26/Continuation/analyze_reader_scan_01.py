"""Locate the native TASK finding in existing paired bytes; no Echo I/O."""
from pathlib import Path
import gzip
import json

W = Path(__file__).parent
D = W.parent / 'retry_reader_01'
cases = json.loads((D / 'candidate_regressions.json').read_bytes())
rows=[]
for group, pairs in cases.items():
    if not group.endswith('Pairs'):
        continue
    for entry in pairs:
        report=json.loads(gzip.decompress(Path(entry['output']).read_bytes()))
        probe=report['pair']['legacyInputs']['additional']['healthProbe']
        rows.append(dict(group=group,output=Path(entry['output']).name,probe=probe))
result=dict(readOnly=True,controllerAccess=False,captures=len(rows),
    firstProbe=rows[0]['probe'],rows=rows,
    limitation='Placement uses recorded TASK scalars; it does not identify code or host scheduling as the cause.')
with (D / 'scan_analysis_01.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(dict(captures=len(rows),firstProbe=rows[0]['probe'])))

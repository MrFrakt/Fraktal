from pathlib import Path
import gzip
import json

D = Path('C:/work/fraktal-ab-s4b-20261025/retry_coherence_01')
load = lambda p: json.loads(gzip.decompress(p.read_bytes()))
report = load(D / 'dart_qualification.json.gz')
rows = []
for index, document in enumerate(report['snapshots']):
    for path, value in document['dataValues'].items():
        if value['status'] != 0 or value['ageMs'] >= 7000:
            rows.append(dict(snapshot=index, path=path, **{k: v for k, v in value.items() if k != 'value'}))
rows.sort(key=lambda row: row['ageMs'], reverse=True)
diagnostic = load(D / 'readonly_diagnostics_01.json.gz')
uncertain = []
for sample in diagnostic['samples']:
    for path, value in sample['uncertain'].items():
        uncertain.append(dict(sample=sample['sample'], path=path,
            **{k: v for k, v in value.items() if k != 'value'}))
uncertain.sort(key=lambda row: row['ageMs'], reverse=True)
result = dict(lastSamples=report['samples'][-3:], snapshots=len(report['snapshots']),
    retainedNonGoodOrOldest=rows[:20], supplementaryError=diagnostic['error'],
    supplementaryNonGood=uncertain[:12], supplementarySnapshots=len(diagnostic['snapshots']))
with (D / 'failure_analysis_01.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))

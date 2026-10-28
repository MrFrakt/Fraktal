from pathlib import Path
from collections import Counter
import gzip
import json

W = Path(__file__).parent
D = W.parent / 'retry_root_diagnostic_01'
report = json.loads(gzip.decompress((D / 'dart_qualification.json.gz').read_bytes()))
rejected = [s for s in report['snapshots'] if s.get('qualificationRejectedRootSample')]
summaries = []
for sample in rejected:
    metadata = sample['dataValues']
    summaries.append(dict(
        rootFailure=sample['rootSampleFailure'],
        rootChildren=sample['rootChildren'],
        sampleAgeMs=sample['sampleAgeMs'],
        responseProcessingMs=sample.get('responseProcessingMs'),
        values=len(sample['values']), dataValues=len(metadata),
        statusCounts=dict(Counter(str(row['status']) for row in metadata.values())),
        reasonCounts=dict(Counter(str(row.get('reason')) for row in metadata.values() if row.get('reason'))),
        rootStatusValues={k: v for k, v in sample['values'].items()
            if any(k.startswith(root + '/Status/') for root in sample['rootChildren'])},
        maximumAgeMs=max((row.get('ageMs', 0) for row in metadata.values()), default=0),
        oldestFastValues=sorted((dict(path=key, **row) for key, row in metadata.items() if row['tier'] == 'fast'),
            key=lambda row: row.get('ageMs', 0), reverse=True)[:12],
        maximumAcceptedWindowUs=max((row.get('acceptedWindowUs') or 0 for row in metadata.values()), default=0)))
result = dict(passed=report['passed'], error=report['error'], elapsedMs=report['elapsedMs'],
    completedSamples=len(report['samples']), configurationPages=len(report['configurationPages']),
    retainedSnapshots=len(report['snapshots']), rejectedSnapshots=summaries)
with (D / 'diagnostic_inspection_01.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))

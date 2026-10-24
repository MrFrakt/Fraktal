from pathlib import Path
import datetime, hashlib, json

P = Path(__file__).parent
AB = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
review = AB/'AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md'
approval = dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    questionId='call_43d1f40d2efb4ab69d699df590f3c0bc:0',
    answer='Approve dependent values and offline work',
    scope='224 enumerated dependent value paths: 64 OEE validity flags and 160 profiler fields; offline work only',
    controllerChangesAuthorized=False,
    reviewSha256=hashlib.sha256(review.read_bytes()).hexdigest(),
    enumerationSha256=hashlib.sha256((P/'boundary_implications_02.json').read_bytes()).hexdigest())
with (P/'owner_dependent_values_approval.json').open('x', encoding='utf-8') as f:
    json.dump(approval, f, indent=2)
text = review.read_text(encoding='utf-8')
text = text.replace('# S3g dependent values at unsigned boundaries',
    '# S3g dependent values at unsigned boundaries\n\n**Owner approved on 2026-10-23:** “Approve dependent values and offline work”\n(`call_43d1f40d2efb4ab69d699df590f3c0bc:0`).', 1)
review.write_text(text, encoding='utf-8')
v2 = AB/'AB_FROZEN_CONTRACTS_V2.json'
data = json.loads(v2.read_text())
m = data['approvedMetricsCorrection']
m.update(dependentValuesApproved=True, dependentValuePaths=224,
    dependentValuesApprovalQuestion=approval['questionId'], dependentValuesAnswer=approval['answer'],
    totalAffectedPaths=424, controllerChangesAuthorized=False)
m.pop('pendingDependentValuePaths', None)
v2.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md', 'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_S3G_NOTES_2026-10-23.md'):
    path = AB/name
    text = path.read_text(encoding='utf-8')
    text = text.replace("are pending the owner's decision. The default generator refuses stage 9 until\nthat contract and the complete algorithms pass.",
        'were approved by the owner on 2026-10-23 (question\n`call_43d1f40d2efb4ab69d699df590f3c0bc:0`). The combined finite allowance is\n424 paths: 200 numeric types and 224 dependent values. Full algorithms and\nall complete-image gates remain required before deployment.')
    text = text.replace('The 200 type paths are approved. The 224 dependent value paths remain pending;',
        'The 200 type paths and 224 dependent value paths are approved for offline work;')
    if name.startswith('AB_CANONICAL_PUBLICATION_PLAN'):
        needle = 'on 2026-10-23, including exact Core Float32 arithmetic and UInt32 bucket wrap.'
        assert needle in text
        text = text.replace(needle, needle+' The\n   [224 dependent value paths](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md)\n   are also approved: 64 OEE validity flags and 160 profiler row values.', 1)
    path.write_text(text, encoding='utf-8')
print(json.dumps(approval))

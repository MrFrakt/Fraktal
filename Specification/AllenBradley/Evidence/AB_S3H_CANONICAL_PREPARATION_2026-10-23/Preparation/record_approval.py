from pathlib import Path
import datetime, hashlib, json, shutil

P=Path(__file__).parent
AB=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
review=AB/'AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md'
inventory=AB/'AB_CANONICAL_PUBLICATION_S3H_INVENTORY_2026-10-23.json'
approval=dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    questionId='call_f7da50b3655c43e4be6d7145b8b02c9b:0',
    answer='Approve S3h corrections and offline work',
    scope='36 enumerated Core type corrections and unset Part stamp empty string to zero; other 242 added paths exact; dependent offline work only',
    controllerChangesAuthorized=False,
    reviewSha256=hashlib.sha256(review.read_bytes()).hexdigest(),
    inventorySha256=hashlib.sha256(inventory.read_bytes()).hexdigest())
with (P/'owner_contract_approval.json').open('x',encoding='utf-8') as f:json.dump(approval,f,indent=2)
shutil.copyfile('C:/work/fraktal-ab-s3g-20261023/prepare_feb76c7a0968442293ee0d20b812eb17/run_logged.py',P/'run_logged.py')
v2=AB/'AB_FROZEN_CONTRACTS_V2.json'
data=json.loads(v2.read_text())
assert not data['active'] and data['approvedMetricsCorrection']['runtimeAccepted']
data['approvedTraceabilityCorrection']=dict(stage='S3h',approvalQuestion=approval['questionId'],
    answer=approval['answer'],scope=approval['scope'],contractReview=review.name,
    enumeratedInventory=inventory.name,typeCorrections=36,
    typeChangeCounts={'Int32->UInt32':16,'Int32->Int16':3,'String->DateTime':17},
    unsetPartStamp={'before':'','after':0},unchangedAddedPaths=242,
    runtimeAccepted=False,controllerChangesAuthorized=False)
v2.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
text=review.read_text(encoding='utf-8')
assert '**Owner decision pending.**' in text
text=text.replace('**Owner decision pending.**',
    '**Owner approved on 2026-10-23:** “Approve S3h corrections and offline work”\n(`'+approval['questionId']+'`).',1)
review.write_text(text,encoding='utf-8')
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md'):
    path=AB/name;text=path.read_text(encoding='utf-8')
    text=text.replace('No S3h implementation or exception is approved; stage 10 generation remains\nrefused.',
        'The owner approved these finite corrections and dependent offline work on\n2026-10-23 (`'+approval['questionId']+'`). S3h implementation is in progress;\nno S3h controller-changing operation is authorized.',1)
    if name.startswith('AB_CANONICAL_PUBLICATION_PLAN'):
        needle='   numeric coercion, ignored path or tolerance is permitted.'
        assert needle in text
        text=text.replace(needle,needle+' The owner also approved\n   the [36 S3h type corrections](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md),\n   including unset Part timestamp empty string to zero; the other 242 added paths\n   retain exact values and types.',1)
    path.write_text(text,encoding='utf-8')
notes=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md'
text=notes.read_text(encoding='utf-8').replace('S3h has only an offline inventory/review.\nNo S3h implementation, contract exception, image or controller operation is\nauthorized by the completed S3g session.',
    'The owner approved the 36 S3h corrections and dependent offline work on\n2026-10-23 (`'+approval['questionId']+'`). Implementation is in progress.\nAn exact S3h image and session still need their own gates and authorization.',1)
notes.write_text(text,encoding='utf-8')
print(json.dumps(approval))

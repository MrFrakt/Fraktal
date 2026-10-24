from pathlib import Path
import datetime,hashlib,json,shutil
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley'
review=AB/'AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md';inventory=AB/'AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
approval=dict(date='2026-10-23',capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),questionId='call_98e771c35eec48548b860bd7ad211932:0',answer='Approve S3g corrections and offline work',scope='200 enumerated Core numeric corrections including exact Float32 arithmetic and UInt32 bucket wrap; contract and offline work only',controllerChangesAuthorized=False,reviewSha256=sha(review.read_bytes()),inventorySha256=sha(inventory.read_bytes()))
with (P/'owner_contract_approval.json').open('x') as f:json.dump(approval,f,indent=2)
shutil.copyfile('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009/run_logged.py',P/'run_logged.py')
data=json.loads((AB/'AB_FROZEN_CONTRACTS_V2.json').read_text());assert not data['active'] and data['approvedConfigurationCorrection']['runtimeAccepted']
data['approvedMetricsCorrection']=dict(stage='S3g',approvalQuestion=approval['questionId'],answer=approval['answer'],scope=approval['scope'],contractReview=review.name,enumeratedInventory=inventory.name,typeCorrections=200,typeChangeCounts={'Double->Float':64,'Int32->UInt32':101,'Int32->Int16':35},runtimeAccepted=False,controllerChangesAuthorized=False)
(AB/'AB_FROZEN_CONTRACTS_V2.json').write_text(json.dumps(data,indent=2)+'\n')
text=review.read_text(encoding='utf-8');text=text.replace('**Owner decision pending.**','**Owner approved on 2026-10-23:** “Approve S3g corrections and offline work”\n(`call_98e771c35eec48548b860bd7ad211932:0`).',1).replace('The current approved allow-list remains unchanged.','The finite 200-path amendment is approved for offline implementation; no\ncontroller-changing operation is authorized.',1);review.write_text(text,encoding='utf-8')
plan=AB/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=plan.read_text(encoding='utf-8');text=text.replace('the 110 enumerated Core types, bounded page windows, 12 missing Core fields,','the 110 enumerated Core types, bounded page windows, 12 missing Core fields,',1)
needle='   PLC-owned revision/timestamps and validated provider responses.'
assert needle in text
text=text.replace(needle,needle+' The owner also\n   approved the [200 S3g numeric corrections](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)\n   on 2026-10-23, including exact Core Float32 arithmetic and UInt32 bucket wrap.',1)
text=text.replace('is prepared for owner approval. No S3g implementation, acceptance-rule amendment\nor controller operation has run; the existing finite allow-list stays unchanged.','was approved by the owner for contract/offline work on 2026-10-23. S3g\nimplementation is now in progress. No S3g controller operation is authorized.',1);plan.write_text(text,encoding='utf-8')
handover=AB/'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md';text=handover.read_text(encoding='utf-8').replace('is prepared for owner approval. No S3g implementation, acceptance-rule amendment\nor controller operation has run; the existing finite allow-list stays unchanged.','was approved by the owner for contract/offline work on 2026-10-23. S3g\nimplementation is now in progress. No S3g controller operation is authorized.',1);handover.write_text(text,encoding='utf-8')
print(json.dumps(approval))

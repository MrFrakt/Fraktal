from pathlib import Path
import hashlib,json
BASE=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
catalog=BASE/'AB_CAPACITY_OBSERVATIONS_2026-10-21.json';d=json.loads(catalog.read_text())
assert len(d['samples'])==6 and d['samples'][-1]['label']=='S3d'
source='Evidence/AB_S3E_CANONICAL_PREPARATION_2026-10-22/Preparation/genealogy_s3e_01.L5X.gz'
receipt='Evidence/AB_S3E_CANONICAL_PREPARATION_2026-10-22/Preparation/capacity_review.json'
d['samples'].append(dict(label='S3e',source=source,sourceSha256='3bffceadb98ec7b7b7aa05550202cc187c736a8c2b22c75b7b7d158be4f5ad87',capacity=receipt,capacitySha256=hashlib.sha256((BASE/receipt).read_bytes()).hexdigest(),acdSha256='95E85B507387A548553688C1B5CCF52D7D99B35751C68F1B02DE92AC2A1B240B'))
catalog.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(passed=True,samples=7,addedAfterCandidateAndBaselineAcceptance=True)))

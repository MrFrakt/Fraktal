from pathlib import Path
import gzip,hashlib,json
P=Path(__file__).parent;E=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence')
sha=lambda raw:hashlib.sha256(raw).hexdigest();seals=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
    record=json.loads(path.read_text())
    for item in record['artifacts']:
        raw=(path.parent/item['path']).read_bytes()
        assert len(raw)==item['bytes'] and sha(raw)==item['sha256'].lower(),(path,item['path'])
        if item.get('expandedSha256'):assert sha(gzip.decompress(raw))==item['expandedSha256'].lower()
    if record.get('report'):assert sha((E/record['report']).read_bytes())==record['reportSha256'].lower()
    seals.append(dict(name=path.parent.name,artifacts=len(record['artifacts']),manifestSha256=sha(path.read_bytes())))
assert len(seals)==27 and sum(s['artifacts'] for s in seals)==6251
report=dict(passed=True,predecessorRecords=27,predecessorArtifacts=6251,priorSeals=seals)
with (P/'predecessor_seals_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='priorSeals'}))

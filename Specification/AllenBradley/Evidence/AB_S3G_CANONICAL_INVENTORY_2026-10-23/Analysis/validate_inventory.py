from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');G=Path(__file__).parent;BASE=ROOT/'Specification/AllenBradley/Evidence'
R=Path('C:/work/fraktal-ab-s3f-revision-20261023/runtime_9b86612c2f174292a2773260021df32d');sha=lambda raw:hashlib.sha256(raw).hexdigest()
first=json.loads((G/'inventory_01.json').read_text());current=json.loads((G/'inventory_02.json').read_text())
for key in ('paths','surfaceCounts','proposedTypeChangeCounts','sourceProjectionExpandedSha256'):assert first[key]==current[key],key
assert current['addedLegacyPaths']==1055 and current['proposedTypeChanges']==200 and not current['approvedAllowListChanged']
assert sha((G/'inventory_02.json').read_bytes())==sha((ROOT/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json').read_bytes())
for name,bound in current['sourceBindings'].items():assert sha((ROOT/name).read_bytes())==bound['sha256'],name
ab=json.loads((R/'source_verification_02.json').read_text());assert ab['sourceBindings']==143
for name,pin in ab['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
prior=json.loads((R/'opening_verification_01.json').read_text())['seals']
path=BASE/'AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23/manifest.json';m=json.loads(path.read_text())
prior.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path.read_bytes())))
assert len(prior)==22 and sum(r['artifacts'] for r in prior)==4849
for row in prior:
 path=BASE/row['name']/'manifest.json';assert sha(path.read_bytes())==row['manifestSha256'];m=json.loads(path.read_text())
 for a in m['artifacts']:
  raw=(path.parent/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256'].lower()
  if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'].lower()
 if m.get('report'):assert sha((BASE/m['report']).read_bytes())==m['reportSha256'].lower()
result=dict(passed=True,controllerAccess=False,controllerWrites=0,productionSourceChanges=False,acceptanceRulesChanged=False,paths=1055,typeCorrectionsProposed=200,currentAbSourceBindings=143,sourceBindings=current['sourceBindings'],currentAbSources=ab['sha256'],priorSeals=prior,predecessorRecords=22,predecessorArtifacts=4849,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (G/'validation_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('sourceBindings','currentAbSources','priorSeals')}))

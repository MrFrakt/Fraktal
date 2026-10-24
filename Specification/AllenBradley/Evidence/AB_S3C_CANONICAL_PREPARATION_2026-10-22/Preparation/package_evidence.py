"""Append-only S3c preparation seal; no credentials or ACDs archived."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
BASE=ROOT/'Specification/AllenBradley/Evidence';NAME='AB_S3C_CANONICAL_PREPARATION_2026-10-22';DEST=BASE/NAME;REPORT=BASE/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
verify=json.loads((W/'preparation_verification_01.json').read_text());assert verify['passed'] and verify['controllerChanges']==0
binding=json.loads((W/'source_bindings_01.json').read_text())
for file,pin in binding['sha256'].items():assert sha((ROOT/file).read_bytes())==pin,file
assert sha((W/'s3c_canonical.ACD').read_bytes()).upper()==verify['preparedAcdSha256']
assert sha((W/'capacity_review.ACD').read_bytes()).upper()==verify['preparedAcdSha256']
assert not any((W/file).exists() for file in ('authorization.json','backup.sha256','deploy_attempt.json','preflight.json','echo_before_s3c.ACD'))
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').read_bytes()).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
DEST.mkdir()
def put(relative,raw):
 file=DEST/relative;file.parent.mkdir(parents=True,exist_ok=True)
 with file.open('xb') as stream:stream.write(raw)
for file in sorted(W.rglob('*')):
 if not file.is_file() or any(p in ('bin','obj','__pycache__') for p in file.parts):continue
 if '.acd' in file.name.lower() or 'credential' in file.name.lower():continue
 if file.suffix.lower() not in {'.py','.ps1','.cs','.csproj','.config','.json','.sha256','.md','.log','.gz','.l5x','.txt'}:continue
 name='Preparation/'+file.relative_to(W).as_posix();raw=file.read_bytes()
 if file.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
 put(name,raw)
for file in binding['sha256']:put('Source/'+file,(ROOT/file).read_bytes())
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json','AB_CANONICAL_PUBLICATION_S3C_NOTES_2026-10-22.md','AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md','AB_CANONICAL_PUBLICATION_S3C_INVENTORY_2026-10-22.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json','AB_CAPACITY_FORECAST_METHOD_2026-10-21.md'):
 put('Target/'+name,(BASE.parent/name).read_bytes())
put('Reference/echo38_5580_seed.L5X.gz',gzip.compress(Path('C:/work/echo38_5580_seed.L5X').read_bytes(),mtime=0))
artifacts=[]
for file in sorted(DEST.rglob('*')):
 if not file.is_file():continue
 raw=file.read_bytes();row=dict(path=file.relative_to(DEST).as_posix(),bytes=len(raw),sha256=sha(raw))
 if file.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
 artifacts.append(row)
capacity=json.loads((W/'capacity_review.json').read_text())
manifest=dict(schema='fraktal.ab.s3c-canonical-preparation-evidence',schemaVersion=1,date='2026-10-22',timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),sourceCommit=binding['sourceCommit'],publicationStage='S3c',offlineGatesPassed=True,runtimeAccepted=False,controllerChanges=0,currentAuthorizationPending=True,manualNormalizationPending=True,preflightRecorded=False,preparedAcdSha256=verify['preparedAcdSha256'],generatedSourceSha256=verify['sourceSha256'],expectedPaths=647,fixtureEquipmentModules=0,fixtureConcurrentLegs=0,capacityMeasured=True,capacityProvider=capacity['Provider'],usedStandardBlocks=capacity['UsedStandardBlocks'],availableBlocks=capacity['AvailableBlocks'],totalBlocks=capacity['TotalBlocks'],nativeAcdFilesArchived=False,credentialFilesArchived=False,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(r['bytes'] for r in artifacts),priorSeals=json.loads((W/'prior_seals_verification_01.json').read_text())['rows'])
put('manifest.json',json.dumps(manifest,indent=2).encode())
for row in manifest['artifacts']:
 raw=(DEST/row['path']).read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
 if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256']
assert sha(REPORT.read_bytes())==manifest['reportSha256']
with (W/'seal_verification_01.json').open('x') as stream:json.dump(dict(passed=True,artifacts=len(artifacts),bytes=manifest['totalBytes'],reportSha256=manifest['reportSha256'],manifestSha256=sha((DEST/'manifest.json').read_bytes()),controllerChanges=0),stream,indent=2)
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),bytes=manifest['totalBytes'],reportSha256=manifest['reportSha256'])))

"""Seal the offline S3k slice, including failed attempts, without native binaries."""
from pathlib import Path
import datetime,gzip,hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;B=W.parent
E=R/'Specification/AllenBradley/Evidence'
NAME='AB_S3K_READ_SURFACES_OFFLINE_2026-10-25';OUT=E/NAME
assert not OUT.exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
def write_new(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
def save(p,v):write_new(p,(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode())
prior=json.loads((E/'AB_S3J_CANONICAL_RETRY_PREPARATION_2026-10-25/Preparation/source_bindings_01.json').read_bytes())
names=set(prior['sha256'])
names.update(p.relative_to(R).as_posix() for p in (R/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
names.update('Specification/AllenBradley/'+s for s in ['AB_CANONICAL_PUBLICATION_S3K_NOTES_2026-10-25.md','AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md'])
bindings={n:sha((R/n).read_bytes()) for n in sorted(names)}
save(W/'source_bindings_01.json',dict(passed=True,sha256=bindings,codeTestBinding='AB suite 02; no AB code modified after completion'))
gates=['ab_suite_02','root_tests_02','ab_spec_02','ab_contracts_02','consistency_02','whitespace_03','final_provenance_01',
 'native_EchoController_02','native_PhysicalController_02','readback_EchoController_03','readback_PhysicalController_03',
 'access_Echo_02','access_Physical_02','prepare_acd_01','prepared_compare_01','capacity_01','replay_prior_01','compatibility_01',
 'baseline_guard_01','baseline_preflight_01']
for label in gates:assert json.loads((W/(label+'_exit.json')).read_bytes())['exitCode']==0,label
for n in ('sdk_EchoController_02.json','sdk_PhysicalController_02.json','sdk_prepare_01.json'):
    assert json.loads((W/n).read_bytes())['Clean'],n
assert json.loads((W/'accepted_images_01.json').read_bytes())['images']==12
cap=json.loads((W/'capacity_auto_01.json').read_bytes())
provenance=json.loads((W/'final_provenance_01.json').read_bytes());assert provenance['passed']
assert provenance['priorSeals']==56 and provenance['priorArtifacts']==13256
artifacts=[]
def archive(src,relative,compress=False):
    raw=src.read_bytes(); data=gzip.compress(raw,mtime=0) if compress else raw
    rel=relative+('.gz' if compress else '')
    write_new(OUT/rel,data)
    row=dict(path=rel,bytes=len(data),sha256=sha(data))
    if compress:row['expandedSha256']=sha(raw)
    artifacts.append(row)
for group,label in [('inventory_01','Inventory'),('owner_01','Owner'),('r4_01','R4'),('read_surface_01','ReadSurface')]:
    for p in sorted((B/group).iterdir()):
        if not p.is_file():continue
        # Deliberate whitelist: no ACD/BAK, credentials, binaries or arbitrary host files.
        if p.suffix.lower() not in ('.py','.json','.log','.l5x','.md'):continue
        assert not ('credential' in p.name.lower() and p.name.lower().endswith('.json')),p
        archive(p,label+'/'+p.name,p.suffix.lower()=='.l5x')
for n in bindings:archive(R/n,'Source/'+n,True)
report=E/(NAME+'.md')
manifest=dict(schema='fraktal.ab.s3k-read-surfaces-offline',schemaVersion=1,date='2026-10-25',timeZone='America/Mexico_City',
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=report.name,reportSha256=sha(report.read_bytes()),
 status='offline-read-surfaces-r4-pass-command-binding-choice-pending',nativeAccepted=False,
 semanticApproval='call_2e1575c86f2947c59925e347cd3d0109:0',controllerChangesAuthorized=False,controllerOperationsPerformed=0,
 sourceSha256=provenance['pins']['s3k_read_surface_02.L5X'],offlineAcdSha256=provenance['pins']['read_surface_01.ACD'],
 readPaths=133,fullCommandBindingImplemented=False,commandBindingChoicePending=True,sourceBindings=len(bindings),
 abTests=2264,rootTests=74,acceptedImagesByteIdentical=12,priorCapturesReplayed=1385,
 nativeBuildTargets=['EchoController','PhysicalController'],scanMeasured=False,
 capacity={k:cap[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent')},
 priorSeals=json.loads((W/'prior_seals_01.json').read_bytes())['rows'],
 documentationUpdates=json.loads((W/'documentation_updates_02.json').read_bytes()),
 artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),
 credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
save(OUT/'manifest.json',manifest)
# Verify every new compressed/raw artifact and every current source binding before reporting.
for a in artifacts:
    raw=(OUT/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256']
    if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256']
for n,pin in bindings.items():assert sha((R/n).read_bytes())==pin,n
assert sha(report.read_bytes())==manifest['reportSha256']
summary=dict(passed=True,manifest=str(OUT/'manifest.json'),manifestSha256=sha((OUT/'manifest.json').read_bytes()),
 artifacts=len(artifacts),sourceBindings=len(bindings),totalBytes=manifest['totalBytes'],priorSeals=56,priorArtifacts=13256,
 nativeAccepted=False,controllerOperationsPerformed=0)
save(W/'sealed_01.json',summary)
print(json.dumps(summary))

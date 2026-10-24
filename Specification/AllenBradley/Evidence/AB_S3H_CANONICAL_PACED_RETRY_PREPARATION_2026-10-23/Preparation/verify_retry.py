from pathlib import Path
import datetime,gzip,hashlib,json,re
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;W=P.parent/'transport_ae4489870e334fefaf4d7d28580708cc';E=ROOT/'Specification/AllenBradley/Evidence'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for directory,labels in ((W,('ab_suite_01','paced_tests_01','four_paced_proxy_01')),
    (P,('helper_build_02','source_bindings_01','exact_image_readback_01','exact_access_01','preflight_readonly_01','final_readonly_01',
        'scan_start_proxy_01','finalize_retry_documents_01','root_tests_02','ab_spec_02','ab_contracts_02','consistency_02','whitespace_02'))):
    for label in labels:assert json.loads((directory/(label+'_exit.json')).read_text())['exitCode']==0,label
found=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(W/'ab_suite_01.log').read_text());assert found and int(found[1])==2149
bindings=json.loads((P/'source_bindings_01.json').read_text());assert bindings['sourceBindings']==159
for name,pin in bindings['sha256'].items():assert sha(ROOT/name)==pin,name
pin=(P/'canonical.sha256').read_text().strip()
assert sha(P/'s3h_canonical.ACD').upper()==sha(P/'capacity_review.ACD').upper()==pin=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
assert sha(P/'s3h_candidate_03.L5X')==sha(P/'s3h_regenerated_paced_01.L5X')=='e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315'
ref=json.loads((P/'prepared_image_reference.json').read_text())
for key in ('capacityEvidence','nativeBuildEvidence'):assert sha(ROOT/'Specification/AllenBradley'/ref[key])==ref[key+'Sha256']
cap=json.loads((P/'capacity_review.json').read_text());assert cap['VerifiedFit'] and cap['Measured'] and cap['CanonicalSha256']==pin
assert (cap['UsedStandardBlocks'],cap['AvailableBlocks'],cap['TotalBlocks'])==(2501720,644008,3145728)
assert json.loads((P/'exact_image_readback_01.log').read_text())['Equivalent']
assert json.loads((P/'exact_access_01.json').read_text())['passed']
proxy=json.loads((P/'scan_start_proxy_01.json').read_text());assert proxy['passed'] and len(proxy['samples'])==1000
assert proxy['attemptsObserved']['maximum']<=100 and proxy['attemptsLimit']==100 and proxy['secondsLimit']==5
assert not proxy['canonicalS3hAcceptance'] and proxy['controllerWrites']==0
for name in ('authorization.json','deploy_attempt.json','backup.sha256','canonical_downloaded.L5X','genealogy_restored.L5X'):assert not (P/name).exists()
assert not json.loads((P/'authorization.template.json').read_text())['CurrentOwnerApproved']
assert json.loads((P/'final_readonly_01.json').read_text())['passed']
seals=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
    m=json.loads(path.read_text())
    for item in m['artifacts']:
        raw=(path.parent/item['path']).read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'].lower()
        if item.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['expandedSha256'].lower()
    if m.get('report'):assert sha(E/m['report'])==m['reportSha256'].lower()
    seals.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(seals)==31 and sum(r['artifacts'] for r in seals)==7480
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),retryReady=True,currentOwnerApprovalPending=True,
    controllerChanges=0,stageAccepted=False,preparedAcdSha256=pin,sourceSha256=sha(P/'s3h_candidate_03.L5X'),
    sourceBindings=159,sha256=bindings['sha256'],abTests=2149,abSeconds=float(found[2]),rootTests=74,
    imageAndNativeBuildAndCapacityUnchanged=True,unchangedEvenWaitSeconds=.001,capacityBlocks=2501720,availableBlocks=644008,totalBlocks=3145728,
    connections=4,maximumOutstandingPerConnection=1,attemptLimit=100,secondsLimit=5.0,allWaitingPollsCounted=True,
    qualifiedBaselineProxyCaptures=1000,canonicalS3hRetryNotExecuted=True,plannedCandidateRows=41,plannedBaselineRows=31,
    sessionExecutableSha256=sha(P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe'),sessionSourceSha256=sha(P/'session/Program.cs'),
    predecessorRecords=31,predecessorArtifacts=7480,priorSeals=seals)
with (P/'retry_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('sha256','priorSeals')}))

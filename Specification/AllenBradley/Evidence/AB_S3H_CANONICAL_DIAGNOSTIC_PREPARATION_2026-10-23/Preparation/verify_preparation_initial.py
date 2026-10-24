from pathlib import Path
import datetime,gzip,hashlib,json,re
P=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for label in ('helper_build_01','diagnostic_tests_02','preflight_readonly_01','exact_image_readback_01','exact_access_01',
 'final_readonly_01','record_preparation_01','root_tests_01','ab_spec_01','ab_contracts_01','consistency_01','whitespace_01'):
 assert json.loads((P/(label+'_exit.json')).read_text())['exitCode']==0,label
assert re.search(r'Ran 4 tests in [\d.]+s\s+OK',(P/'diagnostic_tests_02.log').read_text())
bindings=json.loads((P/'source_bindings_01.json').read_text());assert len(bindings['sha256'])==159
for n,pin in bindings['sha256'].items():assert sha(ROOT/n)==pin,n
for n,pin in bindings['diagnostics'].items():assert sha(P/n)==pin,n
old=P.parent/'retry_fc306d330cc642499a52abbb53bae945'
v=json.loads((old/'retry_verification_01.json').read_text());assert v['sha256']==bindings['sha256'] and v['abTests']==2149
assert sha(P/'s3h_canonical.ACD').upper()==sha(P/'capacity_review.ACD').upper()==v['preparedAcdSha256']
assert sha(P/'s3h_candidate_03.L5X')==v['sourceSha256']
assert json.loads((P/'exact_image_readback_01.log').read_text())['Equivalent']
assert json.loads((P/'exact_access_01.json').read_text())['passed']
assert json.loads((P/'final_readonly_01.json').read_text())['passed']
approval=json.loads((P/'authorization.template.json').read_text())
assert not any(approval[k] for k in ('CurrentOwnerApproved','ReadTimingDiagnosticsAuthorized','FaultClearAuthorized','ClockSetAuthorized'))
for n in ('authorization.json','deploy_attempt.json','backup.sha256','canonical_downloaded.L5X','genealogy_restored.L5X'):
 assert not (P/n).exists(),n
seals=[]
for path in sorted(E.glob('AB_*/manifest.json')):
 if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL',
  'AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
 m=json.loads(path.read_text())
 for item in m['artifacts']:
  raw=(path.parent/item['path']).read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'].lower()
  if item.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['expandedSha256'].lower()
 assert sha(E/m['report'])==m['reportSha256'].lower()
 seals.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(seals)==33 and sum(r['artifacts'] for r in seals)==8072
result=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),diagnosticReady=True,
 currentOwnerApprovalPending=True,controllerChanges=0,stageAccepted=False,projectSourcesUnchanged=True,
 sourceBindings=159,sha256=bindings['sha256'],diagnosticBindings=bindings['diagnostics'],diagnosticWrapperTests=4,
 abTests=2149,abSeconds=v['abSeconds'],rootTests=74,preparedAcdSha256=v['preparedAcdSha256'],sourceSha256=v['sourceSha256'],
 sessionExecutableSha256=sha(P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe'),sessionSourceSha256=sha(P/'session/Program.cs'),
 capacityBlocks=2501720,availableBlocks=644008,totalBlocks=3145728,capacityReusedByExactImageHash=True,
 plannedCandidateRows=41,plannedBaselineRows=31,additionalControllerWrites=0,postFailureTaskScalars=8,
 connections=4,maximumOutstandingPerConnection=1,attemptLimit=100,secondsLimit=5,
 priorSeals=seals,predecessorRecords=33,predecessorArtifacts=8072)
with (P/'diagnostic_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:x for k,x in result.items() if k not in ('sha256','priorSeals')}))

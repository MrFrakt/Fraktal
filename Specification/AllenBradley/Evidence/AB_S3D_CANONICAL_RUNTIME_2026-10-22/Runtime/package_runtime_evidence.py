from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3d-20261022/prepare_f1995b2579fe4f7a9d15d02dd8ed53e9')
BASE=ROOT/'Specification/AllenBradley/Evidence';NAME='AB_S3D_CANONICAL_RUNTIME_2026-10-22'
DEST=BASE/NAME;REPORT=BASE/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((R/'runtime_verification_01.json').read_text());assert v['passed'] and v['sessionComplete']
for name in v['requiredSuccessfulRuns']:assert json.loads((R/(name+'_exit.json')).read_text())['exitCode']==0,name
bindings=json.loads((R/'source_bindings_runtime_01.json').read_text())
for name,pin in bindings['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').read_bytes()).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert json.loads((R/'session_completed.json').read_text())['currentAuthorizationConsumed']
assert not DEST.exists();DEST.mkdir()
def put(relative,raw):
 p=DEST/relative;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def archive(relative,p):
 if '.acd' in p.name.lower() or 'credential' in p.name.lower():raise ValueError('forbidden evidence filename')
 raw=p.read_bytes()
 if p.suffix.lower()=='.l5x':relative+='.gz';raw=gzip.compress(raw,mtime=0)
 put(relative,raw)
for p in sorted(R.rglob('*')):
 if not p.is_file() or any(x in ('bin','obj','__pycache__') for x in p.parts):continue
 if p.name.startswith('package_01') or p.name.startswith('seal_verification_'):continue
 if '.acd' in p.name.lower() or 'credential' in p.name.lower():continue
 if p.suffix.lower() not in {'.py','.ps1','.cs','.csproj','.config','.json','.sha256','.md','.log','.gz','.l5x','.txt'}:continue
 archive('Runtime/'+p.relative_to(R).as_posix(),p)
session=('authorization.json','preflight.json','backup.sha256','canonical.sha256','deploy_attempt.json','capacity_review.json','baseline_capacity.json','baseline_reference.json','canonical_prepared_compare.json','native_summary_final.json','source_bindings_01.json','session_completed.json','echo_before_s3d.L5X','canonical_downloaded.L5X','genealogy_restored.L5X','session/Program.cs','session/S3dSession.csproj','session/NuGet.Config','scripts/guard_echo.py','scripts/preflight.py','ensure_manual.py','final_checks.py','measure_timing.py','verify_runtime_acceptance.py','RUNBOOK.md')
for name in session:archive('Session/'+name,W/name)
for name in bindings['sha256']:put('Source/'+name,(ROOT/name).read_bytes())
documents=('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json','AB_CANONICAL_PUBLICATION_S3D_NOTES_2026-10-22.md','AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md','AB_CANONICAL_PUBLICATION_S3D_INVENTORY_2026-10-22.json','AB_CAPACITY_FORECAST_METHOD_2026-10-21.md','AB_CAPACITY_OBSERVATIONS_2026-10-21.json')
for name in documents:put('Target/'+name,(BASE.parent/name).read_bytes())
artifacts=[]
for p in sorted(DEST.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();row=dict(path=p.relative_to(DEST).as_posix(),bytes=len(raw),sha256=sha(raw))
 if p.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
 artifacts.append(row)
prior=json.loads((R/'prior_seals_verification_01.json').read_text());assert prior['records']==14 and prior['artifacts']==2258
cap=json.loads((W/'capacity_review.json').read_text())
manifest=dict(schema='fraktal.ab.s3d-canonical-runtime-evidence',schemaVersion=1,date='2026-10-22',timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),sourceCommit=bindings['sourceCommit'],publicationStage='S3d',runtimeAccepted=True,acceptedScope='2125 genealogy paths; no EM/concurrent fixture; WAIT_RESET not runtime-observed',preparedAcdSha256=v['originalCandidatePin'],sdkSavedCandidateSha256=v['sdkSavedCandidateSha256'],generatedSourceSha256=sha((W/'genealogy_s3d_01.L5X').read_bytes()),backupSha256=v['backupSha256'],currentAuthorizationConsumed=True,expectedPaths=2125,candidateRegressionRows=31,baselineRegressionRows=31,actualRecordedRegressionRows=96,extraRecordedRegressionRows=34,failedFixtureRowCounts=[8,26],decisionCaptures=4,conditionCaptures=14,sequenceCaptures=21,resetCaptures=8,resetBeforeAfterPairs=4,pairedCapturesIncludingIdle=48,sameScanAttempts=v['sameScanAttempts'],readOnlyAcquisitionConnections=2,metadataCoherence=v['metadataCoherence'],activeStatesObserved=[0,1],waitResetObserved=False,ringWrapObserved=True,manualNormalizations=2,additionalMailboxCommands=6,perTagWriteCallCountMeasured=False,failedRuns=v['failedRuns'],unchangedPreparedSourceFiles=68,changedReadOnlyHarnessFiles=2,plcSourcesUnchanged=True,abSuite=v['abSuite'],rootSuite=v['rootSuite'],capacityMeasured=True,capacityProvider=cap['Provider'],usedStandardBlocks=cap['UsedStandardBlocks'],availableBlocks=cap['AvailableBlocks'],totalBlocks=cap['TotalBlocks'],nativeRecords=v['nativeRecords'],totalNativePayloadBytes=v['totalNativePayloadBytes'],candidateTiming=v['candidateTiming'],baselineTiming=v['baselineTiming'],finalChecksPassed=True,finalManualOrdinal=1,nativeAcdFilesArchived=False,credentialFilesArchived=False,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),priorSeals=prior['rows'])
put('manifest.json',json.dumps(manifest,indent=2).encode())
for a in artifacts:
 raw=(DEST/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256'],a['path']
 if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'],a['path']
assert sha(REPORT.read_bytes())==manifest['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=manifest['totalBytes'],reportSha256=manifest['reportSha256'],manifestSha256=sha((DEST/'manifest.json').read_bytes()),predecessorRecords=prior['records'],predecessorArtifacts=prior['artifacts'],runtimeAccepted=True,currentAuthorizationConsumed=True)
with (R/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))

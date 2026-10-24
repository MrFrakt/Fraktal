from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;P=R.parent/'prepare_5822102a73e348ec95ff7082959ef940'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
required=('backup_01','backup_log_audit_01','backup_access_01','deploy_01','deploy_log_audit_01','deploy_readback_01',
    'deploy_access_01','restore_genealogy_01','restore_log_audit_01','restore_access_01','baseline_regressions_01',
    'manual_final_01','final_checks_01','preflight_final_01','baseline_timing_01','tooling_validation_01')
for label in required:assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
session=json.loads((R/'session_execution_01.json').read_text());assert not session['passed'] and session['restoreError'] is None
fixture=json.loads((R/'candidate_regressions_01.json').read_text());baseline=json.loads((R/'baseline_regressions_01.json').read_text())
assert fixture['restored'] and fixture['policyRestored'] and fixture['error']=='configuration equivalence failed'
assert len(baseline['rows'])==31 and all(r['passed'] for r in baseline['rows']) and baseline['restored'] and baseline['policyRestored']
assert json.loads((R/'final_checks_01.json').read_text())['passed']
inspection=json.loads((R/'acquisition_inspection_01.json').read_text())['rows']
passed=[r for r in inspection if r['passed']];failed=[r for r in inspection if not r['passed']]
assert len(passed)==10 and len(failed)==1 and failed[0]['attempts']==100
assert failed[0]['error']=='no completed PLC scan held across the paired read window'
inputs=json.loads((R/'tooling_validation_01.json').read_text())
for name,pin in inputs['sha256'].items():assert sha(ROOT/name)==pin,name
with (R/'source_verification_failed_01.json').open('x') as f:json.dump(dict(passed=True,sourceBindings=157,changedDuringNativeSession=[],
    correctedBeforeDownload=inputs['changedFromPreparation'],sha256=inputs['sha256']),f,indent=2)
source=ROOT/'Specification/AllenBradley/Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21/Reference/genealogy_current.L5X.gz'
raw=gzip.decompress(source.read_bytes());assert hashlib.sha256(raw).hexdigest()=='91bf67c9101eae863cf29c1a9df6413d7256ab056d985394587f0183aa525714'
with (R/'genealogy_reference.L5X').open('xb') as f:f.write(raw)
records=json.loads(gzip.decompress((R/passed[0]['file']).read_bytes()))['pair']['capture']['records']
sizes=[dict(tag=r['tag'],bytes=len(bytes.fromhex(r['rawHex']))) for r in records]
report=dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stageAccepted=False,
    sessionStoppedAtCoherenceGate=True,candidateRows=len(fixture['rows']),accessRows=len(fixture.get('s3hAccessRows',[])),
    configurationRows=len(fixture.get('s3hConfigRows',[])),passingPairs=10,failedPairs=1,failedCapture=failed[0],
    noObservedValueOrTypeMismatch=True,unchangedCoherenceGate=dict(attempts=100,seconds=5,connections=4),
    packetRequestsPerPassingPair=47,fragmentPackets=42,batchPackets=5,
    nativeRecordBytes=sizes,totalNativeBytes=sum(r['bytes'] for r in sizes),
    baselineRows=31,baselineRestored=True,finalGenealogyReady=True,authorizationConsumed=True,
    preparedAcdSha256=inputs['preparedAcdSha256'],sdkSavedAcdSha256=sha(P/'s3h_canonical.ACD').upper(),
    backupAcdSha256=sha(P/'echo_before_s3h.ACD').upper(),sourceSha256=inputs['preparedSourceSha256'],
    sourceBindings=157,correctedBeforeDownload=inputs['changedFromPreparation'],abTests=2140,rootTests=74,focusedTests=13,
    missingGates=['41 complete candidate checks','full-ring/Part lifecycle coverage','final generic/idle read and 20-sample candidate scan','successful complete native session'],
    faultClears=0,clockChanges=0)
with (R/'failed_session_closure_01.json').open('x') as f:json.dump(report,f,indent=2)
with (R/'authorization_consumed_failed_01.json').open('x') as f:json.dump(dict(consumed=True,
    approvalQuestion='call_ee9b48ca64a744a5a7221f84bf3615a1:0',capturedUtc=report['capturedUtc'],
    reason='Exact S3h attempt ended at coherence gate; genealogy rollback and baseline checks completed',
    furtherControllerChangesAuthorized=False),f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('correctedBeforeDownload','failedCapture')}))

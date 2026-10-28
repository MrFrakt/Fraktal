"""Seal actual S4b reader results after verified rollback; never changes Echo."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import statistics

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
D = W.parent / 'retry_reader_01'
E = R / 'Specification/AllenBradley/Evidence'
load = lambda p: json.loads(gzip.decompress(p.read_bytes())) if p.suffix == '.gz' else json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

session = load(D / 'session_result.json')
cases = load(D / 'candidate_regressions.json')
baseline = load(D / 'baseline_regressions.json')
final = load(D / 'final_checks.json')
dart = load(D / 'dart_qualification.json.gz')
replay = load(D / 'paired_replay_01.json')
inspection = load(D / 'runtime_inspection_01.json')
assert session['genealogyRestored'] and session['rollbackError'] is None and session['authorizationConsumed']
assert not session['dumpFiles'] and all(session[k] == 0 for k in ('faultClears','clockChanges','powerOperations','hardKills'))
for key, count in (('rows',31), ('s4bAccessRows',2), ('s4bConfigRows',8)):
    assert len(cases[key]) == count and all(row['passed'] for row in cases[key])
assert cases['restored'] and cases['policyRestored'] and cases['s3fSetMediumEmpty']
assert len(baseline['rows']) == 31 and all(row['passed'] for row in baseline['rows'])
assert baseline['restored'] and baseline['policyRestored']
assert final['passed'] and all(final['checks'].values()) and all(final['savedDocumentsEqual'].values())
assert replay['passed'] and replay['pairs'] == 87
bindings = load(D / 'source_bindings.json')['sha256']
changed = [name for name,pin in bindings.items() if sha(Path(name)).upper() != pin.upper()]
assert changed == [(D / 's4b_read_view.ACD').as_posix()], changed
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper() == 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
stages = {p.name.removesuffix('_exit.json'): load(p)['exitCode'] for p in D.glob('*_exit.json')}
functional = session['passed'] and dart['passed']
native = None
if functional:
    idle = load(D / 'idle_equivalence.json.gz')
    generic = load(D / 'generic_snapshot.json.gz')
    config = load(D / 'configuration_page_comparison_01.json')
    timings = [row['values'] for row in load(D / 'candidate_timing.json')['samples']]
    native = dict(idlePaths=len(idle['pair']['canonical']['values']),
        idleDifferences=idle['comparison'].get('differences'),
        acquiredValues=len(generic['values']), acquiredModules=generic['moduleCount'],
        configurationPages=config['pages'], configurationScalarComparisons=config['scalarComparisons'],
        taskScanMedianUs=statistics.median(row['FRK_Press_HealthProbe.TaskLastScanUs'] for row in timings),
        taskScanCumulativeMaxUs=max(row['FRK_Press_HealthProbe.TaskMaxScanUs'] for row in timings),
        taskOverlaps=max(row['FRK_Press_HealthProbe.TaskOverlapCount'] for row in timings))
    assert idle['passed'] and idle['comparison']['equal'] and idle['comparison']['typeAcceptance']
    assert config['passed'] and config['pages'] == len(dart['configurationPages']) == 4
    assert all(code == 0 for code in stages.values()), stages
    assert all(row['bad'] == 0 and row['sampleAgeMs'] < 1000 and row['maximumAcceptedRowWindowUs'] < 10000 for row in dart['samples'])
else:
    failed = {'qualification_run_01', 'candidate_regressions', 'dart_observer'}
    assert all(code == (1 if name in failed else 0) for name,code in stages.items()), stages

scan_passed = functional and native['taskOverlaps'] == 0 and native['taskScanCumulativeMaxUs'] < 10000
accepted = functional and scan_passed

baseline_timings = [row['values'] for row in load(D / 'baseline_timing.json')['samples']]
all_good = sum(row['bad'] == 0 and row['uncertain'] == 0 for row in dart['samples'])
uncertain = sum(row['uncertain'] > 0 for row in dart['samples'])
summary = dict(nativeAccepted=accepted, nativeReaderPassed=functional, scanReviewPassed=scan_passed,
    scanCauseConfirmed=False, desktopAccepted=False, serial='601FC87B',
    candidateCases=41, pairedCapturesReplayed=87, pairedMinimumPaths=replay['minimumPaths'],
    pairedMaximumPaths=replay['maximumPaths'], observerSamples=len(dart['samples']),
    observerPassed=dart['passed'], observerError=dart['error'], allGoodSamples=all_good,
    samplesWithUncertainRows=uncertain, samplesWithBadRows=sum(row['bad'] > 0 for row in dart['samples']),
    sampleAgeMs=inspection['sampleAgeMs'], rpcUs=inspection['rpcUs'],
    maximumAcceptedRowWindowUs=inspection['maximumAcceptedRowWindowUs'],
    configurationPages=len(dart['configurationPages']), nativeMeasurements=native,
    genealogyRestored=True, baselineCases=31, originalDocumentsRestored=5, finalChecksPassed=True,
    baselineScanMedianUs=statistics.median(row['FRK_Press_HealthProbe.TaskLastScanUs'] for row in baseline_timings),
    baselineScanCumulativeMaxUs=max(row['FRK_Press_HealthProbe.TaskMaxScanUs'] for row in baseline_timings),
    baselineOverlaps=max(row['FRK_Press_HealthProbe.TaskOverlapCount'] for row in baseline_timings),
    sourceBindingsVerified=len(bindings), sdkSavedWorkingAcdOnly=True, stageExits=stages,
    authorizationConsumed=True, currentControllerChangesAuthorized=False,
    dumpFiles=[], faultClears=0, clockChanges=0, powerOperations=0, hardKills=0)
save(D / 'runtime_summary_01.json', summary)
save(D / 'owner_authorization_consumed_01.json', dict(authorizationConsumed=True,
    currentControllerChangesAuthorized=False, approvalQuestion='call_abc4d640a85f42539728d5b6b697dbb4:0',
    ownerInstruction='Approve guarded S4b reader retry', authorizationSha256=sha(D / 'authorization.json'),
    sessionResultSha256=sha(D / 'session_result.json')))
name = 'AB_S4B_READER_RUNTIME_2026-10-26' if functional else 'AB_S4B_READER_RETRY_ATTEMPT_2026-10-26'
OUT = E / name
REPORT = OUT.with_suffix('.md')
assert not OUT.exists() and not REPORT.exists()
report = (W / ('reader_runtime_report.txt' if functional else 'reader_attempt_report.txt')).read_text(encoding='utf-8')
report = report.format(summary=summary, inspection=inspection, native=native, samples=len(dart['samples']),
    all_good=all_good, uncertain=uncertain, error=dart['error'], baseline_median=summary['baselineScanMedianUs'],
    baseline_max=summary['baselineScanCumulativeMaxUs'])
with REPORT.open('x',encoding='utf-8') as stream:
    stream.write(report)
artifacts=[]
def archive(path,relative):
    raw=path.read_bytes()
    expanded=None
    if path.suffix.lower() in ('.log','.l5x'):
        expanded=hashlib.sha256(raw).hexdigest()
        raw=gzip.compress(raw,mtime=0)
        relative+='.gz'
    target=OUT / relative
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(target),
        **({'expandedSha256':expanded} if expanded else {})))
for path in sorted(D.rglob('*')):
    if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.relative_to(D).parts):
        continue
    if path.suffix.lower() not in ('.py','.json','.gz','.log','.txt','.sha256','.l5x','.cs','.csproj'):
        continue
    assert 'credential' not in path.name.lower()
    archive(path,'Runtime/'+path.relative_to(D).as_posix())
for name in ('authorize_reader_retry_01.py','inspect_reader_runtime_01.py','replay_reader_pairs_01.py',
             'compare_reader_config_pages_01.py','inspect_reader_pair_schema_01.py',
             'analyze_reader_scan_01.py','review_reader_scan_01.py',
             'inventory_legacy_consumers_01.py','legacy_consumer_inventory_01.json',
             'seal_reader_runtime_01.py','reader_runtime_report.txt','reader_attempt_report.txt'):
    archive(W / name,'Continuation/'+name)
for name in ('authorize_reader_retry_01.log','authorize_reader_retry_01_exit.json'):
    archive(W.parent / 'session_01' / name,'Continuation/'+name)
save(OUT / 'manifest.json',dict(schema='fraktal.ab.s4b-reader-runtime',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    preparationManifestSha256=sha(E / 'AB_S4B_READER_RETRY_PREPARATION_2026-10-26/manifest.json'),
    nativeAccepted=accepted,nativeReaderPassed=functional,scanReviewPassed=scan_passed,
    scanCauseConfirmed=False,desktopAccepted=False,candidateCases=41,pairedCapturesReplayed=87,
    observerSamples=len(dart['samples']),observerPassed=dart['passed'],configurationPages=len(dart['configurationPages']),
    baselineCases=31,genealogyRestored=True,finalChecksPassed=True,authorizationConsumed=True,
    currentControllerChangesAuthorized=False,dumpFiles=0,faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,
    credentialFilesArchived=False,acdBinariesArchived=False,committed=False,pushed=False,artifacts=artifacts))
for row in artifacts:
    assert sha(OUT / row['path']) == row['sha256']
save(W / 'sealed_reader_runtime_01.json',dict(passed=True,nativeAccepted=accepted,nativeReaderPassed=functional,
    scanReviewPassed=scan_passed,desktopAccepted=False,
    report=REPORT.as_posix(),artifacts=len(artifacts),manifestSha256=sha(OUT / 'manifest.json')))
print(json.dumps(dict(sealed=True,nativeAccepted=accepted,nativeReaderPassed=functional,
    scanReviewPassed=scan_passed,desktopAccepted=False,artifacts=len(artifacts),
    samples=len(dart['samples']),genealogyRestored=True)))

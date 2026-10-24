from pathlib import Path
import datetime
import gzip
import hashlib
import json
import sys

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
R=Path(__file__).parent
W=R.parent/'prepare_0d22cab49f6e4aeeb6fa005ef0f4f9be'
BASE=ROOT/'Specification/AllenBradley/Evidence'
NAME='AB_S3A_CANONICAL_RUNTIME_2026-10-21'
DEST=BASE/NAME
REPORT=BASE/(NAME+'.md')

def sha(data):return hashlib.sha256(data).hexdigest()

def put(relative,data):
    path=DEST/relative
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data:raise RuntimeError('append-only artifact differs: '+relative)
        return
    with path.open('xb') as output:output.write(data)

if sys.argv[1]=='stage':
    DEST.mkdir()
    put('Runtime/capacity_review.json',(R/'capacity_review.json').read_bytes())
    reference=Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.L5X')
    put('Reference/genealogy_current.L5X.gz',gzip.compress(reference.read_bytes(),mtime=0))
    for name in ('canonical.sha256','backup.sha256','preflight.json','deploy_attempt.json',
                 'baseline_capacity.json','baseline_reference.json','RUNBOOK.md',
                 'audit_access.py','final_checks.py','measure_timing.py',
                 'session/Program.cs','session/S3aSession.csproj',
                 'scripts/guard_echo.py','scripts/preflight.py'):
        put('Session/'+name,(W/name).read_bytes())
    for name in ('canonical_downloaded.L5X','echo_before_s3a.L5X','genealogy_restored.L5X'):
        put('Session/'+name+'.gz',gzip.compress((W/name).read_bytes(),mtime=0))
    bindings=json.loads((R/'runtime_source_bindings.json').read_text())['sha256']
    for name,expected in bindings.items():
        data=(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'/name).read_bytes()
        assert sha(data)==expected
        put('Tools/'+name,data)
    for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
                 'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md',
                 'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
                 'AB_CANONICAL_PUBLICATION_S3A_NOTES_2026-10-21.md',
                 'AB_CAPACITY_FORECAST_METHOD_2026-10-21.md',
                 'AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
        put('Target/'+name,(BASE.parent/name).read_bytes())
    print(json.dumps(dict(staged=True,directory=str(DEST))))
elif sys.argv[1]=='seal':
    if (DEST/'manifest.json').exists():raise RuntimeError('already sealed')
    for file in R.iterdir():
        if file.is_file():
            if file.suffix.lower()=='.acd' or 'credential' in file.name.lower():
                raise RuntimeError('forbidden artifact')
            put('Runtime/'+file.name,file.read_bytes())
    artifacts=[]
    for file in sorted(DEST.rglob('*')):
        if not file.is_file():continue
        data=file.read_bytes()
        row=dict(path=file.relative_to(DEST).as_posix(),bytes=len(data),sha256=sha(data))
        if file.name.endswith('.L5X.gz'):row.update(expandedSha256=sha(gzip.decompress(data)))
        artifacts.append(row)
    expected_original='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
    assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').read_bytes()).upper()==expected_original
    for name in ('backup_01','deploy_01','restore_01','candidate_regressions_02','baseline_regressions_01',
                 'ab_suite_01','root_tests_01','spec_gate_01','contracts_gate_01','consistency_gate_01',
                 'whitespace_gate_01','capacity_holdout_02','capacity_profile_replay_01','final_checks_02'):
        assert json.loads((R/(name+'_exit.json')).read_text())['exitCode']==0,name
    for name in ('candidate_regressions_02','baseline_regressions_01'):
        evidence=json.loads((R/(name+'.json')).read_text())
        assert len(evidence['rows'])==31 and all(row['passed'] for row in evidence['rows'])
        assert evidence['restored'] and evidence['policyRestored']
    assert json.loads((R/'final_checks_02.json').read_text())['passed']
    manifest=dict(schema='fraktal.ab.s3a-canonical-runtime-evidence',schemaVersion=1,
        date='2026-10-21',timeZone='America/Mexico_City',
        sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),artifacts=artifacts,
        artifactCount=len(artifacts),totalBytes=sum(row['bytes'] for row in artifacts),
        runtimeAccepted=True,publicationStage='S3a',acceptedPaths=94,
        acceptedRegressionRows=62,extraPartialCandidateRegressionRows=18,totalRegressionRows=80,
        acceptedActiveDecisionPairs=4,retainedFailedAcquisitions=1,recordedDownloads=2,
        recordedModeChanges=4,faultClears=0,nativeAcdFilesArchived=False,credentialFilesArchived=False,
        priorSeals=json.loads((R/'prior_seals_verification_02.json').read_text())['rows'])
    with (DEST/'manifest.json').open('x',encoding='utf-8') as output:json.dump(manifest,output,indent=2)
    print(json.dumps(dict(sealed=True,artifacts=len(artifacts),bytes=manifest['totalBytes'],reportSha256=manifest['reportSha256'])))
else:raise SystemExit('stage or seal required')

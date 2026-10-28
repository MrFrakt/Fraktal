"""Append-only S4a preparation seal; no credentials or native ACD binaries."""
from pathlib import Path
import datetime,gzip,hashlib,json,re

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
W=Path(__file__).parent;D=W.parent/'session_01'
E=ROOT/'Specification/AllenBradley/Evidence'
NAME='AB_S4A_COHERENCE_PREPARATION_2026-10-25'
OUT=E/NAME;REPORT=E/(NAME+'.md')
load=lambda p:json.loads(p.read_bytes())
sha=lambda data:hashlib.sha256(data).hexdigest()

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')

assert not OUT.exists() and REPORT.exists() and not (D/'authorization.json').exists()
gates=('ab_suite_02','root_tests_02','sealed_spec_01','sealed_contracts_01','sealed_consistency_01',
       'sealed_whitespace_01','native_EchoController_02','native_PhysicalController_02',
       'readback_EchoController_02','readback_PhysicalController_02','access_Echo_02','access_Physical_02',
       'prepared_compare_02','prepare_capacity_02','compatibility_01','qualification_checks_01',
       'session_helper_build_02','pinned_lockfile_01','pinned_analyze_01','pinned_suite_01','echo_readiness_01')
for name in gates:assert load(W/(name+'_exit.json'))['exitCode']==0,name
assert re.search(r'Ran 2320 tests', (W/'ab_suite_02.log').read_text())
assert '608 ~12: All tests passed!' in (W/'pinned_suite_01.log').read_text()
assert load(W/'qualification_checks_01.json')['passed']
assert load(W/'capacity_auto_02.json')['CanonicalSha256']==sha((D/'s4a_coherence.ACD').read_bytes()).upper()

decision=dict(schema='fraktal.ab.owner-wire-contract-decision',schemaVersion=1,
    question='call_6bf53f81733f4bac8119326954e3b4d6:0',
    answer='A — publish existing counter bindings (Recommended)',
    recordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    approvedScope='V6.7 publication contract and dependent offline work only',
    controllerChangesAuthorized=False,serial='601FC87B')
save(W/'owner_wire_contract_decision_01.json',decision)

previous=E/'AB_S3K_CANONICAL_RUNTIME_2026-10-25/manifest.json'
names={row['name'] for row in load(previous)['priorSeals']}|{previous.parent.name}
names.update(('AB_PRESS_S3_EXIT_ATTEMPT_2026-10-25','AB_PRESS_S3_EXIT_RETRY_ATTEMPT_2026-10-25',
              'AB_PRESS_S3_EXIT_THIRD_ATTEMPT_2026-10-25','AB_PRESS_S3_EXIT_RUNTIME_2026-10-25'))
seals=[];total=0
for name in sorted(names):
    path=E/name/'manifest.json';held=load(path)
    for row in held['artifacts']:
        raw=(path.parent/row['path']).read_bytes()
        assert sha(raw)==row['sha256'].lower() and len(raw)==row['bytes'],(name,row['path'])
        if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256'].lower()
    if held.get('reportSha256'):assert sha((E/held['report']).read_bytes())==held['reportSha256'].lower()
    seals.append(dict(name=name,manifestSha256=sha(path.read_bytes()),artifacts=len(held['artifacts'])))
    total+=len(held['artifacts'])
save(W/'prior_seals_01.json',dict(passed=True,records=len(seals),artifacts=total,rows=seals))
print(json.dumps(dict(priorSealsVerified=len(seals),priorArtifacts=total)),flush=True)

files=set(T.glob('*.py'))|set((T/'Fraktal.Ab.OfflineProbe').glob('*.cs'))|set((T/'Fraktal.Ab.OfflineProbe').glob('*.csproj'))
files.update(D.rglob('*.py'));files.update((D/'session').glob('*.cs'));files.update((D/'session').glob('*.csproj'))
files.update((D/'session/bin/Debug/net8.0/win-x86').glob('*.dll'))
files.add(D/'session/bin/Debug/net8.0/win-x86/S4Session.exe')
files.update((D/'s4a_coherence.ACD',D/'s4a_coherence.L5X',D/'canonical.sha256',D/'genealogy.sha256',
              D/'capacity_review.json',D/'canonical_prepared_compare.json'))
prior=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
files.update(prior/n for n in ('audit_baseline_access.py','final_checks.py','measure_timing.py'))
files.update((ROOT/'tools').glob('check_*.py'))
docs=['Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S4_COHERENCE_REVIEW_2026-10-25.md',
      'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
      'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json',
      'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',
      'AGENTS.md','Specification/Fraktal_AB_Part_III.md','Specification/OPCUA_TRANSPORT.md',
      'Specification/HMI_CONTRACT.md','Specification/reason_rationalization.json']
hmi=['FraktalCore/HMI/packages/fraktal_opcua_client/lib/src/cip_template.dart',
     'FraktalCore/HMI/packages/fraktal_opcua_client/lib/src/cip_read_coherence.dart',
     'FraktalCore/HMI/test/cip_template_test.dart','FraktalCore/HMI/test/cip_read_coherence_test.dart',
     'FraktalCore/HMI/test/fixtures/cip_template_goldens.json.gz','FraktalCore/HMI/lib/ui/facet_cards.dart',
     'FraktalCore/HMI/pubspec.yaml','FraktalCore/HMI/pubspec.lock']
files.update(ROOT/p for p in docs+hmi)
binding=dict(schema='fraktal.ab.s4a-source-bindings',schemaVersion=1,gatesPassed=True,
             currentControllerChangesAuthorized=False,sha256={str(p):sha(p.read_bytes()).upper() for p in sorted(files)},
             gates=list(gates),abTests=2320,rootTests=74,flutterPassed=608,flutterSkipped=12)
save(D/'source_bindings.json',binding)

artifacts=[]
def archive(source,relative,compress=False):
    raw=source.read_bytes();data=gzip.compress(raw,mtime=0) if compress else raw
    name=relative+('.gz' if compress else '')
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(data)
    row=dict(path=name,bytes=len(data),sha256=sha(data))
    if compress:row['expandedSha256']=sha(raw)
    artifacts.append(row)

for folder,prefix in ((W,'Preparation'),(D,'Session')):
    for source in sorted(folder.rglob('*')):
        if not source.is_file() or any(p in ('bin','obj','__pycache__') for p in source.relative_to(folder).parts):continue
        if source.suffix.lower() not in ('.py','.json','.log','.txt','.sha256','.l5x','.cs','.csproj'):continue
        assert 'credential' not in source.name.lower()
        archive(source,prefix+'/'+source.relative_to(folder).as_posix(),source.suffix.lower() in ('.log','.l5x'))
for source in sorted(files):
    if source.is_relative_to(ROOT):
        archive(source,'Source/'+source.relative_to(ROOT).as_posix(),source.suffix!='.gz')
manifest=dict(schema='fraktal.ab.s4a-coherence-preparation',schemaVersion=1,date='2026-10-25',
    timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),decision=decision,offlineGatesPassed=True,
    nativeAccepted=False,controllerChangesAuthorized=False,controllerChangesPerformed=0,
    readOnlyEchoReadinessPassed=True,acdSha256=binding['sha256'][str(D/'s4a_coherence.ACD')],
    sourceSha256=binding['sha256'][str(D/'s4a_coherence.L5X')],
    abTests=2320,rootTests=74,flutterPassed=608,flutterSkipped=12,
    measuredOfflineCapacity=load(W/'capacity_auto_02.json'),plannedGroupCount=8,
    preparationAuthorizationRefusalCases=16,priorSeals=seals,priorArtifacts=total,
    artifacts=artifacts,artifactCount=len(artifacts),credentialFilesArchived=False,nativeAcdFilesArchived=False,
    committed=False,pushed=False)
save(OUT/'manifest.json',manifest)
for row in artifacts:
    raw=(OUT/row['path']).read_bytes()
    assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
    if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256']
assert sha(REPORT.read_bytes())==manifest['reportSha256']
save(W/'sealed_preparation_01.json',dict(passed=True,manifest=str(OUT/'manifest.json'),
    manifestSha256=sha((OUT/'manifest.json').read_bytes()),artifacts=len(artifacts),priorSeals=len(seals),
    priorArtifacts=total,currentControllerChangesAuthorized=False))
print(json.dumps(dict(passed=True,artifacts=len(artifacts),priorSeals=len(seals),nativeAccepted=False,
    currentControllerChangesAuthorized=False)),flush=True)

"""Seal a session-only diagnostic over unchanged shipping sources; no I/O to Echo."""
from pathlib import Path
import concurrent.futures,datetime,gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;S=W.parent/'session_01'
OLD=Path('C:/work/fraktal-ab-s4b-pool-20261027/session_01');H=OLD.parent/'offline_01'
G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')
E=R/'Specification/AllenBradley/Evidence';P=E/'AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27'
O=E/'AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27';REPORT=O.with_suffix('.md')
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not O.exists() and not REPORT.exists() and not (S/'source_bindings.json').exists()
for name in ('authorization.json','session_started.json','deploy_attempt.json','echo_before_s4b.ACD','desktop_live','part_read_diagnostics.jsonl'):
    assert not (S/name).exists(),name
for label in ('prepare_session_01','part_trace_tests_01','partdiag_sdk_build_01','partdiag_authorization_checks_01',
 'partdiag_workflow_checks_01','partdiag_readiness_checks_01','partdiag_readonly_refusals_01','update_status_01',
 'partdiag_spec_01','partdiag_contracts_01','partdiag_consistency_01','partdiag_root_tests_01','partdiag_whitespace_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert load(W/'cli_refusal_01_exit.json')['exitCode']==255
assert b'Ran 6 tests' in (W/'part_trace_tests_01.log').read_bytes()
assert b'Ran 74 tests' in (W/'partdiag_root_tests_01.log').read_bytes()
for label in ('pool_pub_01','pool_flutter_02','pool_analyze_02','pool_windows_02','pool_tests_06'):
    assert load(H/(label+'_exit.json'))['exitCode']==0,label
assert b'660 ~12: All tests passed!' in (H/'pool_flutter_02.log').read_bytes()
assert b'Ran 2339 tests' in (G/'ab_suite_01.log').read_bytes()
previous=load(OLD/'runtime_summary_01.json')
assert not previous['nativeAccepted'] and previous['candidateCases']==25 and previous['pairedCapturesReplayed']==53
assert previous['observerSamples']==1288 and previous['allGoodSamples']==1288
assert previous['genealogyRestored'] and previous['baselineCases']==31 and previous['finalChecksPassed']
assert load(OLD/'session_result.json')['authorizationConsumed']
pin='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5'
source_pin='60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E'
assert sha(S/'s4b_read_view.ACD').upper()==pin==sha(G/'canonical_cold_01.ACD').upper()
assert sha(S/'s4b_read_view.L5X').upper()==source_pin
assert load(G/'capacity_auto_01.json')['CanonicalSha256']==pin
allowed={R/'Specification/AllenBradley'/name for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
 'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json')}
files=set();changed=[];plc_count=0
for name,expected in load(OLD/'source_bindings.json')['sha256'].items():
    path=Path(name)
    if path.is_relative_to(OLD):
        path=S/path.relative_to(OLD)
        if not path.is_file():continue
    else:
        if sha(path).upper()!=expected.upper():
            assert path in allowed,'unexpected shipping/input change: '+name
            changed.append(path)
        if 'FraktalCore/PLC/Allen-Bradley/tools/' in name:
            assert sha(path).upper()==expected.upper(),name
            plc_count+=1
    files.add(path)
assert set(changed)==allowed and plc_count==373
mirror=load(W/'isolated_hmi_sources_01.json');assert len(mirror['files'])==318
for row in mirror['files']:
    p,copy=Path(row['source']),Path(row['copy'])
    assert sha(p)==row['sha256'] and p.read_bytes()==copy.read_bytes()
    files.update((p,copy))
for path in S.rglob('*'):
    if path.is_file() and not any(p in ('obj','__pycache__') for p in path.parts):
        if path.suffix.lower() in ('.py','.cs','.csproj','.dart','.json','.dll','.exe','.l5x','.acd','.sha256'):files.add(path)
files.update(allowed)
assert (S/'part_read_diagnostics.py').read_bytes()==(W/'part_read_diagnostics.py').read_bytes()
text=(OLD/'candidate_regressions_v2.py').read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
before="            result=genealogy.main(run_type_factory=paired,schema='fraktal.ab.s4b-genealogy-fixture',expected_declaration='fraktal_ab_genealogy_s4b_demo')"
assert text.count(before)==1
text=text.replace(before,"            from part_read_diagnostics import trace_part_reads\n            with trace_part_reads(D/'part_read_diagnostics.jsonl'):\n    "+before)
assert text==(S/'candidate_regressions_v2.py').read_text(encoding='utf-8')
for name in ('qualification_session_v2.py','desktop_readonly.py','task_monitor.py','session/Program.cs'):
    assert (S/name).read_text(encoding='utf-8')==(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix()),name
package=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01/.dart_tool/package_config.json')
assert load(package)['flutterVersion']=='3.47.5'
assert (package.parent.parent/'pubspec.lock').read_bytes()==(R/'FraktalCore/HMI/pubspec.lock').read_bytes()
assert not load(S/'authorization.template.json')['CurrentOwnerApproved']
files.add(package);files.discard(R/'FraktalCore/HMI/.dart_tool/package_config.json')
names={p['name'] for p in load(P/'manifest.json')['priorSeals']}
names.update(('AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27','AB_S4B_PARALLEL_READER_ATTEMPT_2026-10-27'))
assert len(names)==96
seals=[];checks=[]
for name in sorted(names):
    p=E/name/'manifest.json';m=load(p)
    if m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256'].lower(),name
    checks.extend((p.parent/row['path'],row) for row in m['artifacts'])
    seals.append(dict(name=name,manifestSha256=sha(p),artifacts=len(m['artifacts'])))
def verify(item):
    p,row=item;raw=p.read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'].lower(),p
    if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256'].lower(),p
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(verify,checks))
def save(path,value):
    with path.open('x',encoding='utf-8',newline='') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
# Outputs begin only after all input, gate and prior-evidence checks succeed.
save(S/'source_bindings.json',dict(schema='fraktal.ab.s4b-part-read-diagnostic-source-bindings',gatesPassed=True,
 currentOwnerApproved=False,canonicalSha256=pin,sourceSha256=source_pin,unchangedPlcBoundFiles=373,
 changedHmiFiles=[],hmiMirrorInputs=318,sessionOnlyPartTracing=True,privatePinnedPackageMap=True,
 sha256={p.as_posix():sha(p).upper() for p in sorted(files)}))
with REPORT.open('x',encoding='utf-8',newline='') as f:f.write((W/'partdiag_preparation_report_01.md').read_text(encoding='utf-8'))
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower(),path
    raw=path.read_bytes();expanded=None
    if path.suffix.lower() in ('.log','.l5x'):
        expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=O/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,source=path.as_posix(),bytes=len(raw),sha256=sha(target),
      **(dict(expandedSha256=expanded) if expanded else {})))
for p in sorted(files):
    if p.suffix.lower() in ('.acd','.dll','.exe'):continue
    if p.is_relative_to(S):rel='Preparation/'+p.relative_to(S).as_posix()
    elif p.is_relative_to(R):rel='Source/'+p.relative_to(R).as_posix()
    else:continue
    archive(p,rel)
archive(S/'source_bindings.json','Preparation/source_bindings.json')
for p in sorted(W.iterdir()):
    if p.is_file() and p.name!='seal_preparation_01.log' and p.suffix.lower() in ('.py','.dart','.json','.log','.md'):
        archive(p,'Offline/'+p.name)
for label in ('pool_pub_01','pool_flutter_02','pool_analyze_02','pool_windows_02','pool_tests_06'):
    for suffix in ('.log','_exit.json'):archive(H/(label+suffix),'TransferredHmiGates/'+label+suffix)
for label in ('ab_suite_01','build_EchoController_01','readback_EchoController_01','build_PhysicalController_01',
 'readback_PhysicalController_01','access_echo_01','access_physical_01','sdk_gate_echo_01','sdk_gate_physical_01',
 'capacity_01','prepared_compare_01'):
    for suffix in ('.log','_exit.json'):archive(G/(label+suffix),'TransferredPlcGates/'+label+suffix)
for name in ('capacity_auto_01.json','prepared_pins_01.json','cold_layout_comparison_01.json'):
    archive(G/name,'TransferredPlcGates/'+name)
save(O/'manifest.json',dict(schema='fraktal.ab.s4b-part-read-diagnostic-preparation',schemaVersion=1,
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
 canonicalSha256=pin,sourceSha256=source_pin,sourceBindingsSha256=sha(S/'source_bindings.json'),
 abTests=2339,rootTests=74,flutterTests=660,flutterSkipped=12,partTraceTests=6,
 unchangedPlcBoundFiles=373,changedHmiFiles=0,sessionOnlyPartTracing=True,
 nativeSessionAuthorized=False,nativeAccepted=False,controllerChanges=0,priorSeals=seals,artifacts=artifacts,
 credentialFilesArchived=False,acdBinariesArchived=False,sdkBinariesArchived=False))
for row in artifacts:assert sha(O/row['path'])==row['sha256']
save(W/'sealed_preparation_01.json',dict(passed=True,manifestSha256=sha(O/'manifest.json'),artifacts=len(artifacts),
 sourceBindings=len(files),priorSeals=len(seals),unchangedPlcBoundFiles=373,changedHmiFiles=0,
 nativeSessionAuthorized=False,controllerChanges=0))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(files),priorSeals=len(seals),
 changedShippingFiles=0,nativeSessionAuthorized=False,controllerChanges=0)))

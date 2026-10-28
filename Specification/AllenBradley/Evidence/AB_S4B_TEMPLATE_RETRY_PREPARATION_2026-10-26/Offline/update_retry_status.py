from pathlib import Path
import hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;H=R/'FraktalCore/HMI';COPY=W.parent/'hmi_verify_01'
original=json.loads((W/'isolated_hmi_sources_01.json').read_bytes());rows=[]
for row in original['files']:
    source=Path(row['source']);copy=Path(row['copy']);assert source.read_bytes()==copy.read_bytes(),source
    rows.append(dict(source=source.as_posix(),copy=copy.as_posix(),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),bytes=source.stat().st_size))
for name in ('isolated_test_dependencies_01.json','isolated_core_dependencies_01.json'):
    for row in json.loads((W/name).read_bytes())['files']:
        assert Path(row['source']).read_bytes()==Path(row['copy']).read_bytes()
config=json.loads((COPY/'.dart_tool/package_config.json').read_bytes());assert config['flutterVersion']=='3.47.5' and config['generatorVersion']=='3.13.4'
assert (COPY/'pubspec.lock').read_bytes()==(H/'pubspec.lock').read_bytes()
with (W/'isolated_hmi_sources_02.json').open('x',encoding='utf-8',newline='') as stream:
    json.dump(dict(passed=True,files=rows,sdk='Flutter 3.47.5 / Dart 3.13.4',dependencySourcesEqual=True,lockfileUnchanged=True),stream,indent=2)
v2=R/'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(v2.read_bytes());status=doc['manifestV68']
status.update(nativeAccepted=False,currentSessionAuthorized=False,
    lastAttempt='Evidence/AB_S4B_CANONICAL_ATTEMPT_2026-10-26.md',lastAttemptAccepted=False,sessionApprovalConsumed=True,
    nativeDeploymentSdkReadbackAccessPassed=True,lastAttemptCandidateCases=0,baselineChecks=31,genealogyRestored=True,finalChecksPassed=True,
    preparation='Evidence/AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26.md',
    retryNativeSessionAuthorized=False,qualificationRunner='C:/work/fraktal-ab-s4b-20261025/retry_template_01/qualification_session_v2.py',
    parserCorrection='Read complete DINT allocation of Template definition; strict names/fragment bounds retained; handle/offset diagnostics added',
    correctionProof='Ten recorded native S0 definitions, including two with a final NUL beyond unrounded length; four new tests; S4b failing handle not recorded',
    currentReadOnlyBaselineDiscovery=dict(symbols=60,templates=50,elapsedMs=118))
status['offlineGates'].update(flutterTests=635,flutterSkipped=12,namespaceRecordedTemplates=10,namespaceTests=4,
    hmiTestEnvironment='Identical isolated HMI sources plus unchanged sibling PLC module inventory; pinned SDK; full suite concurrency=1')
status['loginFixtureCorrection']='Completed-expired result observed explicitly; production budget/timeout and rejection semantics unchanged'
if 'manifestV67' in doc:doc['manifestV67']['s4Status']='S4a initial small-group scope accepted. S4b implemented offline; first native discovery attempt failed before candidate writes and rolled back cleanly. Template parser correction prepared; native S4b/desktop acceptance pending.'
v2.write_bytes((json.dumps(doc,indent=2,ensure_ascii=False)+'\n').encode())
print(json.dumps(dict(passed=True,identicalHmiSources=len(rows),sdk=config['flutterVersion'],nativeAccepted=False,retryAuthorized=False)))

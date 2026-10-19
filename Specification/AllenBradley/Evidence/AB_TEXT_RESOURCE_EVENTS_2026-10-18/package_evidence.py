import hashlib, json, re, shutil
from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).parent
DEST=ROOT/'Specification/AllenBradley/Evidence/AB_TEXT_RESOURCE_EVENTS_2026-10-18'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def read_json(name): return json.loads((WORK/name).read_text(encoding='utf-8'))
def log(name):
    raw=(WORK/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
for name,count in [('ab_tests_01.log',1878),('focused_tests_02.log',15),('root_tests_01.log',74)]:
    text=log(name)
    assert re.search(rf'^Ran {count} tests ',text,re.M) and re.search(r'^OK\s*$',text,re.M),name
assert read_json('ab_tests_01_result.json')['exitCode']==0
runtime=read_json('runtime_01.json')
final=read_json('final_checks.json')
assert runtime['restored'] and runtime['policyRestored'] and len(runtime['rows'])==31 and all(row['passed'] for row in runtime['rows'])
assert final['passed'] and len(final['checks'])==31
for name in ('echo_compare.json','physical_compare.json','prepared_compare.json','downloaded_compare.json','array_echo_compare.json','array_physical_compare.json'):
    assert read_json(name)['Equivalent'],name
for name in ('compiler_audit.json','download_audit.json'):
    assert all(row['Clean'] for row in read_json(name).values()),name
assert read_json('array_compiled.json')['passed']
assert all(row['audit']['Clean'] for row in read_json('array_compiled.json')['rows'])
native_names=['text_01.L5X','text_array_01.L5X','numeric_baseline.L5X','tower_baseline.L5X',
    'echo_readback.L5X','physical_readback.L5X','array_echo_readback.L5X','array_physical_readback.L5X',
    'prepared_readback.L5X','downloaded_text.L5X','text_01.ACD','echo_before_text.ACD',
    'echo_before_text.L5X','text_reproduced.L5X','text_predeploy_reproduced.L5X']
native=[dict(path=str(WORK/name),sha256=sha(WORK/name),bytes=(WORK/name).stat().st_size) for name in native_names]
files=['compile.py','array_build.py','preflight.py','guard_echo.py','check_prepared.py','session.py','Program.cs','TextSession.csproj',
    'final_checks.py','package_evidence.py','numeric_baseline_generation.json','text_01_generation.json','array_generation.json',
    'compiled.json','array_compiled.json','echo_compare.json','physical_compare.json','prepared_compare.json','downloaded_compare.json',
    'array_echo_compare.json','array_physical_compare.json','compiler_audit.json','download_audit.json',
    'echo_build.log','physical_build.log','array_echo_build.log','array_physical_build.log','prepare.log','backup.log','deploy-authorized.log',
    'prepared.sha256','backup.sha256','preflight.json','runtime_01.json','runtime_01.log','predeploy_reproduction.json',
    'final_checks.json','final_batch.json','final_identity.json','final_echo.json','hmi_host_values.json','size.json',
    'resources.sqlite','resources.cursor.json','sink_1.log','sink_2.log',
    'ab_tests_01.log','ab_tests_01_result.json','focused_tests_01.log','focused_tests_02.log','root_tests_01.log',
    'spec_gate_02.log','contracts_gate_02.log','consistency_gate_02.log']
source_names=['fraktal_ab_declaration.py','fraktal_ab_generate.py','fraktal_ab_resources.py','fraktal_ab_host_events.py',
    'fraktal_ab_manifest.py','fraktal_ab_part.py','fraktal_ab_sets.py','fraktal_ab_resource_demo.py','fraktal_ab_resource_execute.py',
    'fraktal_ab_text_resource_demo.py','fraktal_ab_text_resource_execute.py','fraktal_ab_tower_execute.py',
    'fraktal_ab_part_execute.py','fraktal_ab_host_sink.py','test_fraktal_ab_resources.py','test_fraktal_ab_text_resources.py']
for name in files: assert (WORK/name).is_file(),name
DEST.mkdir(exist_ok=False)
for name in files: shutil.copy2(WORK/name,DEST/name)
bindings=[]
for name in source_names:
    path='FraktalCore/PLC/Allen-Bradley/tools/'+name
    copied=DEST/'Sources'/path
    copied.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/path,copied)
    bindings.append(dict(path=path,sha256=sha(ROOT/path)))
artifacts=[dict(path=path.relative_to(DEST).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
    for path in sorted(DEST.rglob('*')) if path.is_file()]
manifest=dict(schema='fraktal.ab.text-resource-evidence',version=1,
    baselineCommit='5b5104a2f21b83882b2259ccbccb93d51137224a',
    authorization=dict(ownerStatement='simulated plc is available for you to download anytime',
        target='local Echo 601FC87B',physicalControllerAuthorized=False),
    declaration='fraktal_ab_text_resource_demo',manifestHash=final['manifestHash'],
    validation=dict(abTests=1878,newTextTests=15,rootTests=74,compilerCases=4,liveRows=31,resourceRows=21,
        liveLiteralConfirmations=9,liveArrayQualification=False,finalChecks=31,
        configurationRestored=True,policyRestored=True),
    preparedAcdSha256=final['preparedAcdSha256'],downloadedAcdSha256=final['downloadedAcdSha256'],
    backupAcdSha256=final['backupAcdSha256'],nativeArtifactReferences=native,
    nativeArtifactsArchived=False,sourceBindings=bindings,artifacts=artifacts)
with (DEST/'manifest.json').open('x',encoding='utf-8') as stream:
    json.dump(manifest,stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(artifacts=len(artifacts),sources=len(bindings),bytes=sum(a['bytes'] for a in artifacts),manifestSha256=sha(DEST/'manifest.json'))))

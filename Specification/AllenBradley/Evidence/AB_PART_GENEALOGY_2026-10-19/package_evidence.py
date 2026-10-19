import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).parent
DEST=ROOT/'Specification/AllenBradley/Evidence/AB_PART_GENEALOGY_2026-10-19'

def sha(value): return hashlib.sha256(value).hexdigest().upper()
def read(name): return json.loads((WORK/name).read_text(encoding='utf-8'))
def blob(path):return subprocess.check_output(['git','show',':'+path],cwd=ROOT)
def decoded(name):
    value=(WORK/name).read_bytes()
    return value.decode('utf-16' if value.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')

assert read('ab_tests_02_result.json')['exitCode']==0
for name,count in [('ab_tests_02.log',1890),('focused_tests_04.log',12),('root_final_4.log',74)]:
    log=decoded(name)
    assert re.search(rf'^Ran {count} tests ',log,re.M) and re.search(r'^OK\s*$',log,re.M),name
assert '+12: All tests passed!' in decoded('hmi_tests_final.log')
assert 'No issues found!' in decoded('hmi_analyze.log')
assert all(row['exitCode']==0 for row in read('root_final_results.json'))
runtime=read('runtime_01.json');final=read('final_checks.json')
assert runtime['restored'] and runtime['policyRestored'] and len(runtime['rows'])==31
assert all(row['passed'] for row in runtime['rows'])
assert sum(row.get('genealogyChecksPassed',False) for row in runtime['rows'])==21
assert final['passed'] and len(final['checks'])==37
assert read('post_gateway_checks.json')['passed']
gateway=read('gateway_restart.json')
assert gateway['passed'] and gateway['reconnectAndHistoryPreserved'] and len(gateway['rows'][0]['history'])==260
assert all(read(name)['Equivalent'] for name in ('echo_compare.json','physical_compare.json',
    'array_echo_compare.json','array_physical_compare.json','prepared_compare.json','downloaded_compare.json'))
assert all(row['Clean'] for name in ('compiler_audit.json','download_audit.json') for row in read(name).values())
assert read('array_compiled.json')['passed'] and all(row['audit']['Clean'] for row in read('array_compiled.json')['rows'])
assert read('predeploy_reproduction.json')['equivalent']
assert sha((WORK/'text_baseline.L5X').read_bytes())=='E96AF70FFC0C77FD2E44AB8CEB1B8F14FF5381A1D9A5830EC640A825872C71C9'
assert sha((WORK/'tower_baseline.L5X').read_bytes())=='03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED'

native_names=['genealogy_01.L5X','genealogy_array_01.L5X','text_baseline.L5X','tower_baseline.L5X',
    'echo_readback.L5X','physical_readback.L5X','array_echo_readback.L5X','array_physical_readback.L5X',
    'prepared_readback.L5X','downloaded_genealogy.L5X','genealogy_01.ACD','echo_before_genealogy.ACD',
    'echo_before_genealogy.L5X','genealogy_reproduced.L5X','genealogy_predeploy_reproduced.L5X']
native=[dict(path=str(WORK/name),sha256=sha((WORK/name).read_bytes()),bytes=(WORK/name).stat().st_size) for name in native_names]
files=['compile.py','array_build.py','preflight.py','check_prepared.py','session.py','Program.cs','TextSession.csproj',
    'final_checks.py','final_checks_attempt_01.py','final_attempt_01.json','gateway_restart.py','post_gateway_checks.py',
    'package_evidence.py','text_baseline_generation.json','genealogy_01_generation.json','array_generation.json',
    'compiled.json','array_compiled.json','echo_compare.json','physical_compare.json','prepared_compare.json','downloaded_compare.json',
    'array_echo_compare.json','array_physical_compare.json','compiler_audit.json','download_audit.json',
    'echo_build.log','physical_build.log','array_echo_build.log','array_physical_build.log','prepare.log','backup.log','deploy-authorized.log',
    'prepared.sha256','backup.sha256','preflight.json','runtime_01.json','runtime_01.log','predeploy_reproduction.json',
    'final_checks.json','final_batch.json','final_identity.json','final_echo.json','hmi_host_values_final.json','hmi_part_values.json','size.json',
    'resources.sqlite','resources.cursor.json','sink_1.log','sink_2.log','gateway_1.log','gateway_02_1.log','gateway_02_2.log',
    'gateway_restart.json','post_gateway_checks.json','ab_tests_02.log','ab_tests_02_result.json','focused_tests_04.log',
    'root_final_1.log','root_final_2.log','root_final_3.log','root_final_4.log','root_final_results.json',
    'hmi_tests_final.log','hmi_analyze.log']
sources=json.loads((WORK/'authored_paths.json').read_text())
sources+=['FraktalCore/PLC/Allen-Bradley/tools/'+name for name in (
    'fraktal_ab_text_resource_demo.py','fraktal_ab_text_resource_execute.py','fraktal_ab_resource_execute.py',
    'fraktal_ab_part_execute.py','fraktal_ab_tower_execute.py','fraktal_ab_host_sink.py','fraktal_ab_gateway.py',
    'fraktal_ab_st_model.py','fraktal_ab_ld_model.py')]
sources+=['Specification/AllenBradley/Evidence/AB_PART_GENEALOGY_2026-10-19.md']
assert len(sources)==len(set(sources))
for name in files:assert (WORK/name).is_file(),name
for path in sources:blob(path)
DEST.mkdir(exist_ok=False)
for name in files:shutil.copy2(WORK/name,DEST/name)
shutil.copy2('C:/work/fraktal-echo-deploy-20261018/guard_echo.py',DEST/'guard_echo.py')
shutil.copy2(WORK/'hmi_validation/FraktalCore/HMI/test/live_genealogy_snapshot_test.dart',DEST/'live_genealogy_snapshot_test.dart')
bindings=[]
for path in sources:
    value=blob(path)
    copied=DEST/'Sources'/path
    copied.parent.mkdir(parents=True,exist_ok=True)
    copied.write_bytes(value)
    bindings.append(dict(path=path,sha256=sha(value)))
artifacts=[dict(path=path.relative_to(DEST).as_posix(),sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
    for path in sorted(DEST.rglob('*')) if path.is_file()]
manifest=dict(schema='fraktal.ab.part-genealogy-evidence',version=1,
    baselineCommit='21acd6fc900203635831e3d81e27194d5da3aa31',
    authorization=dict(ownerStatement='simulated plc is available for you to download anytime',
        target='local Echo 601FC87B',physicalControllerAuthorized=False),
    declaration='fraktal_ab_genealogy_demo',manifestHash=final['manifestHash'],configRevision=final['configRevision'],
    validation=dict(abTests=1890,newGenealogyTests=12,rootTests=74,hmiTests=12,compilerCases=4,
        liveRows=31,genealogyRows=21,completedGenealogyCaptures=9,liveArrayQualification=False,
        finalChecks=37,postGatewayChecks=12,readOnlyGatewayRestartPhases=2,retainedGatewayHistoryPaths=260,
        installedWindowsServiceTested=False,configurationRestored=True,policyRestored=True),
    preparedAcdSha256=final['preparedAcdSha256'],downloadedAcdSha256=final['downloadedAcdSha256'],
    backupAcdSha256=final['backupAcdSha256'],nativeArtifactReferences=native,
    nativeArtifactsArchived=False,sourceBindings=bindings,artifacts=artifacts)
with (DEST/'manifest.json').open('x',encoding='utf-8') as stream:
    json.dump(manifest,stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(artifacts=len(artifacts),sources=len(bindings),bytes=sum(row['bytes'] for row in artifacts),manifestSha256=sha((DEST/'manifest.json').read_bytes()))))

import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).parent
DEST=ROOT/'Specification/AllenBradley/Evidence/AB_RESOURCE_EVENTS_2026-10-18'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def log(path):
    raw=path.read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
for name,count in [('ab_tests_03.log',1855),('focused_tests_03.log',88),('root_tests_02.log',74)]:
    text=log(WORK/name)
    if not re.search(rf'^Ran {count} tests ',text,re.M) or not re.search(r'^OK\s*$',text,re.M):
        raise AssertionError('test gate failed: '+name)
runtime=json.loads((WORK/'runtime_01.json').read_text(encoding='utf-8'))
final=json.loads((WORK/'final_checks.json').read_text(encoding='utf-8'))
if (not runtime['restored'] or not runtime['policyRestored'] or len(runtime['rows'])!=31
        or not all(row['passed'] for row in runtime['rows']) or not final['passed']):
    raise AssertionError('runtime/restoration gate failed')
native_names=['resources_01.L5X','tower_baseline.L5X','echo_readback.L5X','physical_readback.L5X',
              'prepared_readback.L5X','downloaded_resources.L5X','resources_01.ACD',
              'echo_before_resources.ACD','echo_before_resources.L5X']
native=[dict(path=str(WORK/name),sha256=sha(WORK/name),bytes=(WORK/name).stat().st_size)
        for name in native_names]
files=['prepare.py','preflight.py','check_prepared.py','session.py','Program.cs','ResourceSession.csproj',
       'final_checks.py','package_evidence.py','generation_01.json','compiled.json',
       'echo_compare.json','physical_compare.json','prepared_compare.json','downloaded_compare.json',
       'compiler_audit.json','download_audit.json','echo_build.log','physical_build.log','prepare.log',
       'backup.log','deploy-authorized.log','prepared.sha256','backup.sha256','preflight.json',
       'runtime_01.json','runtime_01.log','final_checks.json','final_batch.json','final_identity.json',
       'final_echo.json','final_reproduction.json','size.json','resources.sqlite','resources.cursor.json',
       'sink_1.log','sink_2.log','ab_tests_01.log','ab_tests_02.log','ab_tests_03.log',
       'focused_tests_03.log','root_tests_02.log','spec_gate_02.log','contracts_gate_02.log','consistency_gate_02.log']
for name in files:
    if not (WORK/name).is_file(): raise AssertionError('missing artifact: '+name)
source_names=['fraktal_ab_declaration.py','fraktal_ab_generate.py','fraktal_ab_host_events.py',
    'fraktal_ab_manifest.py','fraktal_ab_part.py','fraktal_ab_part_execute.py','fraktal_ab_sets.py',
    'fraktal_ab_tower_execute.py','fraktal_ab_resources.py','fraktal_ab_resource_demo.py',
    'fraktal_ab_resource_execute.py','test_fraktal_ab_resources.py']
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
manifest=dict(schema='fraktal.ab.resource-evidence-manifest',version=1,
    baselineCommit='db924620a1ac4508dcdd4e5e918cd46481a4041d',
    authorization=dict(ownerStatement='simulated plc is available for you to download anytime',
                       target='local Echo 601FC87B',physicalControllerAuthorized=False),
    declaration='fraktal_ab_resource_demo',manifestHash=final['manifestHash'],
    validation=dict(abTests=1855,focusedTests=88,rootTests=74,liveRows=31,resourceRows=21,
                    finalChecks=27,configurationRestored=True,policyRestored=True),
    preparedAcdSha256=final['preparedAcdSha256'],downloadedAcdSha256=final['downloadedAcdSha256'],
    backupAcdSha256=final['backupAcdSha256'],nativeArtifactReferences=native,
    nativeArtifactsArchived=False,sourceBindings=bindings,artifacts=artifacts)
with (DEST/'manifest.json').open('x',encoding='utf-8') as stream:
    json.dump(manifest,stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(artifacts=len(artifacts),sources=len(bindings),bytes=sum(a['bytes'] for a in artifacts),
                      manifestSha256=sha(DEST/'manifest.json'))))

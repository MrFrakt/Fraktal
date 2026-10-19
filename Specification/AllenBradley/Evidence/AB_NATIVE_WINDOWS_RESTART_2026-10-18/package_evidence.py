import hashlib, json, re, shutil
from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).parent
DEST=ROOT/'Specification/AllenBradley/Evidence/AB_NATIVE_WINDOWS_RESTART_2026-10-18'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def read_json(name): return json.loads((WORK/name).read_text(encoding='utf-8'))
def log(name):
    raw=(WORK/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
for name,count in [('ab_tests_01.log',1863),('root_tests_02.log',74)]:
    text=log(name)
    assert re.search(rf'^Ran {count} tests ',text,re.M) and re.search(r'^OK\s*$',text,re.M), name
runtime=read_json('runtime_01.json')
final=read_json('final_checks.json')
observation=read_json('observation_01.json')
restart=[read_json(name+'.json') for name in ('after_download','after_regression')]
assert runtime['restored'] and runtime['policyRestored'] and len(runtime['rows'])==31 and all(row['passed'] for row in runtime['rows'])
assert final['passed'] and len(final['checks'])==23
assert observation['completed'] and observation['stableCompletedRecord']
assert observation['observations']['WindowResetObserved'] and not observation['observations']['faultsObserved'] and not observation['observations']['overlapChanged']
assert all(row['passed'] for row in restart)
for name in ('echo_compare.json','physical_compare.json','prepared_compare.json','downloaded_compare.json'):
    assert read_json(name)['Equivalent'],name
for name in ('compiler_audit.json','download_audit.json'):
    assert all(row['Clean'] for row in read_json(name).values()),name
native_names=['windows_01.L5X','tower_baseline.L5X','echo_readback.L5X','physical_readback.L5X',
    'prepared_readback.L5X','downloaded_windows.L5X','windows_01.ACD','echo_before_windows.ACD',
    'echo_before_windows.L5X','windows_reproduced.L5X']
native=[dict(path=str(WORK/name),sha256=sha(WORK/name),bytes=(WORK/name).stat().st_size) for name in native_names]
files=['compile.py','preflight.py','guard_echo.py','check_prepared.py','session.py','Program.cs','WindowSession.csproj',
    'observe.py','restart_check.py','final_checks.py','package_evidence.py','generation_01.json','compiled.json',
    'echo_compare.json','physical_compare.json','prepared_compare.json','downloaded_compare.json',
    'compiler_audit.json','download_audit.json','echo_build.log','physical_build.log','prepare.log',
    'backup.log','deploy-authorized.log','prepared.sha256','backup.sha256','preflight.json',
    'observation_01.json','runtime_01.json','runtime_01.log','after_download.json','after_regression.json',
    'cursor_before_download.json','sink_before_download.json','restart.cursor.json','restart.sqlite',
    'after_download_first.log','after_download_reopen.log','after_regression_first.log','after_regression_reopen.log',
    'after_regression_stale_cursor_replay.log','after_regression_stale_cursor_reopen.log',
    'final_checks.json','final_batch.json','final_identity.json','final_echo.json','size.json',
    'ab_tests_01.log','root_tests_02.log','spec_gate_01.log','contracts_gate_01.log','consistency_gate_01.log']
source_names=['fraktal_ab_task_window_probe.py','test_fraktal_ab_task_window_probe.py',
    'fraktal_ab_observer_fixture.py','fraktal_ab_resource_demo.py','fraktal_ab_resource_execute.py',
    'fraktal_ab_tower_execute.py','fraktal_ab_part_execute.py','fraktal_ab_host_events.py','fraktal_ab_host_sink.py']
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
manifest=dict(schema='fraktal.ab.native-windows-restart-evidence',version=1,
    baselineCommit='23912ff5171021fc533b73ea510d564752be91cb',
    authorization=dict(ownerStatement='simulated plc is available for you to download anytime',
        target='local Echo 601FC87B',physicalControllerAuthorized=False),
    declaration='fraktal_ab_resource_demo',manifestHash=final['manifestHash'],
    validation=dict(abTests=1863,newProbeTests=8,rootTests=74,liveRows=31,resourceRows=21,
        nativeWindows=4,nativeIntervals=400,immediateRestartChecks=11,replayChecks=17,finalChecks=23,
        configurationRestored=True,policyRestored=True),
    productionHealthProviderChanged=False,clockReplayQualified=False,
    preparedAcdSha256=final['preparedAcdSha256'],downloadedAcdSha256=final['downloadedAcdSha256'],
    backupAcdSha256=final['backupAcdSha256'],nativeArtifactReferences=native,
    nativeArtifactsArchived=False,sourceBindings=bindings,artifacts=artifacts)
with (DEST/'manifest.json').open('x',encoding='utf-8') as stream:
    json.dump(manifest,stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(artifacts=len(artifacts),sources=len(bindings),bytes=sum(a['bytes'] for a in artifacts),manifestSha256=sha(DEST/'manifest.json'))))

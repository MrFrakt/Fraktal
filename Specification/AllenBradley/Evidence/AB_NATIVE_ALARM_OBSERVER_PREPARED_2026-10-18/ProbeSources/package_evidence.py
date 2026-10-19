import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

repo=Path('C:/Users/SoftIndVM/Fraktal')
root=Path('C:/work/fraktal-ab-alarm-runtime-20261018')
sys.path.insert(0,str(repo/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_sdk_log_gate import audit_log

def text(path):
    raw=path.read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
def read(name): return json.loads(text(root/name))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def seal(payload,metadata):
    files=[dict(path=p.relative_to(payload).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
           for p in sorted(payload.rglob('*')) if p.is_file()]
    metadata.update(schemaVersion=1,createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    baseCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),files=files)
    (payload/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(payload.name,'files',len(files),'bytes',sum(f['bytes'] for f in files))

for name in ('echo_compare_utf8.json','physical_compare_utf8.json','prepared_01_compare_utf8.json'):
    assert read(name)['Equivalent']
assert read('backup_code_compare.json')['Equivalent'] and read('reproduction.json')['Equal']
assert all(v['Clean'] for v in read('native_log_gates.json').values())
assert 'Ran 1828 tests' in text(root/'ab_suite_01.log') and '\nOK' in text(root/'ab_suite_01.log')
assert 'Ran 29 tests' in text(root/'focused_01.log') and '\nOK' in text(root/'focused_01.log')
assert 'Ran 74 tests' in text(root/'root_tests_01.log') and '\nOK' in text(root/'root_tests_01.log')
assert sha(root/'alarm_02.L5X')=='928E4E81444933E0F70958244F5B0B7B93A5B75F96A2083841B278CDB1A0D2ED'
before=read('before_download_read.json')
assert all(before['configurationReopen'].values()) and not before['echo']['IsFaulted']

prepared=repo/'Specification/AllenBradley/Evidence/AB_NATIVE_ALARM_OBSERVER_PREPARED_2026-10-18'
runtime=repo/'Specification/AllenBradley/Evidence/AB_NATIVE_ALARM_RUNTIME_2026-10-18'
assert not prepared.exists() and not runtime.exists()
prepared.mkdir()
with zipfile.ZipFile(prepared/'source_snapshot.zip','x',zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((repo/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py')):
        archive.write(path,path.relative_to(repo).as_posix())
    for name in ('Specification/Fraktal_Core_Part_I.md','Specification/Fraktal_AB_Part_III.md',
                 'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/Program.cs',
                 'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/Fraktal.Ab.OfflineProbe.csproj'):
        archive.write(repo/name,name)
    archive.write('C:/work/echo38_5580_seed.L5X','echo38_5580_seed.L5X')
with zipfile.ZipFile(prepared/'native_artifacts.zip','x',zipfile.ZIP_DEFLATED) as archive:
    for name in ('timing_reproduced.L5X','alarm_01.L5X','alarm_01_echo.L5X','alarm_02.L5X',
                 'alarm_02_echo.L5X','alarm_02_physical.L5X','prepared_01_readback.L5X','echo_before_alarm.L5X'):
        archive.write(root/name,name)
for folder in ('Logs','Checks','ProbeSources'):
    (prepared/folder).mkdir()
for name in ('focused_01.log','ab_suite_01.log','root_tests_01.log','generation_01.log',
             'generation_02.log','generation_03.log','reproduction.log','compile_echo_01.log',
             'compile_echo_02.log','compile_echo_03.log','compile_physical_01.log','prepare_01.log',
             'backup_01.log','preflight_read.log'):
    shutil.copyfile(root/name,prepared/'Logs'/name)
for name in ('echo_compare_utf8.json','physical_compare_utf8.json','prepared_01_compare_utf8.json',
             'native_log_gates.json','reproduction.json','backup_code_compare.json','before_download_read.json'):
    shutil.copyfile(root/name,prepared/'Checks'/name)
for name in ('Program.cs','AlarmSession.csproj','before_download_read.py','package_evidence.py'):
    shutil.copyfile(root/name,prepared/'ProbeSources'/name)
shutil.copyfile('C:/work/fraktal-echo-deploy-20261018/guard_echo.py',prepared/'ProbeSources/guard_echo.py')
seal(prepared,dict(schema='fraktal.ab.alarm-observer-prepared-evidence',controllerWrites=0,
    runtimeAccepted=False,productionAlarmOwnerChanged=False,fullAbTests=1828,focusedTests=29,rootTests=74,
    recordBytes=880,phases=14,durationPlcSeconds=104,
    generatedSha256=sha(root/'alarm_02.L5X'),preparedAcdSha256=before['preparedAcdSha256'],
    backupSha256=before['backupSha256']))

observation=read('observation_01.json')
live=read('live_01.json')
final=read('final_read.json')
downloaded=read('downloaded_compare.json')
assert observation['BaseComparisonPassed'] and observation['ControllerWrites']==0
assert len(observation['Observation']['Checks'])==22 and all(observation['Observation']['Checks'].values())
assert len(live['rows'])==31 and all(r['passed'] for r in live['rows'])
assert live['restored'] and live['policyRestored'] and not live['configuration']['restoring']
assert downloaded['Equivalent'] and all(final['configurationReopen'].values())
assert not final['echo']['IsFaulted'] and final['echo']['ControllerMode']==1
assert final['alarmObserver']['Done']==1 and final['alarmObserver']['ProbeFault']==0 and final['alarmObserver']['InputBits']==0
audit=audit_log(text(root/'download_01.log'),('Open project','Download','Change Controller Mode','Save','Save As'))
assert audit['Clean'],audit
(root/'download_log_gate.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
runtime.mkdir()
for folder in ('Logs','Checks','ProbeSources'):
    (runtime/folder).mkdir()
for name in ('download_01.log','observation_01.log','live_01.log','final_read.log'):
    shutil.copyfile(root/name,runtime/'Logs'/name)
for name in ('downloaded_compare.json','download_log_gate.json','observation_01.json','live_01.json','final_read.json'):
    shutil.copyfile(root/name,runtime/'Checks'/name)
shutil.copyfile(root/'final_read.py',runtime/'ProbeSources/final_read.py')
with zipfile.ZipFile(runtime/'downloaded_artifact.zip','x',zipfile.ZIP_DEFLATED) as archive:
    archive.write(root/'downloaded_alarm.L5X','downloaded_alarm.L5X')
seal(runtime,dict(schema='fraktal.ab.native-alarm-runtime-evidence',
    authorization=dict(answer='Download, restore and run the checks',serial='601FC87B',
        scope='Prepared replacement image, saved configuration restore, 104-second private native alarm comparison and 31 tower/Part regressions'),
    preparedEvidence=prepared.name+'/manifest.json',productionAlarmOwnerChanged=False,
    productionProjectionAccepted=False,operatorIsolationQualified=False,collectorWrites=0,
    nativeChecks=22,liveRegressions=31,restored=True,policyRestored=True,
    observations=observation['Observation'],nativeScans=observation['Record']['Scans'],
    generatedSha256=sha(root/'alarm_02.L5X'),preparedAcdSha256=before['preparedAcdSha256'],
    downloadedAcdSha256=final['downloadedAcdSha256'],backupSha256=final['backupSha256']))

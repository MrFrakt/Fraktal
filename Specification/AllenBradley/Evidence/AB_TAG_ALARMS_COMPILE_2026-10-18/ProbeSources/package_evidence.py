import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

repo=Path('C:/Users/SoftIndVM/Fraktal')
root=Path('C:/work/fraktal-ab-tag-alarm-20261018')
payload=repo/'Specification/AllenBradley/Evidence/AB_TAG_ALARMS_COMPILE_2026-10-18'
assert not payload.exists()
closure=json.loads((root/'closure.json').read_text())
assert closure['Complete'] and len(closure['Cases'])==12
assert closure['CanonicalReadback']['Equivalent']
assert sum(row['Expected']=='pass' and row['Accepted'] for row in closure['Cases'])==4
assert sum(row['Expected']=='fail' and row['CompilerRejected'] for row in closure['Cases'])==6
assert sum(row['Expected']=='observe' and row['Accepted'] for row in closure['Cases'])==2
def log_text(path):
    raw=path.read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
assert 'Ran 1818 tests' in log_text(root/'ab_tests_final.log') and '\nOK' in log_text(root/'ab_tests_final.log')
assert 'Ran 29 tests' in log_text(root/'focused_tests_qualified.log') and '\nOK' in log_text(root/'focused_tests_qualified.log')
assert 'Ran 74 tests' in log_text(root/'root_tests_final.log') and '\nOK' in log_text(root/'root_tests_final.log')
echo=json.loads(log_text(root/'echo_read_only.log'))
assert echo['SerialNumber']==0x601FC87B and not echo['IsFaulted'] and echo['ControllerMode']==1
payload.mkdir()

with zipfile.ZipFile(payload/'source_snapshot.zip','x',zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((repo/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py')):
        archive.write(path,path.relative_to(repo).as_posix())
    for name in ('Specification/Fraktal_Core_Part_I.md','Specification/Fraktal_AB_Part_III.md',
                 'Specification/AllenBradley/AB_V38_NATIVE_FEATURE_AUDIT_2026-10-18.md',
                 'Specification/AllenBradley/AB_PORT_COMPLETION_PLAN_2026-10-04.md',
                 'Specification/AllenBradley/Evidence/AB_TAG_ALARMS_COMPILE_2026-10-18.md',
                 'FraktalCore/PLC/Allen-Bradley/README.md',
                 'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/Program.cs',
                 'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/Fraktal.Ab.OfflineProbe.csproj'):
        archive.write(repo/name,name)
    archive.write('C:/work/echo38_5580_seed.L5X','echo38_5580_seed.L5X')

with zipfile.ZipFile(payload/'native_artifacts.zip','x',zipfile.ZIP_DEFLATED) as archive:
    paths=[*root.glob('*.L5X'),*root.glob('*.L5K')]
    for directory in ('probes_01','probes_final','probes_qualified','compiled_01',
                      'compiled_final','compiled_access','compiled_discriminator','reproduced'):
        paths.extend((root/directory).glob('*.L5X'))
    for path in sorted(paths):
        archive.write(path,path.relative_to(root).as_posix())

for folder in ('Logs','Checks','ProbeSources'):
    (payload/folder).mkdir()
logs=[*root.glob('*.log'),*root.glob('*.studio.txt'),root/'studio_import_diagnostic.txt']
for directory in ('compiled_01','compiled_final','compiled_access','compiled_discriminator'):
    logs.extend((root/directory).glob('*.log'))
for path in sorted(logs):
    shutil.copyfile(path,payload/'Logs'/path.relative_to(root).as_posix().replace('/','_'))
checks=[*root.glob('*.json')]
for directory in ('probes_01','probes_final','probes_qualified','compiled_01',
                  'compiled_final','compiled_access','compiled_discriminator','reproduced'):
    checks.extend((root/directory).glob('*.json'))
for path in sorted(checks):
    shutil.copyfile(path,payload/'Checks'/path.relative_to(root).as_posix().replace('/','_'))
for name in ('studio_diagnostic.ps1','reference_generation.py','final_checks.py',
             'check_native_metadata.py','package_evidence.py','export_sdk/Program.cs','export_sdk/Export.csproj'):
    shutil.copyfile(root/name,payload/'ProbeSources'/name.replace('/','_'))

files=[dict(path=p.relative_to(payload).as_posix(),bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper())
       for p in sorted(payload.rglob('*')) if p.is_file()]
manifest=dict(schema='fraktal.ab.tag-alarm-compile-evidence',schemaVersion=1,
 createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 baseCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
 controllerWrites=0,runtimeAccepted=False,productionAlarmOwnerChanged=False,
 fullAbTests=1818,finalFocusedTests=29,rootTests=74,positiveBuilds=4,
 negativeCompilerControls=6,acceptedOperatorWriteDiscriminators=2,canonicalBuilds=1,
 nativeMetadataMutationChecks=8,generatedCases=6,files=files)
(payload/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(files),bytes=sum(f['bytes'] for f in files),payload=str(payload)),indent=2))

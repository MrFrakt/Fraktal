from pathlib import Path
import json,hashlib,shutil,uuid
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence';S=E/'AB_R1_R2_CANONICAL_PREPARATION_2026-10-24/Preparation'
OLD='C:/work/fraktal-ab-r1-r2-20261024/prepare_8f74e954758141dd81821a0c1316c2ef'
O=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01');W=O.parent/('prepare_'+uuid.uuid4().hex);W.mkdir()
m=json.loads((S.parent/'manifest.json').read_bytes());pins={a['path']:a['sha256'] for a in m['artifacts']}
changes=[]
for name in ('scripts/guard_echo.py','scripts/preflight.py','ensure_manual.py','final_checks.py','measure_timing.py','audit_baseline_access.py','run_logged.py','gate_dry_check.py','session/Program.cs','session/S3iLifetimeSession.csproj','session/NuGet.Config','runtime_template/start_session.py','runtime_template/candidate_then_restore.py'):
 b=(S/name).read_bytes();assert hashlib.sha256(b).hexdigest()==pins['Preparation/'+name],name
 b=b.replace(OLD.encode(),W.as_posix().encode()).replace(b'echo_before_s3i',b'echo_before_s3j').replace(b's3i_canonical.ACD',b's3j_canonical.ACD').replace(b'S3iLifetimeSession',b'S3jSession')
 target=W/name.replace('S3iLifetimeSession','S3jSession');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 changes.append(dict(path=str(target.relative_to(W)),sourceSha256=pins['Preparation/'+name],copiedSha256=hashlib.sha256(b).hexdigest()))
p=W/'session/Program.cs';s=p.read_bytes().decode();nl='\r\n' if '\r\n' in s else '\n';s=s.replace('\r\n','\n')
s=s.replace('"restore-genealogy","cycle-retained"','"restore-genealogy"')
a=s.index('if (args[0]=="cycle-retained") {');b=s.index('if (args[0]=="backup") {',a);s=s[:a]+s[b:]
s=s.replace('NativeLineVectorsAuthorized','S3jIoVectorsAuthorized')
s=s.replace('        !approved.GetProperty("CalendarLifetimeVectorsAuthorized").GetBoolean() ||\n','').replace('        !approved.GetProperty("RetainedCycleAuthorized").GetBoolean() ||\n','')
p.write_bytes(s.replace('\n',nl).encode())
# Fixed S3j entry points replace the R1/R2 profile wrapper and lifetime phases.
p=W/'runtime_template/candidate_then_restore.py';s=p.read_bytes().decode();nl='\r\n' if '\r\n' in s else '\n';s=s.replace('\r\n','\n')
s=s.replace("W/'s3i_bench_05.L5X'","W/'s3j.L5X'")
s=s.replace("PY, W/'run_candidate.py', 'fixture'","PY, T/'fraktal_ab_s3j_fixture_execute.py'")
a=s.index("    run('calendar_01'");b=s.index("    run('idle_equivalence_01'",a)
s=s[:a]+"""    run('io_vectors_01', PY, T/'fraktal_ab_s3j_io_execute.py', '--execute-fixture', '--expect-serial', '601FC87B',
        '--expect-acd-sha256', (W/'canonical.sha256').read_text().strip(), '--authorization-file', W/'authorization.json', '--output', R/'io_vectors_01.json')
"""+s[b:]
s=s.replace("PY, W/'run_candidate.py', 'equivalence'","PY, T/'fraktal_ab_s3j_equivalence.py'")
p.write_bytes(s.replace('\n',nl).encode())
identity=json.loads((O/'prepared_identity_02.json').read_bytes());pin=identity['acdSha256']
for name in ('s3j_canonical.ACD','capacity_review.ACD'):shutil.copyfile(O/'capacity_final_review.ACD',W/name)
shutil.copyfile(O/'s3j_06.L5X',W/'s3j.L5X');(W/'canonical.sha256').write_bytes((pin+'\n').encode())
shutil.copyfile(O/'audit_access.py',W/'audit_access.py')
# Prior-stage comparison is the accepted R1/R2 exact image, not the rollback project.
base=E/'AB_R1_R2_CANONICAL_PREPARATION_2026-10-24/Offline/capacity_auto_01.json';shutil.copyfile(base,W/'baseline_capacity.json');prior=json.loads(base.read_bytes())
(W/'baseline_reference.json').write_text(json.dumps(dict(capacitySha256=hashlib.sha256(base.read_bytes()).hexdigest().upper(),record=str(base.relative_to(E))),indent=2),encoding='utf-8')
cap=json.loads((O/'capacity_auto_02.json').read_bytes())
for a,b in [('BaselineSha256','CanonicalSha256'),('BaselineUsedStandardBlocks','UsedStandardBlocks'),('BaselineAvailableBlocks','AvailableBlocks'),('BaselineTotalBlocks','TotalBlocks')]:cap[a]=prior[b]
(W/'capacity_review.json').write_text(json.dumps(cap,indent=2),encoding='utf-8')
auth=dict(CurrentOwnerApproved=False,ManualNormalizationAuthorized=False,AccessVectorsAuthorized=False,ConfigurationVectorsAuthorized=False,
 S3jIoVectorsAuthorized=False,FaultClearAuthorized=False,ClockSetAuthorized=False,Serial='601FC87B',CanonicalSha256=pin,
 SourceSha256=identity['sourceSha256'],RuntimeDirectory=None,CandidateRows=41,IoVectorRows=9,IoSourceWrites=80,BaselineRows=31,
 Scope='Prepared S3j session only; current exact-image owner authorization required')
for name in ('authorization.json','authorization.template.json'):(W/name).write_text(json.dumps(auth,indent=2),encoding='utf-8')
for name in ():
 for suffix in ('.log','_exit.json'):shutil.copyfile(O/(name+suffix),W/(name+suffix))
p=W/'runtime_template/start_session.py';s=p.read_bytes()
for name in ('ab_suite','root_tests','ab_spec','ab_contracts','consistency','whitespace'):
 s=s.replace((name+'_03').encode(),(name+'_01').encode()).replace((name+'_04').encode(),(name+'_01').encode())
p.write_bytes(s)
with (W/'setup_01.json').open('x') as f:json.dump(dict(passed=True,byteCopiedPredecessors=changes,explicitChanges=['remove retained/calendar scope and modes','S3j actor and equivalence entry points','exact new image and Capacity bindings'],controllerOperations=0,authorization=False),f,indent=2)
with (O/'native_preparation_location_02.json').open('x') as f:json.dump(dict(workspace=str(W)),f)
print(json.dumps(dict(workspace=str(W),pin=pin,controllerOperations=0,authorization=False)))

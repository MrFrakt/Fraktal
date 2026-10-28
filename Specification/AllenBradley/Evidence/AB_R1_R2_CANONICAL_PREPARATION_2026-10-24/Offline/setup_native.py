from pathlib import Path
import hashlib,json,shutil,uuid
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence'
S=E/'AB_S3I_CANONICAL_LIFETIME_RETRY2_PREPARATION_2026-10-24/Preparation'
P='C:/work/fraktal-ab-s3i-lifetime-20261024/retry2_prepare_8a934eccd6e548aea4d0c1c5a2e06db7'
W=Path('C:/work/fraktal-ab-r1-r2-20261024')/('prepare_'+uuid.uuid4().hex);W.mkdir(parents=True)
O=Path('C:/work/fraktal-ab-s3j-20261024/r1_01')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
seal=json.loads((S.parent/'manifest.json').read_bytes());pins={x['path']:x['sha256'].lower() for x in seal['artifacts']}
copied=[]
for name in ('scripts/guard_echo.py','scripts/preflight.py','scripts/retention_preflight.py','scripts/retention_readiness.py',
             'ensure_manual.py','final_checks.py','measure_timing.py','audit_access.py','audit_baseline_access.py',
             'run_logged.py','test_authorization.py','gate_dry_check.py','session/Program.cs','session/S3iLifetimeSession.csproj',
             'session/NuGet.Config','runtime_template/start_session.py','runtime_template/candidate_then_restore.py'):
 original=(S/name).read_bytes();assert hashlib.sha256(original).hexdigest()==pins['Preparation/'+name],name
 new=original.replace(P.encode(),W.as_posix().encode())
 target=W/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(new)
 assert new==original.replace(P.encode(),W.as_posix().encode())
 copied.append(dict(path=name,sealedSha256=hashlib.sha256(original).hexdigest(),reboundSha256=sha(target),pathRebindings=original.count(P.encode())))
identity=json.loads((O/'prepared_identity_01.json').read_bytes());acd=identity['acdSha256'];source=identity['sourceSha256']
for name in ('s3i_canonical.ACD','capacity_review.ACD','retention_control.ACD'):shutil.copyfile(O/'capacity_review.ACD',W/name);assert sha(W/name).upper()==acd
shutil.copyfile(O/'s3i_r1_r2.L5X',W/'s3i_r1_r2.L5X')
(W/'canonical.sha256').write_bytes((acd+'\n').encode())
# Preserve the accepted S3i measurement as bytes; hash binds the new baseline.
base=E/'AB_S3I_CANONICAL_PREPARATION_2026-10-24/Preparation/capacity_auto_01.json'
if not base.exists():
 candidates=[p for p in (E/'AB_S3I_CANONICAL_PREPARATION_2026-10-24/Preparation').glob('*capacity*.json') if 'UsedStandardBlocks' in p.read_text(encoding='utf-8')]
 base=next(p for p in candidates if json.loads(p.read_bytes()).get('UsedStandardBlocks')==2763512)
shutil.copyfile(base,W/'baseline_capacity.json')
b=json.loads((W/'baseline_capacity.json').read_bytes());assert b['CanonicalSha256']=='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
(W/'baseline_reference.json').write_text(json.dumps(dict(capacitySha256=sha(W/'baseline_capacity.json').upper(),record=str(base.relative_to(E)),canonicalSha256=b['CanonicalSha256']),indent=2),encoding='utf-8')
est=json.loads((O/'capacity_auto_01.json').read_bytes())
for target,key in [('BaselineSha256','CanonicalSha256'),('BaselineUsedStandardBlocks','UsedStandardBlocks'),('BaselineAvailableBlocks','AvailableBlocks'),('BaselineTotalBlocks','TotalBlocks')]:est[target]=b[key]
(W/'capacity_review.json').write_text(json.dumps(est,indent=2),encoding='utf-8')
# The prepared ACD readback has its own fresh strict comparison, added next.
auth=json.loads((S/'authorization.json').read_bytes());assert auth['CurrentOwnerApproved'] is False
for name in list(auth):
 if name.endswith('Authorized'):auth[name]=False
auth.update(CanonicalSha256=acd,SourceSha256=source,RuntimeDirectory=None,
 Scope='Prepared R1+R2 exact-image acceptance; current owner confirmation required',
 CandidateRows=41,BaselineRows=31,MaxCalendarCommits=64,NormalCalendarCommits=38,
 RetainedProgramRunCycles=1,NativeFirstScanVectors=8,NativeFirstScanExecutions=2)
for name in ('authorization.json','authorization.template.json'):(W/name).write_text(json.dumps(auth,indent=2),encoding='utf-8')
profile='''"""Fixed opt-in engineering fixture profile, not a runtime client mapping."""
from dataclasses import replace
from pathlib import Path
import os
CANONICAL_SHA256 = 'PIN'
def configure():
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
    assert (Path(__file__).parent/'canonical.sha256').read_text().strip()==CANONICAL_SHA256
    import fraktal_ab_genealogy_s3i_demo as demo
    if not getattr(demo.application,'r1_r2_profile',False):
        original=demo.application
        def selected():return replace(original(),canonical_type_manifest=True,canonical_table_driven=True)
        selected.r1_r2_profile=True
        demo.application=selected
    import fraktal_ab_s3i_lifetime_execute as lifetime
    lifetime.ACD=CANONICAL_SHA256
'''.replace('PIN',acd)
(W/'candidate_profile.py').write_text(profile,encoding='utf-8')
wrapper='''"""Run only the fixed R1/R2 candidate apparatus; no new write vectors."""
from pathlib import Path
import importlib,os,sys
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from candidate_profile import configure
configure()
mode=sys.argv.pop(1)
if mode=='fixture':
    from fraktal_ab_s3i_fixture_execute import main
elif mode=='lifetime':
    from fraktal_ab_s3i_lifetime_execute import main
elif mode=='equivalence':
    import fraktal_ab_s3i_equivalence as gate
    import fraktal_ab_s2_equivalence as shared
    def main():return shared.main(gate.run,description=gate.__doc__)
else:raise ValueError('fixed candidate mode required')
raise SystemExit(main())
'''
(W/'run_candidate.py').write_text(wrapper,encoding='utf-8')
changes=[]
def change(name,old,new):
 p=W/name;data=p.read_bytes();assert old in data,name;p.write_bytes(data.replace(old,new));changes.append(dict(path=name,old=old.decode(),new=new.decode()))
for name in ('scripts/retention_preflight.py','scripts/retention_readiness.py'):
 change(name,b'import fraktal_ab_s3i_lifetime_execute as fixture',b'sys.path.insert(0,str(W))\nfrom candidate_profile import configure\nconfigure()\nimport fraktal_ab_s3i_lifetime_execute as fixture')
change('audit_access.py',b'app=demo.application()',b'from dataclasses import replace;app=replace(demo.application(),canonical_type_manifest=True,canonical_table_driven=True)')
for module,mode in (('fraktal_ab_s3i_fixture_execute.py','fixture'),('fraktal_ab_s3i_lifetime_execute.py','lifetime'),('fraktal_ab_s3i_equivalence.py','equivalence')):
 change('runtime_template/candidate_then_restore.py',("PY, T/'"+module+"'").encode(),("PY, W/'run_candidate.py', '"+mode+"'").encode())
change('test_authorization.py',b"str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s3i_lifetime_execute.py')",b"str(W/'run_candidate.py'),'lifetime'")
change('runtime_template/start_session.py',b"('ab_suite_01','root_tests_02'",b"('ab_suite_02','root_tests_02'")
(W/'setup_01.json').write_text(json.dumps(dict(passed=True,workspace=str(W),copies=copied,explicitChanges=changes,sourceSha256=source,canonicalSha256=acd,controllerOperations=0,authorization=False),indent=2),encoding='utf-8')
with (O/'native_preparation_location_01.json').open('x') as f:json.dump(dict(workspace=str(W)),f)
print(json.dumps(dict(workspace=str(W),canonicalSha256=acd,baseline=base.name,files=len(copied),changes=len(changes))))

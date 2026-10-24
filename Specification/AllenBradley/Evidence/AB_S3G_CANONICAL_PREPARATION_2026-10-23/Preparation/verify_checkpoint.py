from pathlib import Path
import datetime,gzip,hashlib,json,re,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;E=ROOT/'Specification/AllenBradley/Evidence';sha=lambda raw:hashlib.sha256(raw).hexdigest()
required=('boundary_implications_01','metrics_schema_tests_04','layout_generation_03','layout_generation_05','layout_native_echo_03','layout_native_echo_05','layout_native_physical_05','layout_echo_readback_05','layout_physical_readback_05','layout_echo_log_audit_05','layout_physical_log_audit_05','layout_echo_access_05','layout_physical_access_05','layout_forecast_01','s3f_closing_compatibility_02','ab_suite_01','checkpoint_notes_01')
for label in required:assert json.loads((P/(label+'_exit.json')).read_text())['exitCode']==0,label
match=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(P/'ab_suite_01.log').read_text());assert match and int(match[1])==2118
assert sha((P/'s3f_closing_compatibility_02.L5X').read_bytes()).upper()=='B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3'
source=P/'metrics_layout_probe_05.L5X';targets=[]
for target in ('echo','physical'):
 text=(P/f'layout_native_{target}_05.log').read_text();result=json.loads(text[text.rindex('\n{')+1:])
 assert result['BuildAccepted'] and result['InputUnchanged'] and result['InputSha256'].lower()==sha(source.read_bytes())
 assert json.loads((P/f'layout_{target}_readback_05.log').read_text())['Equivalent']
 assert json.loads((P/f'layout_{target}_access_05.json').read_text())['passed']
 targets.append(result)
R=Path('C:/work/fraktal-ab-s3f-revision-20261023/runtime_9b86612c2f174292a2773260021df32d')
before=json.loads((R/'source_verification_02.json').read_text())['sha256']
added={'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_metrics.py','FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_canonical_metrics.py'}
current={name:sha((ROOT/name).read_bytes()) for name in sorted(set(before)|added)}
changes={name:dict(before=pin,after=current[name]) for name,pin in before.items() if pin!=current[name]}
assert set(changes)=={'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_publication.py'} and len(current)==145
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from dataclasses import replace
import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s3f_demo as demo
app=replace(demo.application(),canonical_publication_stage=9)
assert any('S3g generation is gated' in finding for finding in pub.validate(app))
assert not list(P.rglob('*.ACD')) and not (P/'authorization.json').exists() and not (P/'session').exists()
rows=[]
for path in sorted(E.glob('AB_*/manifest.json')):
 if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL')):continue
 m=json.loads(path.read_text())
 for a in m['artifacts']:
  raw=(path.parent/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256'].lower()
  if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'].lower()
 if m.get('report'):assert sha((E/m['report']).read_bytes())==m['reportSha256'].lower()
 rows.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path.read_bytes())))
assert len(rows)==23 and sum(r['artifacts'] for r in rows)==5032
failed=[dict(label=f.name.removesuffix('_exit.json'),exitCode=json.loads(f.read_text())['exitCode']) for f in sorted(P.glob('*_exit.json')) if json.loads(f.read_text())['exitCode']!=0]
result=dict(passed=True,date='2026-10-23',capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllerAccess=False,controllerChanges=0,fullS3gCandidate=False,runtimeAccepted=False,dependentValuesApproved=False,numericTypePathsApproved=200,pendingDependentValuePaths=224,canonicalPathsAdded=1055,sourceSha256=sha(source.read_bytes()),abTests=2118,abSeconds=float(match[2]),abSourceBindings=145,changedExistingSources=changes,addedSources=sorted(added),sha256=current,nativeTargets=targets,failedRunsRetained=failed,requiredSuccessfulRuns=list(required),priorSeals=rows,predecessorRecords=23,predecessorArtifacts=5032)
with (P/'checkpoint_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('sha256','priorSeals','nativeTargets','requiredSuccessfulRuns')}))

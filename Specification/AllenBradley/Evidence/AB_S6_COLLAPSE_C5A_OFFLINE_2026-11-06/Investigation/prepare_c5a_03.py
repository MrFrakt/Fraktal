"""C5a continuation: reuse hash-bound genealogy builds, complete both profiles. Offline only."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
P=W/'prepare_03';P.mkdir(exist_ok=False);PREVIOUS=W/'prepare_02'
OLD=Path('C:/work/fraktal-ab-s6-host-20261104/prepare')
SDK=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
PREPARE=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe')
SEED=Path('C:/work/echo38_5580_seed.L5X');PY=sys.executable
exits={};pins={};result={};assert PREPARE.is_file()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(label,*args):
 code=subprocess.run([PY,str(W/'run_logged_02.py'),label,str(R),*map(str,args)],cwd=R).returncode
 exits[label]=code
 if code:raise RuntimeError(label+' failed')
try:
 for name,declaration in [('genealogy','fraktal_ab_genealogy_s6_collapse_demo'),('press','fraktal_ab_press_s6_collapse_echo38')]:
  source=P/(name+'.L5X')
  if name=='genealogy':
   assert sha(PREVIOUS/'genealogy.L5X')=='5557604A02885ECE5C67392B552F41F15FDC9B747ED139E275D987064273A95A'
   shutil.copyfile(PREVIOUS/'genealogy.L5X',source)
  else:run('generate_'+name+'_03',PY,T/'fraktal_ab_generate.py',SEED,source,'--declaration',declaration)
  pins[name]=dict(sourceSha256=sha(source),declaration=declaration)
  run('bool_scan_'+name+'_03',PY,T/'fraktal_ab_st_bool_operands.py',source)
  for target in ('EchoController','PhysicalController'):
   back=(PREVIOUS if name=='genealogy' else P)/(name+'_'+target+'_readback.L5X')
   if name=='genealogy':
    for prior in ('build_','readback_','sdk_audit_','access_'):
     assert json.loads((W/(prior+name+'_'+target+'_02_exit.json')).read_bytes())['exitCode']==0
    pins[name].setdefault('reusedReadbacks',[]).append(dict(target=target,path=str(back),sha256=sha(back)))
   else:
    label='build_'+name+'_'+target+'_03'
    run(label,SDK,'--build-readback',source,back,target)
    run('readback_'+name+'_'+target+'_03',PY,T/'fraktal_ab_readback.py',source,back)
    run('sdk_audit_'+name+'_'+target+'_03',PY,T/'fraktal_ab_sdk_log_gate.py',W/(label+'.log'),'--require','Open project','--require','Build','--require','Save As')
   run('access_'+name+'_'+target+'_03',PY,W/'audit_access_c5a_03.py',back,P/('access_'+name+'_'+target+'.json'),declaration)
  acd=P/(name+'.ACD');back=P/(name+'_prepared_readback.L5X')
  run('prepare_acd_'+name+'_03',PREPARE,source,acd,back)
  run('prepared_compare_'+name+'_03',PY,T/'fraktal_ab_readback.py',source,back)
  run('prepared_sdk_audit_'+name+'_03',PY,T/'fraktal_ab_sdk_log_gate.py',W/('prepare_acd_'+name+'_03.log'),'--require','Open project','--require','Build','--require','Save As')
  pins[name]['acdSha256']=sha(acd)
  review=P/(name+'_capacity_review.ACD');shutil.copyfile(acd,review)
  run('capacity_'+name+'_03',PY,T/'fraktal_ab_studio_capacity.py','--acd',review,'--expect-sha256',sha(acd),'--output',P/(name+'_capacity.json'),'--capture-output',P/(name+'_capacity_capture.json'))
  assert sha(acd)==pins[name]['acdSha256']
 for declaration,oldname in [('fraktal_ab_genealogy_s6_host_demo','s6_host_legacy_17.L5X'),('fraktal_ab_press_canonical_echo38','press_canonical_legacy_17.L5X')]:
  out=P/(declaration+'.L5X')
  run('legacy_'+declaration+'_03',PY,T/'fraktal_ab_generate.py',SEED,out,'--declaration',declaration)
  identical=sha(out)==sha(OLD/oldname)
  pins[declaration]=dict(sourceSha256=sha(out),byteIdentical=identical)
  assert identical,'legacy image changed: '+declaration
 result=dict(passed=True)
except BaseException as error:result=dict(passed=False,error=type(error).__name__+': '+str(error))
finally:
 result.update(exits=exits,pins=pins,controllerAccess=False,downloads=0)
 with (W/'prepare_c5a_03.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)

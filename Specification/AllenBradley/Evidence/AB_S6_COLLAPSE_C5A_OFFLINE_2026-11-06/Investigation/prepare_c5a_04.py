"""C5a continuation: complete missing press steps; hash-bind successful earlier outputs."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';PY=sys.executable
P=W/'prepare_04';P.mkdir(exist_ok=False);S=W/'prepare_03';G=W/'prepare_02'
SDK=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
PREPARE=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe')
OLD=Path('C:/work/fraktal-ab-s6-host-20261104/prepare');pins=json.loads((W/'prepare_c5a_03.json').read_bytes())['pins'];exits={};result={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(label,*args):
 code=subprocess.run([PY,str(W/'run_logged_02.py'),label,str(R),*map(str,args)],cwd=R).returncode
 exits[label]=code
 if code:raise RuntimeError(label+' failed')
try:
 for name in ('genealogy','press'):assert sha(S/(name+'.L5X'))==pins[name]['sourceSha256']
 for label in ('build_genealogy_EchoController_02','build_genealogy_PhysicalController_02','build_press_EchoController_03','prepare_acd_genealogy_03','prepared_compare_genealogy_03','prepared_sdk_audit_genealogy_03','capacity_genealogy_03'):
  assert json.loads((W/(label+'_exit.json')).read_bytes())['exitCode']==0
 back=P/'press_PhysicalController_readback.L5X'
 run('build_press_PhysicalController_04',SDK,'--build-readback',S/'press.L5X',back,'PhysicalController')
 run('readback_press_PhysicalController_04',PY,T/'fraktal_ab_readback.py',S/'press.L5X',back)
 run('sdk_audit_press_PhysicalController_04',PY,T/'fraktal_ab_sdk_log_gate.py',W/'build_press_PhysicalController_04.log','--require','Open project','--require','Build','--require','Save As')
 for name,decl in [('genealogy','fraktal_ab_genealogy_s6_collapse_demo'),('press','fraktal_ab_press_s6_collapse_echo38')]:
  for target in ('EchoController','PhysicalController'):
   directory=G if name=='genealogy' else P if target=='PhysicalController' else S
   back=directory/(name+'_'+target+'_readback.L5X')
   run('access_'+name+'_'+target+'_04',PY,W/'audit_access_c5a_04.py',back,P/('access_'+name+'_'+target+'.json'),decl)
   pins[name].setdefault('qualifiedReadbacks',[]).append(dict(target=target,path=str(back),sha256=sha(back)))
 acd=P/'press.ACD';back=P/'press_prepared_readback.L5X'
 run('prepare_acd_press_04',PREPARE,S/'press.L5X',acd,back)
 run('prepared_compare_press_04',PY,T/'fraktal_ab_readback.py',S/'press.L5X',back)
 run('prepared_sdk_audit_press_04',PY,T/'fraktal_ab_sdk_log_gate.py',W/'prepare_acd_press_04.log','--require','Open project','--require','Build','--require','Save As')
 pins['press']['acdSha256']=sha(acd)
 review=P/'press_capacity_review.ACD';shutil.copyfile(acd,review)
 run('capacity_press_04',PY,T/'fraktal_ab_studio_capacity.py','--acd',review,'--expect-sha256',sha(acd),'--output',P/'press_capacity.json','--capture-output',P/'press_capacity_capture.json')
 assert sha(acd)==pins['press']['acdSha256']
 for declaration,oldname in [('fraktal_ab_genealogy_s6_host_demo','s6_host_legacy_17.L5X'),('fraktal_ab_press_canonical_echo38','press_canonical_legacy_17.L5X')]:
  out=P/(declaration+'.L5X')
  run('legacy_'+declaration+'_04',PY,T/'fraktal_ab_generate.py','C:/work/echo38_5580_seed.L5X',out,'--declaration',declaration)
  same=sha(out)==sha(OLD/oldname)
  pins[declaration]=dict(sourceSha256=sha(out),byteIdentical=same)
  assert same,'legacy output differs'
 result=dict(passed=True)
except BaseException as e:result=dict(passed=False,error=type(e).__name__+': '+str(e))
finally:
 result.update(exits=exits,pins=pins,controllerAccess=False,downloads=0)
 with (W/'prepare_c5a_04.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)

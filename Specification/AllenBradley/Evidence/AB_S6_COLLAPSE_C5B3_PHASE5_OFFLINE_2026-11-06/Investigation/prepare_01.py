from pathlib import Path
import hashlib,json,shutil,subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';P=W/'prepare_01';PY=sys.executable
SDK=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
PREPARE=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe')
DEFAULTS=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C4C_OFFLINE_2026-11-06/Investigation/audit_storage_readback_01.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
exits=[];profiles={}
def run(label,*args):
 done=subprocess.run([PY,str(W/'run_logged.py'),label,str(R),*map(str,args)])
 exits.append(dict(label=label,exitCode=done.returncode));assert done.returncode==0,label
try:
 P.mkdir(exist_ok=False)
 for prefix,decl_name in (('press','fraktal_ab_press_s6_collapse_echo38'),('shelving','fraktal_ab_press_s6_shelving_echo38')):
  source=P/(prefix+'.L5X');shutil.copyfile(W/(prefix+'_01.L5X'),source)
  pins=dict(declaration=decl_name,sourceSha256=sha(source),readbacks=[])
  for target in ('EchoController','PhysicalController'):
   back=P/(prefix+'_'+target+'_readback.L5X')
   run(prefix+'_build_'+target+'_01',SDK,'--build-readback',source,back,target)
   run(prefix+'_readback_'+target+'_01',PY,T/'fraktal_ab_readback.py',source,back)
   run(prefix+'_sdk_'+target+'_01',PY,T/'fraktal_ab_sdk_log_gate.py',W/(prefix+'_build_'+target+'_01.log'),'--require','Open project','--require','Build','--require','Save As')
   run(prefix+'_access_'+target+'_01',PY,W/'audit_access_02.py',back,P/(prefix+'_'+target+'_access_01.json'),decl_name)
   run(prefix+'_defaults_'+target+'_01',PY,DEFAULTS,source,back,P/(prefix+'_'+target+'_defaults_01.json'))
   pins['readbacks'].append(dict(target=target,sha256=sha(back)))
  acd=P/(prefix+'.ACD');back=P/(prefix+'_prepared_readback.L5X')
  run(prefix+'_prepare_acd_01',PREPARE,source,acd,back)
  run(prefix+'_prepared_compare_01',PY,T/'fraktal_ab_readback.py',source,back)
  run(prefix+'_prepared_sdk_01',PY,T/'fraktal_ab_sdk_log_gate.py',W/(prefix+'_prepare_acd_01.log'),'--require','Open project','--require','Build','--require','Save As')
  pins['acdSha256']=sha(acd)
  review=P/(prefix+'_capacity_review.ACD');shutil.copyfile(acd,review)
  run(prefix+'_capacity_01',PY,T/'fraktal_ab_studio_capacity.py','--acd',review,'--expect-sha256',sha(acd),'--output',P/(prefix+'_capacity.json'),'--capture-output',P/(prefix+'_capacity_capture.json'))
  assert sha(acd)==pins['acdSha256']
  profiles[prefix]=pins
 result=dict(passed=True)
except BaseException as error:result=dict(passed=False,error=type(error).__name__+': '+str(error))
finally:
 result.update(exits=exits,profiles=profiles,controllerAccess=False,downloads=0)
 with (W/'preparation_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
 print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)

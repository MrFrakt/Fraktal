from pathlib import Path
import hashlib,json,shutil,subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';P=W/'prepare_01';PY=sys.executable
SDK=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
PREPARE=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe')
AUDIT=W/'audit_access_02.py'
DEFAULTS=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C4C_OFFLINE_2026-11-06/Investigation/audit_storage_readback_01.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
rows=[];exits=[]
def run(label,*args):
 done=subprocess.run([PY,str(W/'run_logged.py'),label,str(R),*[str(a) for a in args]])
 exits.append(dict(label=label,exitCode=done.returncode));assert done.returncode==0,label
try:
 source=P/'press.L5X';pins=dict(profile='press',sourceSha256=sha(source),readbacks=[])
 for target in ('EchoController','PhysicalController'):
  back=P/('press_'+target+'_readback.L5X')
  if not back.exists():
   run('build_press_'+target+'_02',SDK,'--build-readback',source,back,target)
  run('readback_press_'+target+'_02',PY,T/'fraktal_ab_readback.py',source,back)
  run('sdk_audit_press_'+target+'_02',PY,T/'fraktal_ab_sdk_log_gate.py',W/('build_press_'+target+('_01.log' if target=='EchoController' else '_02.log')),'--require','Open project','--require','Build','--require','Save As')
  run('access_press_'+target+'_02',PY,AUDIT,back,P/('press_'+target+'_access_02.json'),'fraktal_ab_press_s6_collapse_echo38')
  run('defaults_press_'+target+'_02',PY,DEFAULTS,source,back,P/('press_'+target+'_defaults_02.json'))
  pins['readbacks'].append(dict(target=target,sha256=sha(back)))
 acd=P/'press.ACD';back=P/'press_prepared_readback.L5X'
 run('prepare_acd_press_01',PREPARE,source,acd,back)
 run('prepared_compare_press_01',PY,T/'fraktal_ab_readback.py',source,back)
 run('prepared_sdk_audit_press_01',PY,T/'fraktal_ab_sdk_log_gate.py',W/'prepare_acd_press_01.log','--require','Open project','--require','Build','--require','Save As')
 pins['acdSha256']=sha(acd)
 review=P/'press_capacity_review.ACD';shutil.copyfile(acd,review)
 run('capacity_press_01',PY,T/'fraktal_ab_studio_capacity.py','--acd',review,'--expect-sha256',sha(acd),'--output',P/'press_capacity.json','--capture-output',P/'press_capacity_capture.json')
 assert sha(acd)==pins['acdSha256']
 rows.append(pins);result=dict(passed=True)
except BaseException as e:result=dict(passed=False,error=type(e).__name__+': '+str(e))
finally:
 result.update(exits=exits,pins=rows,controllerAccess=False,downloads=0)
 with (W/'prepare_press_02.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)

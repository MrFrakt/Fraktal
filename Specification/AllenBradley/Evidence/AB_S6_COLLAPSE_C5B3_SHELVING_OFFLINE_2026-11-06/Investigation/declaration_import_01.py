from pathlib import Path
import json,os,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
env=dict(os.environ,FRAKTAL_AB_DECLARATION='fraktal_ab_press_s6_shelving_echo38')
code='''import json
import fraktal_ab_press_execute as press
import fraktal_ab_phase6_shelving_execute as shelving
import fraktal_ab_phase6_access_execute as access
app=press.APP
assert app.system_health.require_controller_metrics
assert app.canonical_collapse and app.canonical_host_services
assert shelving.APP==app and access.APP==app
assert shelving.STANDING==app.reasons['CONTROLLER_METRICS_UNAVAILABLE']==21
print(json.dumps(dict(passed=True,root=app.name,reason=shelving.STANDING,controllerMetricsRequired=True,fixtureSurfaces=len(app.fixture_observation),controllerAccess=False,credentialsRead=False)))
'''
done=subprocess.run([sys.executable,'-c',code],cwd=T,env=env,capture_output=True,text=True)
assert done.returncode==0,done.stderr
result=json.loads(done.stdout)
with (W/'declaration_import_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result))

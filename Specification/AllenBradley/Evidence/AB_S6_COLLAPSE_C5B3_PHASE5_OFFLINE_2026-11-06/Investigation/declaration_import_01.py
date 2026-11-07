from pathlib import Path
import json,os,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
records={}
for decl_name,expect_metrics in (('fraktal_ab_press_s6_collapse_echo38',False),('fraktal_ab_press_s6_shelving_echo38',True)):
 env=dict(os.environ,FRAKTAL_AB_DECLARATION=decl_name)
 code=f'''import json
import fraktal_ab_press_execute as press
import fraktal_ab_phase5_execute as phase5
import fraktal_ab_phase6_shelving_execute as shelving
import fraktal_ab_phase6_access_execute as access
import fraktal_ab_fixture_observation as fo
app=press.APP
assert bool(app.system_health.require_controller_metrics) is {expect_metrics}
assert app.canonical_collapse and app.canonical_host_services
assert phase5.APP==app and shelving.APP==app and access.APP==app
assert shelving.STANDING==app.reasons['CONTROLLER_METRICS_UNAVAILABLE']==21
assert len(fo.facts(app))==141
print(json.dumps(dict(passed=True,declaration={decl_name!r},root=app.name,reason=shelving.STANDING,controllerMetricsRequired=bool(app.system_health.require_controller_metrics),fixtureSurfaces=len(app.fixture_observation),fixtureFacts=len(fo.facts(app)),controllerAccess=False,credentialsRead=False)))
'''
 done=subprocess.run([sys.executable,'-c',code],cwd=T,env=env,capture_output=True,text=True)
 assert done.returncode==0,done.stderr
 records[decl_name]=json.loads(done.stdout)
result=dict(passed=True,profiles=records,controllerAccess=False,credentialsRead=False)
with (W/'declaration_import_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result))

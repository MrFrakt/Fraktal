from pathlib import Path
import ast,hashlib,json,subprocess,sys
from types import SimpleNamespace as NS
from unittest.mock import patch
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_press_s6_collapse_echo38 as profile
import test_fraktal_ab_fixture_reads as replay
import fraktal_ab_phase6_shelving_execute as fixture
import fraktal_ab_phase6_access_execute as users
import fraktal_ab_fixture_reads as views
app=profile.application();label,pair=next((name,pair) for name,pair in replay.pairs() if name.startswith('idle_equivalence'))
extra=pair['legacyInputs']['additional'];active=extra['alarmActive'];ring=extra['alarmRing'];state=extra['accessState']
raw=subprocess.check_output(['git','show','f68314e3b:FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase6_shelving_execute.py'],cwd=R)
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='read_rows')
namespace=dict(vars(fixture),APP=app,projection=NS(read_alarm_log=lambda comm:(active,ring),read_access=lambda comm:state))
exec(compile(ast.Module(body=[node],type_ignores=[]),'<parent read_rows>','exec'),namespace)
old=namespace['read_rows'](object())
session=replay.from_pair(pair)
with patch.object(fixture,'APP',app),patch.object(users,'APP',app),patch.object(views,'_session',return_value=session):new=fixture.read_rows(object())
assert [row['passed'] for row in old]==[False,True]
assert old==new
result=dict(passed=True,analysisOnly=True,candidateEligibleForNativeShelving=False,unchangedPreflightVerdicts=[r['passed'] for r in new],preflightRows=new,controllerMetricsRequired=app.system_health.require_controller_metrics,requiredStandingReason=app.reasons['CONTROLLER_METRICS_UNAVAILABLE'],acceptedIdleCapture=label,acceptedIdleActiveReasonCodes=[code for i,code in enumerate(active['ActReasonCode']) if code and active['ActState'][i]!=fixture.gen.ALARM_CLOSED],conclusion='The original and migrated guard both refuse this press image. Prepare a dedicated acceptance profile/event precondition before positive native shelving acceptance; do not relax the guard or change the base press metrics exclusion.',controllerAccess=False)
with (W/'shelving_eligibility_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,nativeEligible=False,parentAndMigratedVerdictsEqual=True,preflightVerdicts=result['unchangedPreflightVerdicts'])))

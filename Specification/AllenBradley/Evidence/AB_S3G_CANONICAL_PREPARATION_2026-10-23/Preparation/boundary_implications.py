"""Pure counterexamples for dependent values omitted by the type-only list."""
from pathlib import Path
import json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_projection as legacy
import fraktal_ab_genealogy_s3f_demo as demo
import fraktal_ab_generate as gen
app=demo.application()
old=legacy.oee_factors(4294967296,0,0,0,1000)
# Core ST_Oee's RunMs is UDINT. At this exact wrap RunMs=0 and no
# factor is valid. These Boolean changes are independent of float rounding.
new=legacy.oee_factors(0,0,0,0,1000)
bool_changes={k:dict(legacy=old[k],core=new[k]) for k in old if type(old[k]) is bool and old[k]!=new[k]}
assert bool_changes=={'AvailValid':{'legacy':True,'core':False},'PerfValid':{'legacy':True,'core':False},'OeeValid':{'legacy':True,'core':False}}
count=-2147483648;unsigned=count&0xffffffff
assert (count>0) is False and (unsigned>0) is True
paths=[app.name+'/Oee/'+k for k in ('AvailValid','PerfValid','QualValid','OeeValid')]
paths += [f'{app.name}/OeeTrend[{i}]/OeeValid' for i in range(1,gen.OEE_SAMPLES+1)]
paths += [f'{app.name}/Profiler/StepStats[{i}]/{k}' for i in range(1,gen.PROFILE_STEPS+1) for k in ('Id','Label','TimeClass','Avg','Maximum')]
inventory=json.loads((ROOT/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json').read_text())
approved={p for p,r in inventory['paths'].items() if r['ownerApprovalRequired']}
assert len(paths)==224 and not set(paths)&approved and set(paths)<=set(inventory['paths'])
result=dict(passed=True,controllerAccess=False,productionSourceChanges=False,acceptedTypePaths=200,dependentValuePaths=224,allAffectedPaths=424,booleanPaths=64,profilerDependentPaths=160,paths=paths,oeeWrapCounterexample=dict(legacyRunMs=4294967296,coreRunMs=0,good=0,nok=0,idealCycleMs=1000,booleanChanges=bool_changes),profilerCounterexample=dict(nativeDintCount=count,coreUInt32Count=unsigned,legacyVisited=count>0,coreVisited=unsigned>0,owningSource='fraktal_ab_projection.profiler_status: visited predicate and ST_TimingRow.Count : UDINT'),scope='Exact dependent values only; no further type/bound changes, tolerance or ignored path')
with (P/'boundary_implications_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='paths'}))

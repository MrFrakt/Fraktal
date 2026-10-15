import json,os,sys,shutil
from pathlib import Path
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Siemens/tools'))
from fraktal_tia_program_layout import group
stations=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations'
result={}
shutil.copy2(WORK/'candidate_05/38_ConfigBenchRoutines.scl',WORK/'candidate_07/38_ConfigBenchRoutines.scl')
for name,old,new,project in [('runtime','candidate_05','candidate_07','Sequence_Diagnostics_Runtime_20261014'),('press','press_02','press_04','Sequence_Diagnostics_Press_Offline_20261014')]:
    plan=['open-project --path "'+str(stations/project/'FrkS12/FrkS12.ap20')+'"'];changed=[]
    for p in sorted((WORK/new).iterdir()):
        if p.suffix not in ('.scl','.udt','.db','.xml'):continue
        previous=(WORK/old/p.name).read_bytes();current=p.read_bytes()
        if previous==current:continue
        assert p.name.startswith(('20_','35_')) or p.name in ('23_PersistQuiesce.scl','29_PersistQuiesce.scl','29_FB_PressDemoUnit.scl'),p.name
        assert p.suffix=='.scl'
        changed.append(p.name)
        plan.append('import-sources --plc PLC_1 --dir "'+str(p.parent)+'" --only "'+p.name+'" --group "'+group(p.name,current.decode('ascii'))+'"')
    assert changed
    plan+=['compile --plc PLC_1','export --plc PLC_1 --out "'+str(WORK/(name+'_export_final'))+'" --scl true','save']
    (WORK/(name+'_patch.plan')).write_text('\n'.join(plan)+'\n',encoding='ascii')
    result[name]=changed
(WORK/'26_patch_scope.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
print(json.dumps(result))

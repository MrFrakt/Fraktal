import os,shutil
from pathlib import Path
w=Path(__file__).resolve().parent
shutil.copy2(w/'candidate_07/38_ConfigBenchRoutines.scl',w/'candidate_08/38_ConfigBenchRoutines.scl')
changed=[]
for p in (w/'candidate_08').iterdir():
    if p.suffix in ('.scl','.udt','.db') and p.read_bytes()!=(w/'candidate_07'/p.name).read_bytes():changed.append(p.name)
assert set(changed)=={'08_GDB_SequenceQuiesceTest.db','39h_SequenceQuiesceBench.scl'},changed
project=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Sequence_Diagnostics_Runtime_20261014/FrkS12/FrkS12.ap20'
plan=['open-project --path "'+str(project)+'"']
for name in sorted(changed):
    plan+=['import-sources --plc PLC_1 --dir "'+str(w/'candidate_08')+'" --only "'+name+'" --group "Tests/ConfigBench/Fixtures"']
plan+=['compile --plc PLC_1','export --plc PLC_1 --out "'+str(w/'runtime_export_qualified')+'" --scl true','save']
(w/'observation.plan').write_text('\n'.join(plan)+'\n',encoding='ascii')
print(changed)

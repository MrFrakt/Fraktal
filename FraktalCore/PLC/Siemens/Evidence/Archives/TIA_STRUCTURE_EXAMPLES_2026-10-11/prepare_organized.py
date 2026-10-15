from pathlib import Path
import os, sys, shutil, hashlib, json, re
sys.path.insert(0,str(Path('FraktalCore/PLC/Siemens/tools').resolve()))
import fraktal_tia_examples as EX
import fraktal_tia_program_layout as LAYOUT
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
station=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations'
source=station/'Config_Runtime_20261011/FrkS12'
target=station/'Organized_Runtime_20261011/FrkS12'
if not target.exists():shutil.copytree(source,target)
hashes={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
assert all(hashlib.sha256((target/p).read_bytes()).hexdigest()==v for p,v in hashes.items())
(w/'12_runtime_project_copy.json').write_bytes((json.dumps(hashes,indent=2)+'\n').encode('ascii'))
EX.generate(w/'candidate_05')
baseline=w.parent/'Config_Transactions_20261011/package_v6'
merged=w/'merged_05'
shutil.copytree(baseline,merged)
main,routines=LAYOUT.split_main((merged/'40_Main.scl').read_text('ascii'))
(merged/'40_Main.scl').write_bytes(main.encode('ascii'))
(merged/'38_ConfigBenchRoutines.scl').write_bytes(routines.encode('ascii'))
def names(text):return set(re.findall(r'^(?:TYPE|FUNCTION_BLOCK|FUNCTION|DATA_BLOCK|ORGANIZATION_BLOCK)\s+"(\w+)"',text,re.M))
owned=set().union(*(names(p.read_text('ascii')) for p in baseline.iterdir() if p.suffix in ('.scl','.udt','.db')))
added=[]
for p in sorted((w/'candidate_05').iterdir()):
    if p.suffix not in ('.scl','.udt','.db','.xml'):continue
    text=p.read_text('ascii');declared=names(text)
    if p.suffix=='.xml':declared={re.search(r'<Name>(\w+)</Name>',text)[1]}
    if declared & owned:
        assert declared <= owned,(p.name,declared-owned)
        continue
    assert declared,(p.name,'missing declaration')
    filename=p.name
    if (merged/filename).exists():filename='06_Example_'+filename
    shutil.copy2(p,merged/filename);added.extend(sorted(declared))
inventory=LAYOUT.organize(merged,w/'grouped_station_05',target/'FrkS12.ap20',w/'export_station_05')
plan=w/'grouped_station_05/import.plan'
lines=plan.read_text('ascii').splitlines()
lines.insert(1,'export --plc PLC_1 --out "'+str(w/'export_station_before')+'" --scl true')
plan.write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
(w/'12_merge.json').write_bytes((json.dumps({'added_unwired':added,'baseline_objects':len(owned),'source_files':len(inventory),'main_calls':re.findall(r'"(\w+)"\(',main)},indent=2)+'\n').encode('ascii'))
print(json.dumps({'source_files':len(inventory),'unwired_objects':len(added),'project':str(target/'FrkS12.ap20')}))

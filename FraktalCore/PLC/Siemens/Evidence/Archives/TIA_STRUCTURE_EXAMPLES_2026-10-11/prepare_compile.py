from pathlib import Path
import os,shutil,hashlib,json
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
s=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Config_Verify_20261011/FrkS12'
t=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Examples_Verify_20261011/FrkS12'
assert s.is_dir() and not t.exists()
shutil.copytree(s,t)
checks={p.relative_to(s).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in s.rglob('*') if p.is_file()}
assert all(hashlib.sha256((t/p).read_bytes()).hexdigest()==v for p,v in checks.items())
(w/'01_project_copy.json').write_bytes((json.dumps(checks,indent=2)+'\n').encode('ascii'))
base=w/'candidate_01'
(base/'29_Composition.scl').write_bytes(b'''FUNCTION "F_PressDemoComposition" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT Startup : Bool; END_VAR
BEGIN
    // Unwired examples: the owner chooses and attaches sequence/release renditions.
END_FUNCTION
ORGANIZATION_BLOCK "Main"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT Initial_Call : Bool; Remanence : Bool; END_VAR
BEGIN
    "F_PressDemoComposition"(Startup := #Initial_Call);
END_ORGANIZATION_BLOCK
''')
lines=['open-project --path "'+str(t/'FrkS12.ap20')+'"','delete-blocks --plc PLC_1','import-sources --plc PLC_1 --dir "'+str(base)+'"']
for p in sorted(base.glob('*.xml')):lines.append('import-xml --plc PLC_1 --file "'+str(p)+'"')
lines+=['compile --plc PLC_1','export --plc PLC_1 --out "'+str(w/'export_01')+'" --scl true','save']
(w/'02_compile.plan').write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
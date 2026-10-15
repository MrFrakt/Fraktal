from pathlib import Path
import os,sys,shutil,hashlib,json,subprocess
root=Path('C:/Projects/Fraktal');binding=root/'FraktalCore/PLC/Siemens'
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
target=binding/'Evidence/Archives/TIA_STRUCTURE_EXAMPLES_2026-10-11'
assert not target.exists()
target.mkdir()
for p in w.iterdir():
    if p.is_file() and p.suffix in ('.py','.plan','.log','.jsonl','.json'):
        shutil.copy2(p,target/p.name)
for name in ('export_station_before','export_station_verified','grouped_station_07'):
    shutil.copytree(w/name,target/name)
snap=target/'SourceSnapshot'
for relative in ('Framework/Core','Framework/Modules','Examples/PressDemo','Tests/Config'):
    source=binding/relative;out=snap/'FraktalCore/PLC/Siemens'/relative
    shutil.copytree(source,out,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ('fraktal_tia_examples.py','fraktal_tia_ld.py','fraktal_tia_graph.py','fraktal_tia_program_layout.py',
             'fraktal_tia_evidence.py','fraktal_tia_generate.py','fraktal_tia_binding.py','fraktal_tia_declaration.py',
             'tia_lint.py','test_fraktal_tia_examples.py'):
    out=snap/'FraktalCore/PLC/Siemens/tools'/name;out.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(binding/'tools'/name,out)
for relative in ('FraktalCore/PLC/Siemens/tools/TiaCli/Program.cs','FraktalCore/PLC/Siemens/README.md',
                 'Specification/Siemens/README.md','Specification/Fraktal_TIA_Part_IV.md','AGENTS.md'):
    out=snap/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/relative,out)
report=root/'Specification/Siemens/Evidence/TIA_STRUCTURE_EXAMPLES_2026-10-11.md'
shutil.copy2(report,target/report.name)
knowledge=target/'KnowledgeSnapshot'
for name in ('program-groups-and-press-examples.md','INDEX.md'):
    out=knowledge/'tia-automation'/name;out.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path('C:/Projects/SiemensAgent/siemens-kb/tia-automation')/name,out)
for name in ('MEMORY.md','project-siemens-port.md','feedback-siemens-sfc-st-no-ld.md'):
    out=knowledge/'memory'/name;out.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path('C:/Users/Siemens/.claude/projects/c--Projects-Fraktal/memory')/name,out)
rows=[];total=0
for p in sorted(target.rglob('*')):
    if p.is_file():
        data=p.read_bytes();total+=len(data)
        rows.append(hashlib.sha256(data).hexdigest()+'  '+p.relative_to(root).as_posix())
(target/'SHA256SUMS').write_bytes(('\n'.join(rows)+'\n').encode('ascii'))
for line in rows:
    expected,path=line.split('  ',1)
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==expected,path
result={'sha256_bindings':len(rows),'bound_bytes':total,'archive':target.relative_to(root).as_posix()}
(w/'34_freeze_verified.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('ascii'))
print(json.dumps(result))

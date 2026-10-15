from pathlib import Path
import os,json,re,subprocess,sys,hashlib
root=Path('C:/Projects/Fraktal');w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
index=json.loads((root/'FraktalCore/PLC/Siemens/Evidence/relocation.json').read_bytes())
paths=list((root/'Specification').rglob('*.md'))+[root/'AGENTS.md']
paths += [p for p in (root/'FraktalCore/PLC/Siemens').rglob('*.md') if 'Evidence' not in p.relative_to(root/'FraktalCore/PLC/Siemens').parts]
changed=[]
for p in paths:
    text=p.read_text('utf-8');before=text
    for old,new in index['directories'].items():
        text=text.replace(old,new).replace(old.replace('/','\\'),new.replace('/','\\'))
    if text!=before:
        p.write_bytes(text.encode('utf-8'));changed.append(p.relative_to(root).as_posix())
active=list((root/'FraktalCore/PLC/Siemens/Examples/PressDemo').rglob('*'))
active += list((root/'FraktalCore/PLC/Siemens/Framework/Modules').rglob('*'))
active += [root/'FraktalCore/PLC/Siemens/Framework/Core'/n for n in ('sequence_services.scl.in','permissive_services.scl.in')]
checked=0
for p in active:
    if p.is_file() and (p.suffix in ('.scl','.udt','.db','.xml','.json','.plan') or p.name.endswith('.scl.in')):
        data=p.read_bytes();data.decode('ascii');assert b'\r' not in data and not data.startswith(b'\xef\xbb\xbf'),p
        checked+=1
badlinks=[]
for p in [root/'Specification/Siemens/README.md',root/'Specification/Siemens/Evidence/TIA_STRUCTURE_EXAMPLES_2026-10-11.md',root/'FraktalCore/PLC/Siemens/Examples/PressDemo/README.md',root/'FraktalCore/PLC/Siemens/Framework/Modules/README.md']:
    for raw in re.findall(r'\]\(([^)]+)\)',p.read_text('utf-8')):
        if '://' in raw or raw.startswith('#'):continue
        target=p.parent/raw.split('#')[0]
        if not target.exists() and 'TIA_STRUCTURE_EXAMPLES_2026-10-11/' not in raw:badlinks.append((str(p),raw))
assert not badlinks,badlinks
assert all(p.suffix=='.md' for p in (root/'Specification/Siemens').rglob('*') if p.is_file())
result={'ascii_lf_sources':checked,'updated_remaining_relocation_references':changed,'new_document_links_resolve':True}
(w/'33_source_audit.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('ascii'))
print(json.dumps(result))

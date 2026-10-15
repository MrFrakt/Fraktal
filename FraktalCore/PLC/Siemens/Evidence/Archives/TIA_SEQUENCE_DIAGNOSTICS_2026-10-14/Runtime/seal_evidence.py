import hashlib,json,shutil
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
ARCHIVE=ROOT/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14'
assert ARCHIVE.resolve().is_relative_to((ROOT/'FraktalCore/PLC/Siemens/Evidence/Archives').resolve())
ARCHIVE.mkdir(exist_ok=False)
def copy(p,t):t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,t)
for p in WORK.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(WORK)
    if rel.parts[0].startswith('previous_generated_') or '__pycache__' in rel.parts or p.suffix in ('.exe','.dll','.pdb','.pyc'):continue
    copy(p,ARCHIVE/'Runtime'/rel)
siemens=ROOT/'FraktalCore/PLC/Siemens'
for p in siemens.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(siemens)
    if any(part in ('Evidence','bin','obj','__pycache__') for part in rel.parts):continue
    copy(p,ARCHIVE/'SourceSnapshot/FraktalCore/PLC/Siemens'/rel)
for name in ('AGENTS.md','.vscode/settings.json','analysis_options.yaml',
 'Specification/Fraktal_Core_Part_I.md','Specification/Fraktal_TIA_Part_IV.md',
 'Specification/Siemens/README.md','Specification/Siemens/SIEMENS_PORT_PLAN.md',
 'Specification/Siemens/Evidence/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14.md'):
    copy(ROOT/name,ARCHIVE/'SourceSnapshot'/name)
for p in Path(r'C:\Projects\SiemensAgent\siemens-kb\tia-automation').glob('*.md'):
    copy(p,ARCHIVE/'Knowledge/tia-automation'/p.name)
for name in ('MEMORY.md','project-siemens-port.md'):
    copy(Path(r'C:\Users\Siemens\.claude\projects\c--Projects-Fraktal\memory')/name,ARCHIVE/'Knowledge/Memory'/name)
suite=ET.Element('testsuite',name='TIA sequence diagnostics',tests='230',failures='0',errors='0')
for name in ('52_diagnostics_restored.jsonl','49_medium_qualified.jsonl','51_view_regression.jsonl'):
    rows=[json.loads(s) for s in (WORK/name).read_text('utf-8-sig').splitlines() if s.startswith('{')]
    summary=next(r for r in reversed(rows) if r.get('event')=='summary')
    assert summary['complete'] and summary['checks']==summary['passed']
    for n,row in enumerate(r for r in rows if r.get('event')=='check'):
        assert row['passed'];ET.SubElement(suite,'testcase',classname=name.removesuffix('.jsonl'),name=str(n+1)+' '+row['label'])
assert len(suite)==230
ET.indent(suite);ET.ElementTree(suite).write(ARCHIVE/'native-results.xml',encoding='utf-8',xml_declaration=True)
files=sorted(p for p in ARCHIVE.rglob('*') if p.is_file())
(ARCHIVE/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ARCHIVE).as_posix() for p in files)+'\n',encoding='ascii',newline='\n')
for line in (ARCHIVE/'SHA256SUMS').read_text('ascii').splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256((ARCHIVE/name).read_bytes()).hexdigest()==digest
result={'archive':str(ARCHIVE),'verified_files':len(files),'payload_bytes':sum(p.stat().st_size for p in files),'native_checks':len(suite)}
(WORK/'57_archive_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
print(json.dumps(result))

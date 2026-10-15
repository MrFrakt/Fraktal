import hashlib,json,shutil,sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
ARCHIVE=ROOT/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_INTEGRATION_2026-10-14'
assert ARCHIVE.resolve().is_relative_to((ROOT/'FraktalCore/PLC/Siemens/Evidence/Archives').resolve())
ARCHIVE.mkdir(exist_ok=False)

def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)

for source in WORK.rglob('*'):
    if not source.is_file():continue
    relative=source.relative_to(WORK)
    if relative.parts[0].startswith(('driver_build_', 'previous_generated_')):continue
    if '__pycache__' in relative.parts or source.suffix.lower() in ('.exe','.dll','.pdb','.pyc'):continue
    copy(source,ARCHIVE/'Runtime'/relative)

siemens=ROOT/'FraktalCore/PLC/Siemens'
for source in siemens.rglob('*'):
    if not source.is_file():continue
    relative=source.relative_to(siemens)
    if any(p in ('Evidence','bin','obj','__pycache__') for p in relative.parts):continue
    copy(source,ARCHIVE/'SourceSnapshot/FraktalCore/PLC/Siemens'/relative)

paths=[
    '.vscode/settings.json','analysis_options.yaml',
    'Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md',
    'Specification/Siemens/README.md','Specification/Siemens/SIEMENS_PORT_PLAN.md',
    'Specification/Fraktal_Core_Part_I.md','Specification/Fraktal_TIA_Part_IV.md','Specification/HMI_CONTRACT.md',
    'FraktalCore/HMI/README.md','FraktalCore/HMI/pubspec.yaml','FraktalCore/HMI/pubspec.lock',
    'FraktalCore/HMI/lib/data/opcua_browse_paths.dart','FraktalCore/HMI/lib/data/opcua_repository.dart',
    'FraktalCore/HMI/lib/data/opcua_config_manifest.dart','FraktalCore/HMI/lib/data/opcua_snapshot_mapper.dart',
    'FraktalCore/HMI/gateway/lib/src/fraktal_gateway_server.dart',
    'FraktalCore/HMI/test/opcua_repository_test.dart','FraktalCore/HMI/test/opcua_config_manifest_test.dart',
    'FraktalCore/HMI/test/fraktal_gateway_server_test.dart','FraktalCore/HMI/test/live_tia_sequence_view_test.dart',
]
for relative in paths:copy(ROOT/relative,ARCHIVE/'SourceSnapshot'/relative)
for source in Path(r'C:\Projects\SiemensAgent\siemens-kb\tia-automation').glob('*.md'):
    copy(source,ARCHIVE/'Knowledge/tia-automation'/source.name)
for source in Path(r'C:\Users\Siemens\.claude\projects\c--Projects-Fraktal\memory').glob('*.md'):
    if source.name in ('MEMORY.md','project-siemens-port.md'):
        copy(source,ARCHIVE/'Knowledge/Memory'/source.name)

suite=ET.Element('testsuite',name='TIA sequence integration',tests='157',failures='0',errors='0')
for filename in ('08_medium_view.jsonl','09_view_regression.jsonl'):
    records=[json.loads(line) for line in (WORK/filename).read_text('utf-8-sig').splitlines() if line.startswith('{')]
    summary=next(r for r in reversed(records) if r.get('event')=='summary')
    assert summary['complete'] and summary['checks']==summary['passed']
    for number,row in enumerate(r for r in records if r.get('event')=='check'):
        assert row['passed']
        ET.SubElement(suite,'testcase',classname=filename.removesuffix('.jsonl'),name=str(number+1)+' '+row['label'])
assert len(suite)==157
ET.indent(suite);ET.ElementTree(suite).write(ARCHIVE/'native-results.xml',encoding='utf-8',xml_declaration=True)

payloads=sorted(p for p in ARCHIVE.rglob('*') if p.is_file())
lines=[]
for p in payloads:
    lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ARCHIVE).as_posix())
(ARCHIVE/'SHA256SUMS').write_text('\n'.join(lines)+'\n',encoding='ascii',newline='\n')
for line in (ARCHIVE/'SHA256SUMS').read_text('ascii').splitlines():
    sha,name=line.split('  ',1);assert hashlib.sha256((ARCHIVE/name).read_bytes()).hexdigest()==sha
result={'archive':str(ARCHIVE),'verified_files':len(payloads),'payload_bytes':sum(p.stat().st_size for p in payloads),'native_checks':len(suite)}
(WORK/'33_archive_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
print(json.dumps(result))

import hashlib,json,os,shutil,sys
from pathlib import Path
work=Path(__file__).resolve().parent
repo=Path('C:/Projects/Fraktal');plc=repo/'FraktalCore/PLC/Siemens'
archive=plc/'Evidence/Archives/TIA_CONFIG_TYPES_2026-10-15'
assert not archive.exists()
assert json.loads((work/'kb_index.json').read_bytes())['integrity']=='ok'
assert json.loads((work/'gates_verified.json').read_bytes())['final_gates_passed']
assert all(r['exit_code']==0 for r in json.loads((work/'remaining_results.json').read_bytes()))
assert len(json.loads((work/'runtime13/numeric01.json').read_bytes()))==33
def rows(p):return [json.loads(line) for line in p.read_text('ascii').splitlines()]
typed=rows(work/'runtime13/types03.jsonl');assert typed[-1]['completed'] and typed[-1]['failures']==0
sets=rows(work/'runtime13/sets_regression03.jsonl');assert sets[-1]['event']=='complete' and sets[-1]['failed']==0
idle=rows(work/'final_idle01.jsonl');assert idle[-1]['completed'] and idle[-1]['failures']==0
assert json.loads((work/'hmi01/result.json').read_bytes())['complete']
assert all(r['passed'] for rs in (typed,sets,idle) for r in rs if r['event']=='check')
for name in ('runtime13','press05'):
 witness=json.loads((work/name/'native_readback.json').read_bytes());assert witness['sources'] and witness['interfaces']
for p in ('runtime13/compile.log','runtime13/download.log','press05/compile.log'):
 entries=rows(work/p);compiles=[r for r in entries if r.get('event')=='compile'];assert any(r.get('event')=='driver' for r in entries) and any(r.get('event')=='plan-complete' for r in entries) and compiles and all(r['errors']==0 and r['warnings']==0 for r in compiles),p
# Work directories contain source/export/log payloads, never engineering projects.
assert not list(work.rglob('*.plf'))
shutil.copytree(work,archive/'Runs',ignore=shutil.ignore_patterns('kb_before.sqlite*','__pycache__'))
snapshot=archive/'SourceSnapshot'
shutil.copytree(plc,snapshot/'FraktalCore/PLC/Siemens',ignore=shutil.ignore_patterns('Evidence','bin','obj','__pycache__','.dart_tool','.vs'))
shutil.copytree(repo/'FraktalCore/HMI/lib',snapshot/'FraktalCore/HMI/lib')
shutil.copytree(repo/'FraktalCore/HMI/packages',snapshot/'FraktalCore/HMI/packages',ignore=shutil.ignore_patterns('.dart_tool','build','__pycache__'))
shutil.copytree(repo/'FraktalCore/HMI/gateway/lib',snapshot/'FraktalCore/HMI/gateway/lib')
for name in ('pubspec.yaml','pubspec.lock'):
 shutil.copy2(repo/'FraktalCore/HMI/gateway'/name,snapshot/'FraktalCore/HMI/gateway'/name)
for rel in ('FraktalCore/HMI/test/live_tia_manifest_test.dart','FraktalCore/HMI/pubspec.yaml','FraktalCore/HMI/pubspec.lock',
 'AGENTS.md','.gitattributes','.gitignore','Specification/Fraktal_Core_Part_I.md','Specification/Fraktal_TIA_Part_IV.md',
 'Specification/HMI_CONTRACT.md','Specification/OPCUA_TRANSPORT.md','Specification/README.md',
 'FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md','tools/check_consistency.py','tools/test_check_consistency.py'):
 dest=snapshot/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/rel,dest)
shutil.copytree(repo/'Specification/Siemens',snapshot/'Specification/Siemens')
metadata=json.loads((work/'runtime13/frames/manifest.json').read_bytes())
for rel,expected in {**metadata['core_inputs'],**metadata['runtime']['authority_inputs']}.items():
 src=repo/rel;assert hashlib.sha256(src.read_bytes()).hexdigest()==expected,rel
 dest=snapshot/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
shutil.copytree(Path('C:/Projects/SiemensAgent/siemens-kb/tia-automation'),snapshot/'Knowledge/tia-automation',ignore=shutil.ignore_patterns('*.sqlite','*.db'))
secrets=[os.environ[name].encode(enc) for name in ('FRAKTAL_TIA_ADMIN_PIN','FRAKTAL_TIA_OPERATOR_PIN','FRAKTAL_TIA_WEB_PASSWORD') for enc in ('utf-8','utf-16-le')]
files=sorted(p for p in archive.rglob('*') if p.is_file());lines=[];total=0
for p in files:
 raw=p.read_bytes();assert len(raw)<100_000_000,p
 assert not any(s in raw for s in secrets),'plaintext credential: '+str(p.relative_to(archive))
 total+=len(raw);lines.append(hashlib.sha256(raw).hexdigest()+'  '+p.relative_to(repo).as_posix())
manifest=archive/'SHA256SUMS';manifest.write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
for line in lines:
 expected,rel=line.split('  ',1);assert hashlib.sha256((repo/rel).read_bytes()).hexdigest()==expected,rel
result=dict(archive=str(archive),files=len(files),bytes=total,verified=True,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),checks=dict(typed=typed[-1]['assertions'],sets=sets[-1]['checks'],idle=idle[-1]['assertions']))
Path(sys.argv[1]).write_bytes((json.dumps(result,indent=2)+'\n').encode('ascii'));print(json.dumps(result))

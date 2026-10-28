from pathlib import Path
import gzip,hashlib,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import test_fraktal_ab_config_read_view as suite
import fraktal_ab_config_read_view as view
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_manifest as wire
import fraktal_ab_s4b_equivalence as oracle
import fraktal_ab_generate as gen
t=suite.ReadViewTests('test_independent_migration_reference_matches_all_new_paths');t.setUp();t.scan()
additional=dict(records=t.records,models=t.controller.tags[gen.model_cfg_tag(t.app)],levels=t.levels,
    query=dict(Revision=t.work['Revision']),read_view_codes=[m.code for m in t.app.models])
expected=oracle.reference(t.app,additional);prefix=view.canonical_root(t.app)+'/'
actual={prefix+m.name:t.text(t.read[m.name]) if m.name=='RootIdentity' else t.read[m.name] for m in t.schema[view.VIEW] if not m.count}
for group,kind,count in (('Definitions',view.DEFINITION,t.read['DefinitionCount']),('Values',view.VALUE,t.read['ValueCount'])):
    for i,row in enumerate(t.read[group][:count]):actual.update({prefix+f'{group}[{i}]/'+n:v for n,v in t.row(row,kind).items()})
assert actual==expected
pages=[]
for bank in range(len(t.app.models)+1):
    pages.append([dict(DefinitionIndex=i,**row) for i,row in enumerate(t.expected(bank)) if bank==0 or row['ModelScoped']])
report=dict(schema='fraktal.cip.config-read-view-offline-goldens.v1',synthetic=True,
    scope='Real generated ST executed in the coupled interpreter, compared against legacy config_page; not native V6.8 evidence.',
    sourceSha256=hashlib.sha256((W/'canonical_read_view_01.L5X').read_bytes()).hexdigest(),
    manifest=wire.normalize(suite.physical(pub.manifest_values(t.app))),rootSymbol=t.app.name,canonicalRoot=view.canonical_root(t.app),values=actual,expectedPages=pages)
destination=R/'FraktalCore/HMI/test/fixtures/cip_read_view_goldens.json.gz'
with destination.open('xb') as stream:stream.write(gzip.compress(json.dumps(report,separators=(',',':'),allow_nan=False).encode(),mtime=0))
print(json.dumps(dict(passed=True,paths=len(actual),banks=len(pages)-1,sha256=hashlib.sha256(destination.read_bytes()).hexdigest())))

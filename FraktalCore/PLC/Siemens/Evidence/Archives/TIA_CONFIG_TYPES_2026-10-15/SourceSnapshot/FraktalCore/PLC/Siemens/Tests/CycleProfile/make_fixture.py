"""Small offline compiler gate for shared profiling services and Core timing rows."""
import argparse,importlib.util,json,os,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
import fraktal_tia_declaration as DECL
import fraktal_tia_runtime as RUNTIME
import fraktal_tia_profile as PROFILE
import fraktal_tia_generate as GEN
from fraktal_tia_binding import Catalog,type_source
from fraktal_tia_program_layout import organize

def prepare(out, existing_project=None):
    out.mkdir(exist_ok=False,parents=True)
    source=out/'sources';source.mkdir()
    spec=importlib.util.spec_from_file_location('view_fixture',HERE.parent/'SequenceView/make_fixture.py')
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    catalog=Catalog.read();model=DECL.validate(fixture.select(fixture.CONFIG.declaration()))
    sources={}
    fields=catalog.resolve(['ST_ModuleStatus','ST_ModuleTiming','ST_StepTiming','ST_CycleSummary'])
    for n,(name,members) in enumerate(fields.items()):sources[f'00_{n:03d}_{name}.udt']=type_source(name,members)
    core,_=RUNTIME.build();sources.update(core)
    frames,_=GEN.build(model,True)
    for name in ('01_FRK_RegistryRow.udt','04_FRK_Registry.db','10_Registry.scl'):
        sources[name]=frames[name]
    profile,_=PROFILE.build(model,catalog);sources.update(profile)
    for name,text in sources.items():(source/name).write_bytes(text.encode('ascii'))
    stations=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations'
    if existing_project is None:
        project=stations/'Cycle_Profile_Compiler_20261014/FrkS12/FrkS12.ap20'
        assert not project.parent.parent.exists()
        shutil.copytree(stations/'FrkS12',project.parent)
    else:
        project=existing_project.resolve(strict=True)
        if project.suffix != '.ap20' or project.parent.parent.name != 'Cycle_Profile_Compiler_20261014':
            raise ValueError('Only the isolated profiling compiler project may be reused')
    organize(source,out/'grouped',project,out/'native')
    (out/'inputs.json').write_text(json.dumps({'sources':len(sources),'core_inputs':catalog.inputs,'declaration':fixture.select(fixture.CONFIG.declaration())},indent=2)+'\n',encoding='ascii')
    print(json.dumps({'sources':len(sources),'project':str(project)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    p.add_argument('--existing-project',type=Path)
    args=p.parse_args();prepare(args.out,args.existing_project)

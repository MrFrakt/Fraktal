from pathlib import Path
import os,sys,subprocess,json,hashlib
repo=Path('C:/Projects/Fraktal');tia=repo/'FraktalCore/PLC/Siemens';sys.path.insert(0,str(tia/'tools'))
import fraktal_tia_io_bridge as bridge
from fraktal_tia_program_layout import organize
w=Path(__file__).parent;stations=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations'
driver=tia/'tools/TiaCli/bin/candidate_structure_examples/Fraktal.Tia.Cli.exe'
assert hashlib.sha256(driver.read_bytes()).hexdigest()=='ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74'
for physical,label,project in ((False,'native05_controller_connect',stations/'Press_IoBridge_Press1500_20261015/FrkS12/FrkS12.ap20'),(True,'physical06_controller_connect',stations/'Press_IoBridge_1214C_20261015/FrkSpikeS2.ap20')):
    assert project.is_file()
    out=w/label;out.mkdir(exist_ok=False);bridge.generate(out/'sources',physical)
    if physical:
        plan=bridge.prepare_plan(out/'sources',project,out/'native')
    else:
        public=(out/'sources/30_PressDemoComposition.scl').read_bytes()
        assert public==(w/'current_public/30_PressDemoComposition.scl').read_bytes()
        (out/'sources/30_PressDemoComposition.scl').write_bytes((w/'native03/sources/30_PressDemoComposition.scl').read_bytes())
        organize(out/'sources',out/'grouped',project,out/'native');plan=out/'grouped/import.plan'
    selected=[];imports=0
    for line in plan.read_text('ascii').splitlines():
        if line.startswith('delete-blocks'):continue
        if line.startswith(('import-sources','import-xml')):
            if '"01_IoBridge.scl"' not in line:continue
            imports+=1
        selected.append(line)
    assert imports==1,(label,imports)
    plan.write_bytes(('\n'.join(selected)+'\n').encode('ascii'))
    with (out/'build.log').open('xb') as f:r=subprocess.run([str(driver),'plan',str(plan)],stdout=f,stderr=subprocess.STDOUT)
    print(dict(build_exit=r.returncode,physical=physical,out=str(out)),flush=True)
    if r.returncode:raise SystemExit(r.returncode)

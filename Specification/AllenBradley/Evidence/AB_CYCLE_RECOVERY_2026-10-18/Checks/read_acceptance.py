import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path('FraktalCore/PLC/Allen-Bradley/tools').resolve()))
from pylogix import PLC
import fraktal_ab_generate as gen
import fraktal_ab_live as live
import fraktal_ab_part_execute as fixture
import fraktal_ab_part_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_press_execute as px

app = demo.application()
path = Path('C:/work/fraktal-ab-recovery-20261018/sink_acceptance.json')
assert not path.exists()
evidence = dict(serial='601FC87B', rows=[])
with PLC('127.0.0.1') as native:
    native.ConnectionSize = 4000
    native.ProcessorSlot = 0
    comm = fixture.Guarded(native, 0x601FC87B, app)
    comm.guard()
    run = fixture.Run(comm, app, {}, evidence)
    run.verify_sink(path)
    held = projection.read_document(comm)['liveConfig']
    medium = live.FileMedium(live.live_directory(app,'601FC87B'))
    wanted = live.documents(app, held, 0)
    matches = {k:live.content(medium.read(k))==live.content(v) for k,v in wanted.items()}
    assert all(matches.values())
    evidence['configurationReopen'] = matches
    unit = run.unit()
    evidence['finalUnit'] = {k:unit[k] for k in ('Mode','Running','Error','ErrorID','Aborted','Step',
                                                'GoodCount','ScrapCount','CycleCount','ScanOrderFail') if k in unit}
    evidence['finalAccessLevel'] = projection.read_access(comm)['CurrentLevel']
    evidence['stimuli'] = {tag:px.read_scalar(comm,tag) for tag in gen.externally_writable(app)}
    evidence['persist'] = projection.read_persist(comm)
    evidence['scanBefore'] = px.read_scalar(comm, 'FRK_Press_ScanCount')
    evidence['projectionPaths'] = len(projection.read_document(comm)['values'])
    evidence['scanAfter'] = px.read_scalar(comm, 'FRK_Press_ScanCount')
    assert evidence['scanAfter'] > evidence['scanBefore']
path.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
print(json.dumps(evidence,indent=2))

import json
import os
import sys
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
OUT=Path('C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5')
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_live as live
import fraktal_ab_manifest as manifest
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_station as station
app=station.application()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0
    native.ConnectionSize=4000
    native.SocketTimeout=5
    comm=fixture.Guarded(native,0x601FC87B,app)
    comm.guard()
    unit=execute.read_unit(comm)
    if unit is None or unit['Mode']!=0 or any(unit[k] for k in ('Running','Error','RunRequest','AbortRequest','ResetRequest')):
        raise RuntimeError('current fixture is not MANUAL and idle')
    access=projection.read_access(comm)
    if access['CurrentLevel']!=0:
        raise RuntimeError('another session is active')
    held=projection.read_document(comm)['liveConfig']
    directory=live.live_directory(app,'601FC87B')
    medium=live.FileMedium(directory)
    wanted=live.documents(app,held,0)
    documents={key:medium.read(key) for key in wanted}
    def values(document):
        return [{k:v for k,v in row.items() if k!='rev'} for row in document[1:]]
    checks={key:documents[key] is not None and values(documents[key])==values(value) for key,value in wanted.items()}
    if not all(checks.values()):
        raise RuntimeError('saved/live configuration differs')
    result=dict(serial='601FC87B',manifest=manifest.content_hash(app),configRevision=manifest.config_revision(app),
        savedDocumentsEqual=checks,documents=documents,medium=str(directory),
        originalPolicy=access['Required'],mode=unit['Mode'])
    destination=OUT/'preflight.json'
    if '--verify-only' in sys.argv:
        prior=json.loads(destination.read_text(encoding='utf-8'))
        if result!=prior:
            raise RuntimeError('configuration, identity or policy changed since backup preflight')
    else:
        with destination.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,indent=2)
            stream.write('\n')
    print(json.dumps(dict(guardPassed=True,manifest=result['manifest'],documents=len(documents))))

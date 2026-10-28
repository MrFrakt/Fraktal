"""Read-only restoration checks for the exact genealogy Echo fixture."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path('C:/work/fraktal-ab-s3j-20261024/prepare_fb6598e2234d43f99f5ae75e718f9860')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
sys.path.insert(0, str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_generate as gen
import fraktal_ab_live as live
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_station as station

destination = Path(sys.argv[1])
if destination.exists():
    raise SystemExit('refusing existing final evidence')
subprocess.run([sys.executable, str(WORK/'scripts/guard_echo.py')], check=True)
app = station.application()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot, native.ConnectionSize, native.SocketTimeout = 0, 4000, 5
    comm = fixture.Guarded(native, 0x601FC87B, app)
    comm.guard()
    unit = px.read_unit(comm)
    access = projection.read_access(comm)
    held = projection.read_document(comm)['liveConfig']
    wanted = live.documents(app, held, 0)
    medium = live.FileMedium(live.live_directory(app, '601FC87B'))
    def values(document):
        return [{k:v for k,v in row.items() if k != 'rev'} for row in document[1:]]
    documents = {key:medium.read(key) for key in wanted}
    equal = {key:documents[key] is not None and values(documents[key]) == values(document)
             for key, document in wanted.items()}
    scan_tag = gen.Names(app, in_aoi=False).scan
    scan = [px.read_scalar(comm, scan_tag)]
    time.sleep(.25)
    scan.append(px.read_scalar(comm, scan_tag))
    initial = json.loads((WORK/'preflight.json').read_text(encoding='utf-8'))
    checks = dict(scanAdvancing=isinstance(scan[0], int) and isinstance(scan[1], int) and scan[1] > scan[0],
                  manual=unit['Mode'] == app.manual_mode,
                  idle=not any(unit[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')),
                  loggedOut=access['CurrentLevel'] == 0,
                  notRestoring=not held.restoring,
                  savedEqualsLive=all(equal.values()),
                  policyRestored=access['Required'] == initial['originalPolicy'])
report = dict(passed=all(checks.values()), checks=checks, savedDocumentsEqual=equal,
              scan=scan, capturedUtc=datetime.now(timezone.utc).isoformat())
with destination.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)

"""Read-only check after the genealogy download, before the baseline cases.

The five host documents must still equal the verified S5 baseline's record
(session_19 preflight.json), and the freshly downloaded image must be idle,
logged out and restoring, so the baseline's own restore re-applies exactly
those documents. No controller or medium write is performed here.
"""
from pathlib import Path
import datetime, json, os, subprocess, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
REFERENCE = Path('C:/work/fraktal-ab-s5-20261029/session_19/preflight.json')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_live as live
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_station as station

before = json.loads(REFERENCE.read_bytes())
app = station.application()
directory = live.live_directory(app, '601FC87B')
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], check=True)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot, native.ConnectionSize, native.SocketTimeout = 0, 4000, 5
    comm = fixture.Guarded(native, 0x601FC87B, app)
    comm.guard()
    unit, access = execute.read_unit(comm), projection.read_access(comm)
    restoring = bool(projection.read_document(comm)['liveConfig'].restoring)
medium = live.FileMedium(directory)
equal = {key: medium.read(key) == document for key, document in before['documents'].items()}
report = dict(readOnly=True, serial='601FC87B', medium=str(directory), mediumIsReference=str(directory) == before['medium'],
              documentsEqualReference=equal, restoring=restoring,
              idle=unit is not None and not any(unit[k] for k in ('Running', 'Error', 'Aborted', 'RunRequest', 'AbortRequest', 'ResetRequest')),
              loggedOut=access['CurrentLevel'] == 0 and not access['LoginBusy'],
              reference=str(REFERENCE), capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
report['passed'] = (report['mediumIsReference'] and len(equal) == 5 and all(equal.values())
                    and restoring and report['idle'] and report['loggedOut'])
with (D / 'medium_check.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(passed=report['passed'], restoring=restoring, documents=equal)))
raise SystemExit(0 if report['passed'] else 1)

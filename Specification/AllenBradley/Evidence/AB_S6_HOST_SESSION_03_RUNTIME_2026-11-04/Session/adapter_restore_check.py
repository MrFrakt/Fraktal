"""Read-only: the Dart host adapter restored the candidate's live documents natively.

The runner started fraktal_host_adapter.exe against a byte-exact session copy
of the five baseline documents (medium/live). This waits for its health line
to report a completed restore with no loss, then verifies the candidate: no
longer restoring, idle, logged out, and its live values equal to the copied
documents. It writes nothing to the controller or to any medium.
"""
from pathlib import Path
import datetime, json, os, subprocess, sys, time

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s6_host_demo'
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_live as live
import fraktal_ab_live_medium as medium_files
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_station as station

deadline, health, lines = time.monotonic() + 180, None, []
while time.monotonic() < deadline:
    lines = [json.loads(l) for l in (D / 'adapter.log').read_text(encoding='utf-8').splitlines() if l.startswith('{')]
    restored = [l for l in lines if isinstance(l.get('health'), dict) and l['health'].get('restoredAt')]
    if restored:
        health = restored[-1]['health']
        break
    time.sleep(1)
app = station.application()
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], check=True)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot, native.ConnectionSize, native.SocketTimeout = 0, 4000, 5
    comm = fixture.Guarded(native, 0x601FC87B, app)
    comm.guard()
    unit, access = execute.read_unit(comm), projection.read_access(comm)
    held = projection.read_document(comm)['liveConfig']
medium = medium_files.FileMedium(D / 'medium/live')
values = lambda document: [{k: v for k, v in row.items() if k != 'rev'} for row in document[1:]]
wanted = live.documents(app, held, 0)
equal = {key: medium.read(key) is not None and values(medium.read(key)) == values(document)
         for key, document in wanted.items()}
report = dict(readOnly=True, serial='601FC87B', adapterHealth=health, adapterLines=len(lines),
              restoring=bool(held.restoring), idle=unit is not None and not any(
                  unit[k] for k in ('Running', 'Error', 'Aborted', 'RunRequest', 'AbortRequest', 'ResetRequest')),
              currentLevel=access['CurrentLevel'], liveEqualsCopiedDocuments=equal,
              capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
report['passed'] = (health is not None and not health.get('losses') and not health.get('failed')
                    and not report['restoring'] and report['idle']
                    and len(equal) == 5 and all(equal.values()))
with (D / 'adapter_restore_check.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(passed=report['passed'], restoring=report['restoring'], documents=equal,
                      health=health)))
raise SystemExit(0 if report['passed'] else 1)

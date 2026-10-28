"""Finish the authorized rollback using this session's original host documents.

Preserves the post-candidate medium before restoring exact preflight documents.
No controller write is performed here. Baseline fixture writes follow separately.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

R = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_live as live
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_station as station

approval = json.loads((R / 'authorization.json').read_bytes())
assert approval['CurrentOwnerApproved'] and approval['RestoreGenealogyAuthorized'] and approval['BaselineRegressionWritesAuthorized']
assert approval['Serial'] == '601FC87B' and not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
assert json.loads((R / 'restore_genealogy_audit_exit.json').read_bytes())['exitCode'] == 0
before = json.loads((R / 'preflight.json').read_bytes())
app = station.application()
assert str(live.live_directory(app, '601FC87B')) == before['medium']
subprocess.run([sys.executable, str(R / 'scripts/guard_echo.py')], check=True)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot, native.ConnectionSize, native.SocketTimeout = 0, 4000, 5
    comm = fixture.Guarded(native, 0x601FC87B, app)
    comm.guard()
    unit, access = execute.read_unit(comm), projection.read_access(comm)
    assert unit is not None and not any(unit[k] for k in ('Running', 'Error', 'Aborted', 'RunRequest', 'AbortRequest', 'ResetRequest'))
    assert access['CurrentLevel'] == 0 and not access['LoginBusy']
    assert projection.read_document(comm)['liveConfig'].restoring
medium = live.FileMedium(Path(before['medium']))
current = {key: medium.read(key) for key in before['documents']}
values = lambda document: [{key: value for key, value in row.items() if key != 'rev'} for row in document[1:]]
assert all(current[key] is not None and values(current[key]) == values(document)
           for key, document in before['documents'].items()), 'candidate medium values differ from preflight; no overwrite'
backup = R / 'medium_before_rollback_completion'
backup.mkdir()
hashes = {}
for source in [medium.directory / live.INDEX_NAME, *(medium._path(key) for key in current)]:
    raw = source.read_bytes()
    with (backup / source.name).open('xb') as stream:
        stream.write(raw)
    hashes[source.name] = hashlib.sha256(raw).hexdigest()
with (R / 'medium_before_rollback_completion.json').open('x') as stream:
    json.dump(dict(documents=current, sha256=hashes), stream, indent=2)
for key, document in before['documents'].items():
    medium.write(key, document)
assert all(medium.read(key) == document for key, document in before['documents'].items())
result = dict(passed=True, originalDocumentsRestored=5, controllerWrites=0,
              originalRevisions={key: document[0]['configRev'] for key, document in before['documents'].items()},
              beforeRevisions={key: document[0]['configRev'] for key, document in current.items()},
              recordValuesUnchanged=True, backedUpOriginalFiles=hashes,
              authorizationSource='existing current session authorization.json; completion of approved genealogy rollback only',
              newCandidateDownloadAuthorized=False, utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R / 'medium_restored_01.json').open('x') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))

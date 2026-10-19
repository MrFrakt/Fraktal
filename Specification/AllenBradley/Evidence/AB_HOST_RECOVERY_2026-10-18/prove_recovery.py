"""Read-only Echo capture; local subprocess crashes against captured events."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
OUT = Path(__file__).parent
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_tower_demo'
sys.path.insert(0, str(TOOLS))
from pylogix import PLC
import fraktal_ab_host_events as host
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_models as models
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_station as station
from fraktal_ab_host_sink import SqliteSink

APP = station.application()
SOURCE = '601FC87B:' + manifest.content_hash(APP)
CHECKS = {}

def check(name, ok):
    CHECKS[name] = bool(ok)
    if not ok:
        raise AssertionError(name)

def save(name, value):
    with (OUT/name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')

def records(path):
    with closing(sqlite3.connect(path)) as connection:
        check('integrity_' + path.stem, connection.execute('PRAGMA integrity_check').fetchone() == ('ok',))
        return [json.loads(row[0]) for row in connection.execute('SELECT Record FROM Events ORDER BY Id')]

def read_live():
    with PLC('127.0.0.1') as comm:
        comm.ProcessorSlot, comm.SocketTimeout = 0, 3
        device = comm.GetDeviceProperties()
        check('exact_echo_identity', device.Status == 'Success'
              and str(device.Value.SerialNumber).lower() == '0x601fc87b'
              and device.Value.Revision == '38.11' and device.Value.ProductCode == 288)
        serial, good = projection.verify_serial(comm, '601FC87B')
        check('serial_guard', good)
        before, status, _ = reader._read_raw(comm, manifest.header_tag(APP))
        check('manifest_read', before is not None)
        projection.validate(reader.decode_header(before))
        unit = execute.read_unit(comm)
        batch = host.read(comm, APP, models.read(comm, APP))
        after, _, _ = reader._read_raw(comm, manifest.header_tag(APP))
        check('manifest_stable', before == after)
        check('manual_idle', unit is not None and unit['Mode'] == 0
              and not any(unit[k] for k in ('Running', 'Error', 'RunRequest', 'AbortRequest', 'ResetRequest')))
        return batch, {key: unit[key] for key in ('Mode', 'Step', 'Running', 'Error', 'CycleCount',
                                                'GoodCount', 'ScrapCount', 'RunRequest', 'ResetRequest')}

batch, initial = read_live()
save('live_batch.json', batch)
check('retained_events_present', len(batch['events']) > 0)
before = records(OUT/'live.events.sqlite')
cli = [sys.executable, str(TOOLS/'fraktal_ab_host_events.py'), '127.0.0.1', '--expect-serial',
       '601FC87B', '--cursor', str(OUT/'live.cursor.json'), '--sqlite-output', str(OUT/'live.events.sqlite')]
reopen = subprocess.run(cli, capture_output=True, timeout=30)
check('cli_reopen_success', reopen.returncode == 0)
check('cli_reopen_no_duplicate_rows', records(OUT/'live.events.sqlite') == before)

child_code = '''
import json, os, sys
from pathlib import Path
import fraktal_ab_host_events as host
from fraktal_ab_host_sink import SqliteSink
batch_path, cursor_path, db_path, source, mode = sys.argv[1:]
batch = json.loads(Path(batch_path).read_text(encoding='utf-8'))
cursor = host.Cursor('Press', cursor_path, source=source)
if mode == 'after_sink':
    cursor._commit = lambda *args: os._exit(71)
else:
    host.os.replace = lambda *args: os._exit(72)
with SqliteSink(db_path, 'Press', source=source) as sink:
    cursor.deliver(batch, sink)
'''
results = []
for mode in ('after_sink', 'before_replace'):
    cursor_path, db_path = OUT/(mode+'.cursor.json'), OUT/(mode+'.sqlite')
    crash = subprocess.run([sys.executable, '-c', child_code, str(OUT/'live_batch.json'),
                            str(cursor_path), str(db_path), SOURCE, mode],
                           cwd=TOOLS, capture_output=True, timeout=20)
    check(mode+'_crash_exit', crash.returncode == (71 if mode == 'after_sink' else 72))
    first = records(db_path)
    check(mode+'_accepted_before_crash', len(first) == 1)
    check(mode+'_no_uncommitted_cursor', not cursor_path.exists())
    with SqliteSink(db_path, APP.name, source=SOURCE) as sink:
        cursor = host.Cursor(APP.name, cursor_path, source=SOURCE)
        check(mode+'_restart_delivery', cursor.deliver(batch, sink))
        check(mode+'_restart_acknowledges_newest', cursor.state['sequence'] == batch['metadata']['NewestSequence'])
    rows = records(db_path)
    expected = len(batch['events']) + (batch['events'][0]['Sequence'] > 1)
    check(mode+'_exactly_one_row_per_key', len(rows) == expected
          and len({json.dumps(r['idempotencyKey']) for r in rows}) == expected)
    results.append(dict(mode=mode, exitCode=crash.returncode, storedRows=len(rows),
                        firstAcceptedKind=first[0]['kind'], cursor=cursor.state))

final_batch, final = read_live()
check('controller_state_unchanged', initial == final)
save('recovery.json', dict(schema='fraktal.ab.host-recovery-evidence', version=1,
    source=SOURCE, python=sys.version, sqlite=sqlite3.sqlite_version,
    controllerWrites=0, initial=initial, final=final, metadata=batch['metadata'],
    liveCliRows=len(before), crashes=results, checks=CHECKS, passed=all(CHECKS.values())))
print(json.dumps(dict(passed=all(CHECKS.values()), checks=len(CHECKS),
                      capturedEvents=len(batch['events']), liveCliRows=len(before), crashes=len(results))))

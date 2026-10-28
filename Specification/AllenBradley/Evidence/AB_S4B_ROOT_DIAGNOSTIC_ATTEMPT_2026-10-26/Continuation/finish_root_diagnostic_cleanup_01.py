"""Finish only the residual cleanup of the current owner-approved session.

No new download or candidate fixture is authorized here. Restore the two
fixture policy gates and MANUAL, using the already approved rollback writes.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

D = Path('C:/work/fraktal-ab-s4b-20261025/retry_root_diagnostic_01')
R = Path('C:/Users/SoftIndVM/Fraktal')
approval = json.loads((D / 'authorization.json').read_bytes())
assert approval['OwnerInstruction'] == 'Approve guarded S4b root diagnostic session'
assert approval['ApprovalQuestion'] == 'call_0c97c2f8c5c84620bbb108165c7177cd:0'
assert approval['CurrentOwnerApproved'] and approval['ManualNormalizationAuthorized'] and approval['BaselineRegressionWritesAuthorized']
result = json.loads((D / 'session_result.json').read_bytes())
assert result['rollbackError'] and not result['dumpFiles']
assert json.loads((D / 'restore_genealogy_exit.json').read_bytes())['exitCode'] == 0
assert json.loads((D / 'restore_access_exit.json').read_bytes())['exitCode'] == 0
assert not (D / 'rollback_cleanup_01.json').exists()
original = json.loads((D / 'preflight.json').read_bytes())
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], check=True)
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
sys.path.insert(0, str(R / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_mailbox as mb
import fraktal_ab_station as station

app = station.application()
report = dict(scope='Residual cleanup of the approved root diagnostic rollback only',
    approvalQuestion=approval['ApprovalQuestion'], authorizationSha256=hashlib.sha256((D / 'authorization.json').read_bytes()).hexdigest(),
    modeChanges=[], restoredPolicyGates=[], downloadOperations=0, faultClears=0, clockChanges=0, powerOperations=0)
try:
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot, native.ConnectionSize, native.SocketTimeout = 0, 4000, 5
        comm = fixture.Guarded(native, 0x601FC87B, app)
        comm.guard()
        raw, _, _ = reader._read_raw(comm, manifest.header_tag(app))
        assert raw is not None
        header = reader.decode_header(raw)
        assert header['ContentHash'] == original['manifest'] == manifest.content_hash(app)
        assert header['ConfigRevision'] == original['configRevision']
        unit = px.read_unit(comm)
        access = projection.read_access(comm)
        assert unit is not None and not any(unit[k] for k in ('Running', 'Error', 'Aborted', 'RunRequest', 'AbortRequest', 'ResetRequest'))
        assert access['CurrentLevel'] == 0, 'active session guard retained'
        assert not projection.read_document(comm)['liveConfig'].restoring
        wanted = original['originalPolicy']
        assert len(access['Required']) == len(wanted)
        differences = [i for i, value in enumerate(wanted) if value != access['Required'][i]]
        assert set(differences) <= {2, 10}, 'policy differs outside approved fixture gates'
        report['before'] = dict(mode=unit['Mode'], currentLevel=access['CurrentLevel'], policy=access['Required'])
        account = next(a for a in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_bytes())['users'] if a['level'] == 4)
        assert account['user'] in {user.name for user in app.access_users}
        run = fixture.Run(comm, app, account, dict(rows=[], serial='601FC87B'))
        if differences or unit['Mode'] != app.manual_mode:
            run.login()
            try:
                for gate in differences:
                    run.command(mb.SET_ACCESS_LEVEL, IntValue=gate, TextValue=str(wanted[gate]))
                    report['restoredPolicyGates'].append(gate)
                if unit['Mode'] != app.manual_mode:
                    run.command(mb.SET_MODE, IntValue=app.manual_mode)
                    run.wait(lambda: run.unit()['Mode'] == app.manual_mode, 'approved MANUAL cleanup')
                    report['modeChanges'].append(app.manual_mode)
            finally:
                run.command(mb.LOGOUT)
        after = px.read_unit(comm)
        access = projection.read_access(comm)
        report['after'] = dict(mode=after['Mode'], currentLevel=access['CurrentLevel'], policy=access['Required'])
        report['passed'] = (after['Mode'] == app.manual_mode and access['CurrentLevel'] == 0
            and access['Required'] == wanted and not any(after[k] for k in ('Running', 'Error', 'Aborted', 'RunRequest', 'AbortRequest', 'ResetRequest')))
except Exception as error:
    report.update(passed=False, error=f'{type(error).__name__}: {error}')
report['capturedUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (D / 'rollback_cleanup_01.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)

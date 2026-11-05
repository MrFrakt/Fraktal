"""Log the fixture's ENGINEER account in or out through the mailbox, as the legacy restore did.

V6.11 restoring writes run under the logged-in session's authorization and the
host adapter gains no login, so an authorized session is open while it restores.
"""
from pathlib import Path
import datetime, json, os, subprocess, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s6_host_demo'
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as fixture
import fraktal_ab_projection as projection
import fraktal_ab_station as station

action = sys.argv[1]
assert action in ('login', 'logout')
app = station.application()
account = next(a for a in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_text())['users']
               if a['level'] == 4)
assert account['user'] in {u.name for u in app.access_users}
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], check=True)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot, native.ConnectionSize, native.SocketTimeout = 0, 4000, 5
    comm = fixture.Guarded(native, 0x601FC87B, app)
    comm.guard()
    run = fixture.Run(comm, app, account, dict(rows=[], serial='601FC87B'))
    if action == 'login':
        run.login()
    else:
        run.command(mb.LOGOUT)
    level = projection.read_access(comm)['CurrentLevel']
report = dict(action=action, currentLevel=level, passed=level == (4 if action == 'login' else 0),
              utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D / f'session_login_{action}.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)

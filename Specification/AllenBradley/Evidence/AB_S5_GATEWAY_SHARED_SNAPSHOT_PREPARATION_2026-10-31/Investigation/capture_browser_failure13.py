from pathlib import Path
import datetime, json, sys, urllib.request

sys.path.pop(0)
D = Path('C:/work/fraktal-ab-s5-20261029/session_13')
sys.path.insert(0, str(D))
from browser_witness import state

ready = json.loads((D / 'browser_ready.json').read_bytes())
record = dict(token=ready['token'], ownerRecorded=True, passed=False,
    ownerWords='seccond tab at first showed connection error page, then connected and keeps reconnecting and disconnecting',
    reportedIssue='Second-tab startup error followed by repeated connection transitions',
    checksNotAccepted=True, credentialValuesRecorded=False,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D / 'browser_owner_failure_report.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
capture = dict(readOnly=True, native=state(), http={})
for port in (8080, 8081):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5) as response:
            health = json.load(response)
        capture['http'][str(port)] = {key: health[key] for key in
            ('status', 'plcReady', 'lastOpcUaSuccess', 'lastOpcUaFailure', 'writeAccess') if key in health}
    except Exception as error:
        capture['http'][str(port)] = dict(error=type(error).__name__)
with (D / 'browser_failure_readonly_boundary.json').open('x', encoding='utf-8') as stream:
    json.dump(capture, stream, indent=2)
for name in ('gateway_echo_02.log', 'gateway_echo-view_01.log'):
    with (D / ('failure_snapshot_' + name)).open('xb') as stream:
        stream.write((D / name).read_bytes())
print(json.dumps(dict(ownerFailurePreserved=True, readOnly=capture, checklistNotAccepted=True)))

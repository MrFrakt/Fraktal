from pathlib import Path
import datetime, json

D = Path(__file__).parent / 'session_13'
failure = json.loads((D / 'browser_owner_failure_report.json').read_bytes())
record = dict(failure,
    checks={},
    ownerCleanupWords='MANUAL, logged out; both tabs closed',
    recordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D / 'browser_owner_checklist.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
print(json.dumps(dict(ownerRecorded=True, passed=False, token=record['token'], guardedRollbackRequested=True)))

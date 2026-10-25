"""Read-only diagnosis of the failed S3i calendar capture from its own records."""
from pathlib import Path
import collections, gzip, json, math, sys

R = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/runtime_9fe4b2baee484ed2bb9b25b66cd32168')
T = Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
output = Path(sys.argv[1])
assert not output.exists()
sys.path.insert(0, str(T))
from fraktal_ab_mailbox_frame import CONNECTION_SIZE

failed = json.loads(gzip.decompress((R/'calendar_01_lifetime_01.json.gz').read_bytes()))
attempts = failed['attempts']
windows = [a for a in attempts if 'after' in a]
accepted_report = json.loads(gzip.decompress((R/'candidate_regressions_01_sequence_01.json.gz').read_bytes()))
accepted = dict(accepted_report['pair'], fixtureObserver=accepted_report.get('fixtureObserver'))
frame = accepted['stateEvidence']['frame']
fragment_bytes = accepted['readPlan'][0]['length']          # measured at 4,000 bytes
overhead = 4000 - fragment_bytes                            # Read Tag Fragmented reply framing
calendar = json.loads((R/'calendar_01.json').read_text())
source = (T/'fraktal_ab_press_execute.py').read_text(encoding='utf-8')
report = dict(
    readOnly=True, controllerAccess=False,
    failedCapture=dict(phase='original_empty_profile', error=failed['error'], attempts=len(attempts),
                       unchangedEvenWaits=sum(1 for a in attempts if a.get('waitingFreshScan')),
                       oddPolls=sum(1 for a in attempts if a['before'] % 2 and 'after' not in a),
                       readWindows=len(windows),
                       windowGenerationDeltas=dict(collections.Counter(a['after'] - a['before'] for a in windows)),
                       firstGeneration=attempts[0]['before'], lastGeneration=attempts[-1].get('after', attempts[-1]['before'])),
    calendarWriteCount=calendar['calendarWriteCount'], configurationRestored=calendar['configurationRestored'],
    frameBytes=frame['bytes'], framePeriodScans=frame['periodScans'],
    acceptedFixtureReads=dict(connectionBytes=4000, fragmentPayloadBytes=fragment_bytes,
                              requests=len(accepted['readPlan']), observer=accepted.get('fixtureObserver')),
    mailboxWriterConnectionBytes=CONNECTION_SIZE,
    mailboxSetsWriterSize='comm.ConnectionSize = CONNECTION_SIZE' in source,
    estimatedRequestsAtWriterSize=math.ceil(frame['bytes'] / (CONNECTION_SIZE - overhead)),
    estimateBasis=f'{overhead}-byte reply framing measured at 4,000 bytes; not a measurement at {CONNECTION_SIZE} bytes',
    cause=('CalendarRun.observe issued QUERY_CONFIG on the mailbox writer, which leaves it at the 500-byte frame size, '
           'and passed that writer to the oracle; the oracle gives its observer sockets the primary size'),
    fix=['fraktal_ab_s3i_lifetime_execute.CalendarRun.observe reads through the independent 4,000-byte capture_gate observer',
         'fraktal_ab_paired_observation.read refuses any read socket not at 4,000 bytes before any controller read'])
with output.open('x', encoding='utf-8') as out:
    json.dump(report, out, indent=2)
print(json.dumps({k: report[k] for k in ('failedCapture', 'estimatedRequestsAtWriterSize', 'acceptedFixtureReads')}))

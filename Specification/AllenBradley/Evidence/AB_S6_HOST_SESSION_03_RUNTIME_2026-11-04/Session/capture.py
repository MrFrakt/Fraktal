"""Read-only native capture of both host-event rings on one quiet ring state (WP6.5).

1. The legacy ring, metadata-bracketed (fraktal_ab_host_events.read).
2. The full canonical S1 acquisition (fraktal_ab_canonical_reader.read_document),
   whose Press root record carries Press/HostEvents.
3. The legacy ring again.

The two legacy batches must be identical and the canonical DataRevision equal
to theirs, so all three describe one ring state. Then each leaf the legacy
projection gives (fraktal_ab_host_events.project) is compared with the canonical
leaf of the same path. The raw canonical capture is kept (gzip) so the host
adapter's canonical-ring reader can be proven against it offline.
"""
from pathlib import Path
import datetime, gzip, json, os, subprocess, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s6_host_demo'
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_canonical_reader as reader
import fraktal_ab_host_events as events
import fraktal_ab_models as models
import fraktal_ab_part_execute as fixture
import fraktal_ab_station as station

for name in ('capture_legacy.json', 'capture_canonical.json.gz', 'capture_equivalence.json'):
    assert not (D / name).exists(), name
app = station.application()
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], check=True)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot, native.ConnectionSize, native.SocketTimeout = 0, 4000, 5
    comm = fixture.Guarded(native, 0x601FC87B, app)
    comm.guard()
    codes = models.read(comm, app)
    first = events.read(comm, app, codes)
    snapshot, capture = reader.read_document(native, expect_serial='601FC87B')
    second = events.read(comm, app, codes)
with gzip.open(D / 'capture_canonical.json.gz', 'xt', encoding='utf-8') as stream:
    json.dump(capture, stream)
with (D / 'capture_legacy.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(codes=list(codes), first=first, second=second), stream, indent=1)
canonical = {k[len(app.name) + 1:]: v for k, v in snapshot['values'].items() if k.startswith(app.name + '/HostEvents/')}
projected = events.project(first)
compared = {k: dict(legacy=v, canonical=canonical.get(k, '<absent>'), equal=canonical.get(k, object()) == v)
            for k, v in projected.items()}
report = dict(readOnly=True, serial='601FC87B', events=len(first['events']), metadata=first['metadata'],
              legacyStable=first == second,
              dataRevisionEqual=canonical.get('HostEvents/DataRevision') == first['metadata']['DataRevision'],
              projectedLeaves=len(projected), canonicalLeaves=len(canonical),
              equalLeaves=sum(1 for c in compared.values() if c['equal']),
              differing={k: c for k, c in compared.items() if not c['equal']},
              canonicalOnly=sorted(set(canonical) - set(projected))[:200],
              capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
report['coherent'] = report['legacyStable'] and report['dataRevisionEqual']
report['equivalent'] = report['coherent'] and not report['differing']
with (D / 'capture_equivalence.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=1, default=str)
print(json.dumps({k: report[k] for k in ('events', 'coherent', 'equivalent', 'projectedLeaves', 'equalLeaves')}))
# The capture itself is the stage's product; only an incoherent capture fails it.
raise SystemExit(0 if report['coherent'] else 1)

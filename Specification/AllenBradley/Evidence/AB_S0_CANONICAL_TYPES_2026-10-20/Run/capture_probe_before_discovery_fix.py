"""Read-only raw Symbol/Template/record capture for this exact S0 image."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path('C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7')
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_s0_canonical_measure as measure

destination = Path(sys.argv[1])
if destination.exists():
    raise SystemExit('refusing existing capture output')
subprocess.run([sys.executable, str(WORK/'scripts/guard_echo.py')], check=True)
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot, comm.SocketTimeout, comm.ConnectionSize = 0, 10, 4000
    response = comm.GetTagList(allTags=False)
    if response.Status != 'Success':
        raise RuntimeError('Symbol acquisition failed: ' + str(response.Status))
    tags = response.Value
    if not any(t.TagName == measure.TAG and t.DataType == measure.RECORD for t in tags):
        raise RuntimeError('loaded image is not the S0 probe')
    before = comm.Read('FRK_S12_Scan')
    reply = comm.Read(measure.TAG)
    time.sleep(.2)
    after = comm.Read('FRK_S12_Scan')
    if any(r.Status != 'Success' for r in (before, reply, after)):
        raise RuntimeError('raw record/scan acquisition failed')
    if not isinstance(reply.Value, (bytes, bytearray)):
        raise RuntimeError('record was not returned as raw bytes')
    raw = bytes(reply.Value)
    templates = {}
    for name, udt in comm.UDTByName.items():
        templates[name] = dict(handle=udt.Type, members=measure.member_table(udt),
                               rawMemberDefinitions=[bytes(f.Bytes).hex() for f in udt.Fields])
    report = dict(schema='fraktal.ab.s0-raw-capture', schemaVersion=1,
                  capturedUtc=datetime.now(timezone.utc).isoformat(), readOnly=True,
                  serial='601FC87B', tag=measure.TAG, recordBytes=len(raw), rawHex=raw.hex(),
                  scan=[before.Value, after.Value], scanAdvancing=after.Value > before.Value,
                  symbols=[vars(t) for t in tags], templates=templates)
with destination.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2, default=str)
    stream.write('\n')
print(json.dumps(dict(recordBytes=len(raw), templates=len(templates), scanAdvancing=report['scanAdvancing'])))

"""Read-only local Echo transport diagnostic; no same-scan acceptance claim."""
from pathlib import Path
import datetime
import gzip
import json
import os
import struct
import sys
import time

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_genealogy_demo as demo
import fraktal_ab_press_execute as execute
import fraktal_ab_models as models
import fraktal_ab_paired_reads as batching
import fraktal_ab_part_execute as fixture

output=Path(sys.argv[1])
if output.exists():raise SystemExit('new evidence required')
app=demo.application()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app)
    comm.guard()
    tags=[execute.UNIT,*(execute.MODULE_CTX[m.name] for m in app.modules),models.tag(app)]
    warm={tag:comm.Read(tag) for tag in tags}
    if any(response.Status!='Success' or not isinstance(response.Value,(bytes,bytearray)) for response in warm.values()):
        raise SystemExit('warm UDT acquisition failed')
    sizes={tag:len(response.Value) for tag,response in warm.items()}
    plan=batching.plan(comm,tags,sizes)
    started=time.perf_counter()
    raw=batching.acquire(comm,plan)
    elapsed=(time.perf_counter()-started)*1000
    decoded=batching.decode(plan,raw,sizes)
    checks={tag:struct.unpack_from('<i',answer.Value)[0]==1 and len(answer.Value)==sizes[tag] for tag,answer in decoded.items()}
    report=dict(readOnly=True,sameStateVerified=False,acceptanceClaim=False,serial='601FC87B',
        capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=all(checks.values()),
        legacyTagCount=len(tags),wireReads=len(plan),readMs=elapsed,
        checks=checks,sizes=sizes,plan=[dict(kind=item['kind'],tags=item['tags'],requestHex=item.get('request',b'').hex()) for item in plan],
        frames=[dict(status=status,rawHex=data.hex()) for status,data in raw],
        decoded={tag:answer.Value.hex() for tag,answer in decoded.items()})
with gzip.open(output,'xt',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('frames','decoded','plan')}))
raise SystemExit(0 if report['passed'] else 1)

"""Read-only timing of wire requests on the approved S3b image; no acceptance claim."""
from pathlib import Path
import datetime,json,os,sys,time
ROOT=Path("C:/Users/SoftIndVM/Fraktal")
sys.path.insert(0,str(ROOT/"FraktalCore/PLC/Allen-Bradley/tools"))
os.environ["FRAKTAL_AB_DECLARATION"]="fraktal_ab_genealogy_demo"
from pylogix import PLC
import fraktal_ab_part_execute as fixture,fraktal_ab_genealogy_demo as demo
import fraktal_ab_press_execute as execute,fraktal_ab_models as models
import fraktal_ab_canonical_publication as publisher,fraktal_ab_paired_reads as batching
destination=Path(sys.argv[1])
if destination.exists():raise SystemExit("new output required")
app=demo.application()
with PLC("127.0.0.1") as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
    tags=[app.name,execute.UNIT,*(execute.MODULE_CTX[m.name] for m in app.modules),models.tag(app)]
    warm={tag:comm.Read(tag) for tag in tags}
    assert all(v.Status=="Success" and isinstance(v.Value,bytes) for v in warm.values())
    sizes={tag:len(v.Value) for tag,v in warm.items()}
    read_plan=batching.plan(comm,tags,sizes)
    comm.Read(publisher.generation_tag(app))
    send=comm.conn.send;calls=[]
    def instrument(request,*args,**kwargs):
        start=time.perf_counter();result=send(request,*args,**kwargs);end=time.perf_counter()
        calls.append((start,end,request,result))
        return result
    comm.conn.send=instrument
    runs=[]
    for number in range(3):
        first=len(calls);start=time.perf_counter()
        before=comm.Read(publisher.generation_tag(app)).Value
        replies=batching.acquire(comm,read_plan)
        after=comm.Read(publisher.generation_tag(app)).Value
        elapsed=time.perf_counter()-start
        decoded=batching.decode(read_plan,replies,sizes)
        runs.append(dict(before=before,after=after,readMs=elapsed*1000,calls=len(calls)-first,completeTags=len(decoded)))
    comm.conn.send=send
    report=dict(readOnly=True,acceptanceClaim=False,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        connectionSize=comm.ConnectionSize,sizes=sizes,plan=[{k:v for k,v in i.items() if k!="request"} for i in read_plan],
        runs=runs,calls=[dict(start=a,end=b,milliseconds=(b-a)*1000,requestHex=q.hex(),
                  status=response[0],rawHex=response[1].hex()) for a,b,q,response in calls])
with destination.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!="calls"}))
print(json.dumps([dict(milliseconds=(b-a)*1000,service=q[0],status=response[0],replyBytes=len(response[1])) for a,b,q,response in calls]))

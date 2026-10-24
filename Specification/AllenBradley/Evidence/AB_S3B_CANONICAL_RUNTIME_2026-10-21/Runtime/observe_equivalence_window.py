"""Read-only instrumentation of the actual S3b paired-read plan."""
from pathlib import Path
import datetime,json,os,sys,time
ROOT=Path("C:/Users/SoftIndVM/Fraktal")
sys.path.insert(0,str(ROOT/"FraktalCore/PLC/Allen-Bradley/tools"))
os.environ["FRAKTAL_AB_DECLARATION"]="fraktal_ab_genealogy_demo"
from pylogix import PLC
import fraktal_ab_s3b_equivalence as gate,fraktal_ab_s2_equivalence as shared
import fraktal_ab_paired_reads as batching,fraktal_ab_genealogy_demo as demo,fraktal_ab_part_execute as fixture
output=Path(sys.argv[1])
if output.exists():raise SystemExit("new output required")
observations=[]
original=shared._scan_reads
def measure(comm,tags,generation,**kwargs):
    sizes=kwargs["raw_sizes"];read_plan=batching.plan(comm,tags,sizes)
    observations.append(dict(kind="plan",connectionSize=comm.ConnectionSize,sizes=sizes,
                             plan=[{k:v for k,v in row.items() if k!="request"} for row in read_plan]))
    send=comm.conn.send
    def instrument(request,*args,**kw):
        start=time.perf_counter();response=send(request,*args,**kw);finish=time.perf_counter()
        observations.append(dict(kind="wire",milliseconds=(finish-start)*1000,service=request[0],
                                 status=response[0],bytes=len(response[1] or b"")))
        return response
    comm.conn.send=instrument
    try:return original(comm,tags,generation,**kwargs)
    finally:comm.conn.send=send
shared._scan_reads=measure
try:
    with PLC("127.0.0.1") as native:
        native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
        comm=fixture.Guarded(native,0x601FC87B,demo.application());comm.guard()
        evidence=gate.run(comm)
    report=dict(readOnly=True,passed=evidence["passed"],comparison=evidence["comparison"],observations=observations)
except Exception as error:
    report=dict(readOnly=True,passed=False,error=str(error),attempts=getattr(error,"attempts",[]),observations=observations)
with output.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ("observations","attempts")}))
print(json.dumps(observations[:12]))
raise SystemExit(0 if report["passed"] else 1)

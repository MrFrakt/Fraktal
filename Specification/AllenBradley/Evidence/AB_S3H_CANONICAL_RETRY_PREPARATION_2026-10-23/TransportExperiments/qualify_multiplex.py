"""Read-only 47-request transport qualification on restored Echo genealogy.

Repeats immutable Access audit fragments and data-policy MSPs to reproduce the
failed S3h packet load. This is transport/latency evidence, not S3h acceptance.
No mailbox, mode, output, fault or clock write exists.
"""
from pathlib import Path
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import collections,hashlib,json,os,statistics,subprocess,sys,time
W=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T));os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
from pylogix import PLC
import fraktal_ab_paired_fragments as fragments
import fraktal_ab_paired_reads as reads
import socket_reads
P=Path('C:/work/fraktal-ab-s3h-20261023/prepare_5822102a73e348ec95ff7082959ef940')
subprocess.run([sys.executable,str(P/'scripts/guard_echo.py')],check=True)
destination=Path(sys.argv[1]);assert not destination.exists()
report=dict(readOnly=True,controllerWrites=0,serial='601FC87B',sameScanS3hAcceptance=False,connections=4,requests=47)
try:
    with ExitStack() as stack:
        channels=[]
        for _ in range(4):
            c=stack.enter_context(PLC('127.0.0.1'));c.ProcessorSlot=0;c.ConnectionSize=4000;c.SocketTimeout=3
            d=c.GetDeviceProperties()
            if d.Status!='Success' or (str(d.Value.SerialNumber).lower(),d.Value.ProductName,d.Value.Revision)!=('0x601fc87b','Emulate 5580 Controller','38.11'):
                raise ValueError('exact baseline Echo identity refused')
            for tag in ('FRK_Press_AccessAudit','FRK_Press_DataPolicy'):
                value=c.Read(tag)
                if value.Status!='Success' or not isinstance(value.Value,bytes):raise ValueError('warm baseline UDT unavailable')
            channels.append(c)
        c=channels[0];audit=c.Read('FRK_Press_AccessAudit').Value;policy=c.Read('FRK_Press_DataPolicy').Value
        packet=fragments.packets(c,'FRK_Press_AccessAudit',len(audit))[0]
        batch=reads.plan(c,['FRK_Press_DataPolicy'],{'FRK_Press_DataPolicy':len(policy)})[0]
        items=[packet]*42+[batch]*5;plans=[items[i::4] for i in range(4)]
        golden={kind:channels[0].conn.send(item['request']) for kind,item in (('fragment',packet),('batch',batch))}
        with ThreadPoolExecutor(max_workers=3) as workers:
            for task in [workers.submit(lambda:None) for _ in range(3)]:task.result()
            samples={'sequential':[],'multiplex':[]}
            for i in range(20):
                for mode in ('sequential','multiplex'):
                    started=time.perf_counter()
                    if mode=='multiplex':result=socket_reads.acquire(channels,plans)
                    else:
                        tasks=[workers.submit(reads.acquire,channel,plan) for channel,plan in zip(channels[1:],plans[1:],strict=True)]
                        result=[reads.acquire(channels[0],plans[0])]+[task.result() for task in tasks]
                    elapsed=(time.perf_counter()-started)*1000000
                    for plan,replies in zip(plans,result,strict=True):
                        for item,reply in zip(plan,replies,strict=True):
                            expected=golden[item['kind']]
                            if reply[0]!=expected[0] or reply[1][46:]!=expected[1][46:]:raise ValueError('immutable response differs')
                    after=channels[0].Read('FRK_Press_ScanCount')
                    if after.Status!='Success' or type(after.Value) is not int:raise ValueError('read stream did not drain')
                    samples[mode].append(elapsed)
        if c.Read('FRK_Press_AccessAudit').Value!=audit or c.Read('FRK_Press_DataPolicy').Value!=policy:
            raise ValueError('baseline qualification owner changed')
        report.update(passed=True,samples=samples,latencyUs={mode:dict(minimum=min(v),median=statistics.median(v),maximum=max(v)) for mode,v in samples.items()},
            responsePayloadsExact=True,streamDrainedAfterEveryBurst=True,maximumPendingPerConnection=1,
            auditSha256=hashlib.sha256(audit).hexdigest(),policySha256=hashlib.sha256(policy).hexdigest(),
            qualificationScope='Same-family immutable baseline bytes at 47 packets/four connections; not complete S3h native acceptance')
except Exception as error:report.update(passed=False,error=f'{type(error).__name__}: {error}')
with destination.open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='samples'}))
raise SystemExit(0 if report['passed'] else 1)

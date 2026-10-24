"""Read-only timing proxy on baseline; not canonical S3h scan acceptance."""
from pathlib import Path
from contextlib import ExitStack
import collections,hashlib,json,statistics,subprocess,sys,time
P=Path(__file__).parent;T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools');sys.path.insert(0,str(T))
from pylogix import PLC
import fraktal_ab_paired_fragments as fragments
import fraktal_ab_paired_reads as reads
import fraktal_ab_paired_socket_reads as sockets
from fraktal_ab_canonical_equivalence import stable_scan_pair
subprocess.run([sys.executable,str(P/'scripts/guard_echo.py')],check=True)
report=dict(readOnly=True,controllerWrites=0,connections=4,requestsPerAcquisition=47,
    canonicalS3hAcceptance=False,timingProxy='legacy scan counter over immutable payloads; not the canonical odd/even generation',
    attemptsLimit=100,secondsLimit=5.0,maximumPendingPerConnection=1)
try:
    with ExitStack() as stack:
        channels=[]
        for _ in range(4):
            c=stack.enter_context(PLC('127.0.0.1'));c.ProcessorSlot=0;c.ConnectionSize=4000;c.SocketTimeout=3
            d=c.GetDeviceProperties();assert d.Status=='Success' and (str(d.Value.SerialNumber).lower(),d.Value.Revision,d.Value.ProductName)==('0x601fc87b','38.11','Emulate 5580 Controller')
            for name in ('FRK_Press_AccessAudit','FRK_Press_DataPolicy'):
                r=c.Read(name);assert r.Status=='Success' and isinstance(r.Value,bytes)
            channels.append(c)
        c=channels[0];audit=c.Read('FRK_Press_AccessAudit').Value;policy=c.Read('FRK_Press_DataPolicy').Value
        packet=fragments.packets(c,'FRK_Press_AccessAudit',len(audit))[0]
        batch=reads.plan(c,['FRK_Press_DataPolicy'],{'FRK_Press_DataPolicy':len(policy)})[0]
        items=[packet]*42+[batch]*5;plans=[items[i::4] for i in range(4)]
        golden={k:c.conn.send(v['request']) for k,v in (('fragment',packet),('batch',batch))}
        def counter():
            r=c.Read('FRK_Press_ScanCount')
            if r.Status!='Success' or type(r.Value) is not int or not 0<r.Value<1073741823:raise ValueError('baseline counter unavailable')
            return r.Value*2
        def acquire():
            started=time.perf_counter();raw=sockets.acquire(channels,plans)
            return dict(raw=raw,acquisitionUs=(time.perf_counter()-started)*1000000)
        samples=[]
        for _ in range(1000):
            pair=stable_scan_pair(counter,acquire,fresh_start=True)
            for plan,replies in zip(plans,pair['raw'],strict=True):
                for item,reply in zip(plan,replies,strict=True):
                    expected=golden[item['kind']]
                    if reply[0]!=expected[0] or reply[1][46:]!=expected[1][46:]:raise ValueError('immutable payload differs')
            history=pair['stateEvidence']['attempts']
            samples.append(dict(acquisitionUs=pair['acquisitionUs'],attempts=len(history),
                waitingPolls=sum(bool(r.get('waitingFreshScan')) for r in history),
                readWindows=sum('after' in r for r in history),history=history))
        assert c.Read('FRK_Press_AccessAudit').Value==audit and c.Read('FRK_Press_DataPolicy').Value==policy
        values=[r['acquisitionUs'] for r in samples]
        report.update(passed=True,samples=samples,latencyUs=dict(minimum=min(values),median=statistics.median(values),maximum=max(values)),
            attemptsObserved=dict(minimum=min(r['attempts'] for r in samples),maximum=max(r['attempts'] for r in samples)),
            responsePayloadsExact=True,transportModuleSha256=hashlib.sha256((T/'fraktal_ab_paired_socket_reads.py').read_bytes()).hexdigest())
except Exception as error:report.update(passed=False,error=f'{type(error).__name__}: {error}',attempts=getattr(error,'attempts',[]))
with (P/'scan_start_proxy_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('samples','attempts')}))
raise SystemExit(0 if report['passed'] else 1)

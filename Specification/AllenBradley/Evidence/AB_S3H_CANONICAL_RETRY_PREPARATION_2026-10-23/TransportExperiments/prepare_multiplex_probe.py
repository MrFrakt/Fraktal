from pathlib import Path
W=Path(__file__).parent;t=(W/'qualify_baseline.py').read_text().replace('import read_burst','import socket_reads')
t=t.replace("samples={'sequential':[],'burst':[]}","samples={'sequential':[],'multiplex':[]}")
t=t.replace("for mode in ('sequential','burst'):","for mode in ('sequential','multiplex'):")
old='''                    acquire=reads.acquire if mode=='sequential' else read_burst.acquire
                    started=time.perf_counter()
                    tasks=[workers.submit(acquire,channel,plan) for channel,plan in zip(channels[1:],plans[1:],strict=True)]
                    result=[acquire(channels[0],plans[0])]+[task.result() for task in tasks]'''
new='''                    started=time.perf_counter()
                    if mode=='multiplex':result=socket_reads.acquire(channels,plans)
                    else:
                        tasks=[workers.submit(reads.acquire,channel,plan) for channel,plan in zip(channels[1:],plans[1:],strict=True)]
                        result=[reads.acquire(channels[0],plans[0])]+[task.result() for task in tasks]'''
assert old in t;t=t.replace(old,new,1).replace('maximumPendingPerConnection=16','maximumPendingPerConnection=1')
assert 'read_burst' not in t
with (W/'qualify_multiplex.py').open('x') as f:f.write(t)
print('One-request-per-connection socket multiplex probe prepared')

from pathlib import Path
import json,os,sys,time,collections,statistics
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_paired_reads as batching
import fraktal_ab_s3d_equivalence as gate
from pylogix import PLC
R=Path(__file__).parent;rows=[]
def acquire(comm,plan):
 result=[];row=[]
 for item in plan:
  start=time.perf_counter()
  result.append(comm.Read(item['tags'][0]) if item['kind']=='single' else comm.conn.send(item['request']))
  row.append(dict(kind=item['kind'],tags=item['tags'],milliseconds=1000*(time.perf_counter()-start)))
 rows.append(row)
 return result
batching.acquire=acquire
try:
 with PLC('127.0.0.1') as comm:
  comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=0,4000,10
  result=gate.run(comm)
 outcome=dict(passed=result['passed'])
except Exception as e:outcome=dict(passed=False,error=str(e),attempts=getattr(e,'attempts',[]))
outcome.update(readOnly=True,controllerWrites=0,profile=rows)
with (R/'read_profile_01.json').open('x') as f:json.dump(outcome,f,indent=2)
print(json.dumps(dict(passed=outcome['passed'],attempts=len(rows),first=rows[0] if rows else [],medianWindowMs=statistics.median(sum(i['milliseconds'] for i in row) for row in rows) if rows else None)))

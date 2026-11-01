import sys
sys.path.pop(0)
import asyncio, datetime, json, time, urllib.request
from pathlib import Path
from websockets.asyncio.client import connect

D=Path('C:/work/fraktal-ab-s5-20261029/session_18')

def summarize(body):
    result={}
    data=body.get('dataValues',{})
    for label,fragment in [('timing','/Timing/'),('history','/AlarmLog/Ring[')]:
        rows=[v for p,v in data.items() if fragment in p and isinstance(v,dict)]
        if not rows:continue
        ages=[v['ageMs'] for v in rows if isinstance(v.get('ageMs'),(int,float))]
        statuses={str(s):sum(v.get('status')==s for v in rows) for s in set(v.get('status') for v in rows)}
        result[label]=dict(leaves=len(rows),statuses=statuses,minimumAgeMs=min(ages,default=None),maximumAgeMs=max(ages,default=None))
    return result

async def observe(page,stream):
    async with connect(page['webSocketDebuggerUrl'],proxy=None,max_size=8*1024*1024) as wire:
        await wire.send(json.dumps(dict(id=1,method='Network.enable',params={})))
        deadline=time.monotonic()+55
        while time.monotonic()<deadline:
            try:message=json.loads(await asyncio.wait_for(wire.recv(),timeout=1))
            except asyncio.TimeoutError:continue
            if message.get('method')!='Network.webSocketFrameReceived':continue
            response=message.get('params',{}).get('response',{})
            if response.get('opcode')!=1:continue
            try:body=json.loads(response.get('payloadData','')).get('result')
            except (ValueError,AttributeError):continue
            if not isinstance(body,dict):continue
            summary=summarize(body)
            if summary:
                stream.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target=page['id'],readOnly=True,**summary))+'\n');stream.flush()

async def main():
    with urllib.request.urlopen('http://127.0.0.1:19114/json/list',timeout=2) as response:pages=json.load(response)
    pages=[p for p in pages if p.get('type')=='page' and p.get('url','').startswith('http://127.0.0.1:8080/')]
    with (D/'browser_detail_quality_observation.jsonl').open('x',encoding='utf-8') as stream:
        results=await asyncio.gather(*(observe(p,stream) for p in pages),return_exceptions=True)
    print(json.dumps(dict(readOnly=True,targets=len(pages),errors=[type(r).__name__ for r in results if isinstance(r,BaseException)],credentialValuesRecorded=False)))

asyncio.run(main())

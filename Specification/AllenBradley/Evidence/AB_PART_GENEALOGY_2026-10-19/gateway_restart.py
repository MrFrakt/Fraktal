"""Read-only local gateway process crash/reconnect, using no installed service."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from websockets.asyncio.client import connect

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
OUT = Path(__file__).parent
TOOLS = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
PROTOCOL = 'fraktal.opcua.gateway.v1'


async def exercise():
    env = dict(os.environ, FRAKTAL_AB_DECLARATION='fraktal_ab_genealogy_demo')
    env.pop('FRAKTAL_GATEWAY_WRITE_TOKEN', None)
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    process = None
    rows = []
    for phase in (1, 2):
        with (OUT/f'gateway_02_{phase}.log').open('xb') as log:
            try:
                process = subprocess.Popen([sys.executable,str(TOOLS/'fraktal_ab_gateway.py'),
                    '127.0.0.1','--expect-serial','601FC87B','--host','127.0.0.1','--port',str(port)],
                    stdout=log,stderr=subprocess.STDOUT,env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                deadline=time.monotonic()+30
                while True:
                    if process.poll() is not None:
                        raise RuntimeError('disposable gateway exited during startup')
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}/livez',timeout=2) as response:
                            health=json.load(response)
                        break
                    except OSError:
                        if time.monotonic()>deadline:raise
                        await asyncio.sleep(.1)
                assert health['writeAccess']['enabled'] is False
                async with connect(f'ws://127.0.0.1:{port}/fraktal',max_size=8*1024*1024,origin='http://localhost') as client:
                    async def rpc(identifier,method,params):
                        await client.send(json.dumps(dict(protocol=PROTOCOL,id=identifier,method=method,params=params)))
                        result=json.loads(await asyncio.wait_for(client.recv(),30))
                        assert result['id']==identifier
                        return result
                    reply=await rpc(1,'snapshot',{})
                    assert reply['ok'],reply
                    snapshot=reply['result']
                    values=snapshot['values']
                    assert values['Press/Part/Parents[1]']=='FIXTURE-BLANK-0001'
                    assert values['Press/Part/Parents[2]']=='FIXTURE-INSERT-0002'
                    assert values['Press/HostEvents/SchemaVersion']==5
                    history={path:value for path,value in values.items()
                             if '/HostEvents/' in path or '/Part/' in path}
                    refused=await rpc(2,'write',dict(path='Press/HmiRequest/Kind',type='int32',value=1))
                    assert not refused['ok'] and 'read-only' in refused['error']
                    rows.append(dict(phase=phase,pid=process.pid,paths=len(snapshot['paths']),
                        nodeCount=snapshot['nodeCount'],history=history,writeRefused=True,
                        snapshotSha256=hashlib.sha256(json.dumps(history,sort_keys=True).encode()).hexdigest().upper()))
                    if phase==1:
                        process.kill()
                        process.wait(timeout=10)
                        try:
                            await asyncio.wait_for(client.recv(),10)
                        except Exception:
                            rows[-1]['disconnectObserved']=True
                        else:raise AssertionError('client did not observe process termination')
            finally:
                if process is not None and process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
    assert rows[0]['history']==rows[1]['history'],'gateway restart changed retained PLC history'
    result=dict(schema='fraktal.ab.read-only-gateway-process-restart',version=1,
        passed=True,serial='601FC87B',rows=rows,writeGateEnabled=False,
        plcMutationAttempted=False,installedWindowsServiceTested=False,
        reconnectAndHistoryPreserved=True)
    with (OUT/'gateway_restart.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(dict(passed=True,phases=len(rows),historyPaths=len(rows[0]['history']))))


asyncio.run(exercise())

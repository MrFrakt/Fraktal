"""Observe only the owned Chrome profile. Never click, command or log input values."""
from pathlib import Path
import argparse,asyncio,datetime,json,logging,time,urllib.parse,urllib.request

ORIGIN='http://127.0.0.1:8080'
METHODS={'snapshot','discoverPaths','setReadTiers','refreshSlowPaths','readValues','readDataValues','readConfigurationPage','write','writeBatch'}
TAILS=('/HmiResponse/AckSequence','/HmiRequest/Sequence','/Access/CurrentLevel','/Access/LoginResultSequence','/ModeActive')
STORAGE_EXPRESSION="""(() => { if(location.origin!=='http://127.0.0.1:8080')return {wrongOrigin:true}; const raw=localStorage.getItem('fraktal.hmi.connection.v1'); if(!raw)return {configured:false}; const c=JSON.parse(raw); let endpoint=null; try{const u=new URL(c.endpoint);endpoint={scheme:u.protocol,host:u.hostname,port:u.port,path:u.pathname==='/fraktal'?'/fraktal':'other'};}catch(_){} return {configured:true,transport:['gateway','simulation'].includes(c.transport)?c.transport:'other',endpoint,selectedRootCount:(c.selectedUnitPaths||[]).length};})()"""

def safe_url(raw):
    try:
        uri=urllib.parse.urlsplit(raw)
        return dict(scheme=uri.scheme,host=uri.hostname,port=uri.port,path=uri.path if uri.path in {'/','/fraktal'} else 'other')
    except (ValueError,TypeError):return dict(invalid=True)

def safe_sent(payload):
    try:value=json.loads(payload)
    except (ValueError,TypeError):return dict(invalidRpc=True)
    if not isinstance(value,dict) or value.get('protocol')!='fraktal.opcua.gateway.v1':return None
    method=value.get('method');result=dict(method=method if method in METHODS else 'unknown')
    if isinstance(value.get('id'),int):result['rpcId']=value['id']
    params=value.get('params')
    if method=='writeBatch' and isinstance(params,dict):
        writes=params.get('writes',[])
        if isinstance(writes,list):
            result['writeCount']=len(writes)
            for row in writes:
                if not isinstance(row,dict):continue
                path=row.get('path','');number=row.get('value')
                if not isinstance(path,str) or type(number) is not int:continue
                if path.endswith('/HmiRequest/Kind') and 0<=number<39:result['kind']=number
                if path.endswith('/HmiRequest/Sequence') and 0<=number<=0xffffffff:result['sequence']=number
    return result

def safe_received(payload,paths):
    try:value=json.loads(payload)
    except (ValueError,TypeError):return dict(invalidRpc=True)
    if not isinstance(value,dict):return None
    result=dict(ok=value.get('ok') is True)
    if isinstance(value.get('id'),int):result['rpcId']=value['id']
    body=value.get('result')
    if isinstance(body,bool):result['accepted']=body
    if isinstance(body,dict):
        if isinstance(body.get('paths'),list):
            paths[:]=[p if isinstance(p,str) else '' for p in body['paths']]
            result['pathCount']=len(paths)
        values=body.get('values',body);counters={}
        if isinstance(values,dict):
            for key,number in values.items():
                path=key
                if isinstance(key,str) and key.isdecimal() and int(key)<len(paths):path=paths[int(key)]
                if isinstance(path,str) and path.endswith(TAILS) and type(number) is int:counters[path]=number
        if counters:result['publicCounters']=counters
    return result

def allowed_cdp(method,params):
    if method in {'Network.enable','Page.enable','Runtime.enable'}:return params=={}
    return method=='Runtime.evaluate' and params==dict(expression=STORAGE_EXPRESSION,returnByValue=True)

async def observe(directory,port,seconds):
    from websockets.asyncio.client import connect
    wireLogger=logging.getLogger('fraktal.c12.cdp');wireLogger.disabled=True
    started=time.monotonic();tasks={};recordCount=0
    logfile=(directory/'browser_rpc_events.log').open('x',encoding='utf-8')
    def emit(**facts):
        nonlocal recordCount
        recordCount+=1
        logfile.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),readOnlyObserver=True,**facts))+'\n');logfile.flush()
    async def target(page):
        pathsBySocket={};nextId=1;storageIds=set();lastSettings=None
        async with connect(page['webSocketDebuggerUrl'],proxy=None,max_size=8*1024*1024,open_timeout=5,logger=wireLogger) as wire:
            async def send(method,params):
                nonlocal nextId
                assert allowed_cdp(method,params),'Only read-only CDP instrumentation is allowed'
                identifier=nextId;nextId+=1
                await wire.send(json.dumps(dict(id=identifier,method=method,params=params)))
                return identifier
            for method in ('Network.enable','Page.enable','Runtime.enable'):await send(method,{})
            emit(event='page-observed',target=page['id'],url=safe_url(page['url']))
            ready=directory/'browser_rpc_page_ready.json'
            if not ready.exists():
                with ready.open('x',encoding='utf-8') as stream:
                    json.dump(dict(ready=True,readOnly=True,origin=ORIGIN,target=page['id']),stream)
            nextStorage=0
            while time.monotonic()-started<seconds and not (directory/'browser_rpc_observer_stop.json').exists():
                if time.monotonic()>=nextStorage:
                    storageIds.add(await send('Runtime.evaluate',dict(expression=STORAGE_EXPRESSION,returnByValue=True)))
                    nextStorage=time.monotonic()+2
                try:message=json.loads(await asyncio.wait_for(wire.recv(),timeout=1))
                except asyncio.TimeoutError:continue
                if message.get('id') in storageIds:
                    storageIds.remove(message['id'])
                    settings=message.get('result',{}).get('result',{}).get('value')
                    # The exact read-only expression returns only these fields.
                    if isinstance(settings,dict) and settings!=lastSettings:
                        safe={k:settings[k] for k in ('configured','transport','endpoint','selectedRootCount') if k in settings}
                        emit(event='connection-settings',target=page['id'],settings=safe);lastSettings=settings
                    continue
                method=message.get('method');params=message.get('params',{});socket=params.get('requestId')
                if method=='Page.frameNavigated' and 'parentId' not in params.get('frame',{}):
                    if not params.get('frame',{}).get('url','').startswith(ORIGIN+'/'):
                        emit(event='page-left-scope',target=page['id']);break
                elif method=='Network.webSocketCreated':
                    pathsBySocket[socket]=[];emit(event='websocket-created',target=page['id'],endpoint=safe_url(params.get('url','')))
                elif method in {'Network.webSocketFrameSent','Network.webSocketFrameReceived'}:
                    response=params.get('response',{})
                    if response.get('opcode')!=1:continue
                    payload=response.get('payloadData','')
                    if not isinstance(payload,str) or len(payload)>2*1024*1024:continue
                    safe=safe_sent(payload) if method.endswith('Sent') else safe_received(payload,pathsBySocket.setdefault(socket,[]))
                    if safe is not None:emit(event='rpc-sent' if method.endswith('Sent') else 'rpc-received',target=page['id'],**safe)
                elif method=='Network.webSocketClosed':emit(event='websocket-closed',target=page['id'])
                elif method=='Runtime.consoleAPICalled':
                    for argument in params.get('args',[]):
                        text=argument.get('value')
                        if isinstance(text,str) and text.startswith('[Fraktal/Connection] stage='):
                            import re
                            match=re.match(r'^\[Fraktal/Connection\] stage=([a-z-]+)',text)
                            if match:emit(event='connection-stage',target=page['id'],stage=match[1])
    try:
        with (directory/'browser_rpc_observer_ready.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(ready=True,readOnly=True,credentialsRecorded=False),stream)
        while time.monotonic()-started<seconds and not (directory/'browser_rpc_observer_stop.json').exists():
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=1) as response:pages=json.load(response)
                for page in pages:
                    if page.get('type')=='page' and page.get('url','').startswith(ORIGIN+'/') and page['id'] not in tasks:
                        tasks[page['id']]=asyncio.create_task(target(page))
                for identifier,task in list(tasks.items()):
                    if task.done():
                        try:task.result()
                        except Exception as error:emit(event='page-observer-ended',target=identifier,errorClass=type(error).__name__)
                        del tasks[identifier]
            except Exception as error:
                emit(event='debugger-not-ready',errorClass=type(error).__name__)
            await asyncio.sleep(.5)
    finally:
        for task in tasks.values():task.cancel()
        await asyncio.gather(*tasks.values(),return_exceptions=True)
        logfile.close()
        with (directory/'browser_rpc_observer_result.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(passed=True,readOnly=True,credentialValuesRecorded=False,records=recordCount),stream,indent=2)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True,type=Path);parser.add_argument('--port',required=True,type=int);parser.add_argument('--seconds',required=True,type=int)
    args=parser.parse_args()
    assert 1024<=args.port<=65535 and 1<=args.seconds<=7500
    asyncio.run(observe(args.directory,args.port,args.seconds))

"""Run one labelled profile/debug rehearsal. No controller-changing operations."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,queue,re,subprocess,sys,threading,time
R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI';W=Path(__file__).parent
SDK=Path('C:/work/fraktal-toolchains/flutter-3.47.5')
DART=SDK/'bin/cache/dart-sdk/bin/dart.exe';FLUTTER=SDK/'bin/cache/flutter_tools.snapshot'
CAP=R/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz'
PIN='b0ebfbd06853fbaf1262c3b74549f88f99bd9af37e1585844dc5b9a4291afb4a'
INVENTORY=R/'Specification/AllenBradley/Evidence/AB_S4B_MSP_PREPARATION_2026-10-27/Preparation/desktop_expected_inventory.json'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
parser.add_argument('--mode',choices=('profile','debug'),default='profile');parser.add_argument('--seed',type=int,default=7)
parser.add_argument('--delay-scale',type=float,default=1)
a=parser.parse_args();assert a.label.replace('_','').isalnum()
O=W/a.label;O.mkdir();assert hashlib.sha256(CAP.read_bytes()).hexdigest()==PIN
sources={}
for relative in ('tool/cip_rehearsal_peer.dart','test/cip_rehearsal_peer_test.dart',
    'integration_test/ab_desktop_acceptance_test.dart','test_driver/integration_test.dart',
    'lib/data/opcua_repository.dart','packages/fraktal_opcua_client/lib/src/cip_session_client.dart',
    'packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',
    'packages/fraktal_opcua_client/lib/src/cip_read_pool.dart',
    'packages/fraktal_opcua_client/lib/src/cip_read_coherence.dart',
    'packages/fraktal_opcua_client/lib/src/cip_operation_queue.dart',
    'packages/fraktal_opcua_client/lib/src/cip_transport.dart',
    'packages/fraktal_opcua_client/lib/src/cip_config_read_view.dart',
    'packages/fraktal_opcua_client/lib/src/cip_publication.dart',
    'test/cip_config_read_view_test.dart',
    'test/cip_operation_queue_test.dart',
    'test/cip_read_coherence_test.dart','test/cip_read_plan_test.dart',
    'test/cip_coalesced_read_test.dart','test/cip_session_client_test.dart',
    'test/opcua_freshness_test.dart','test/cip_read_pool_test.dart',
    'test/reconnecting_opcua_session_client_test.dart',
    'lib/data/opcua_session_client.dart','lib/data/reconnecting_opcua_session_client.dart',
    'packages/fraktal_opcua_client/lib/src/opcua_session_client.dart',
    'tool/qualify_cip_canonical.dart','test/cip_qualification_test.dart',
    'pubspec.yaml','pubspec.lock'):
    raw=(H/relative).read_bytes();target=O/'Sources'/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    sources[relative]=hashlib.sha256(raw).hexdigest()
with (O/'sources.json').open('x') as f:json.dump(sources,f,indent=2)
env=os.environ.copy();env['FLUTTER_ROOT']=str(SDK);env['FRAKTAL_AB_DESKTOP_EXPECTED_INVENTORY']=str(INVENTORY)
env['PATH']=str(SDK/'bin')+os.pathsep+env['PATH']
flags=dict(creationflags=subprocess.CREATE_NO_WINDOW) if os.name=='nt' else {}
def save(name,value):
    with (O/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
def baseline(label):
    command=[sys.executable,'C:/work/fraktal-ab-s4b-msp-20261027/session_01/scripts/preflight.py','--verify-only']
    with (O/(label+'.log')).open('x',encoding='utf-8') as f:p=subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT,**flags)
    assert p.returncode==0,'Genealogy baseline read-only check failed; do not touch Echo'
baseline('echo_before')
peer_command=[str(DART),'run','tool/cip_rehearsal_peer.dart','--capture',str(CAP),
    '--expect-sha256',PIN,'--seed',str(a.seed),'--delay-scale',str(a.delay_scale)]
ready=queue.Queue();peer_log=(O/'peer.log').open('x',encoding='utf-8')
p=subprocess.Popen(peer_command,cwd=H,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,text=True,encoding='utf-8',**flags)
def output():
    for line in p.stdout:
        peer_log.write(line);peer_log.flush()
        try:
            marker=line.find('{')
            if marker<0:continue
            value=json.loads(line[marker:])
            if value.get('rehearsalPeer'):ready.put(value)
        except ValueError:pass
thread=threading.Thread(target=output,daemon=True);thread.start()
started=datetime.datetime.now(datetime.timezone.utc).isoformat();code=None;error=None;forced=False;command=[]
try:
    status=ready.get(timeout=30);save('peer_ready.json',status)
    assert status['sha256']==PIN and status['serial']=='601FC87B' and status['delayScale']==a.delay_scale
    endpoint=f"cip://127.0.0.1:{status['port']}?slot=0&serial=601FC87B"
    assert status['port']!=44818
    common=['--no-pub','--dart-define=fraktal.cip.trace=true',
        '--dart-define=fraktal.ab.desktop.rehearsal=true',
        '--dart-define=fraktal.ab.desktop.endpoint='+endpoint,
        '--dart-define=fraktal.ab.desktop.output='+str(O/'desktop')]
    if a.mode=='profile':
        command=[str(DART),str(FLUTTER),'drive','--profile','-d','windows',
            '--driver=test_driver/integration_test.dart','--target=integration_test/ab_desktop_acceptance_test.dart',*common]
    else:
        command=[str(DART),str(FLUTTER),'test','--reporter','expanded',
            str(W/'debug_rehearsal_test.dart'),*common]
    save('command.json',dict(command=command,peerCommand=peer_command,endpoint=endpoint,mode=a.mode,
        expectedInventorySha256=hashlib.sha256(INVENTORY.read_bytes()).hexdigest(),captureSha256=PIN,
        delayScale=a.delay_scale,apparatusOnly=a.delay_scale!=1))
    print(json.dumps(dict(stage='desktop-rehearsal',mode=a.mode,port=status['port'],label=a.label)),flush=True)
    with (O/'desktop.log').open('x',encoding='utf-8') as f:
        run=subprocess.run(command,cwd=H,env=env,stdout=f,stderr=subprocess.STDOUT,**flags)
    code=run.returncode
except Exception as e:error=f'{type(e).__name__}: {e}'
finally:
    if p.poll() is None:
        p.stdin.write('stop\n');p.stdin.flush()
        try:p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            forced=True;p.terminate();p.wait(timeout=10) # local rehearsal peer only
    thread.join(timeout=5);peer_log.close()
    baseline('echo_after')
result_path=O/'desktop/result.json';coverage=json.loads(result_path.read_bytes()) if result_path.exists() else None
refresh=(O/'desktop/refresh.log').read_text(encoding='utf-8') if (O/'desktop/refresh.log').exists() else ''
ages=[int(v) for v in re.findall(r'stage=complete-sample-mapped effectiveAgeUs=(\d+)',refresh)]
save('result.json',dict(startUtc=started,endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    exitCode=code,error=error,captureSha256=PIN,mode=a.mode,seed=a.seed,forcedPeerShutdown=forced,
    completed=coverage is not None,passed=bool(code==0 and coverage and coverage['rehearsalPassed']),
    maxMappedEffectiveAgeUs=max(ages) if ages else None,mappedSnapshots=len(ages),
    rehearsalMarginPassed=bool(a.delay_scale==1 and ages and max(ages)<=700000),
    delayScale=a.delay_scale,apparatusOnly=a.delay_scale!=1,nativeAcceptanceClaim=False,
    controllerChanges=0,genealogyBeforeAfterVerified=True))
print(json.dumps(dict(label=a.label,exitCode=code,error=error,mappedSnapshots=len(ages),maxEffectiveAgeUs=max(ages) if ages else None)))
raise SystemExit(0 if code==0 and coverage and coverage['rehearsalPassed'] and ages and max(ages)<=700000 else 1)

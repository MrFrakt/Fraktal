"""Fresh observer rehearsal against the immutable read-only loopback peer."""
from pathlib import Path
import gzip,hashlib,json,queue,subprocess,threading
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
SDK=Path('C:/work/fraktal-toolchains/flutter-3.47.5');DART=SDK/'bin/cache/dart-sdk/bin/dart.exe'
CAP=R/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz'
PIN='b0ebfbd06853fbaf1262c3b74549f88f99bd9af37e1585844dc5b9a4291afb4a'
assert hashlib.sha256(CAP.read_bytes()).hexdigest()==PIN
flags=dict(creationflags=subprocess.CREATE_NO_WINDOW)
ready=queue.Queue();lines=[]
with (W/'observer_peer_wire_01.log').open('x',encoding='utf-8') as log:
    peer=subprocess.Popen([str(DART),'run','tool/cip_rehearsal_peer.dart','--capture',str(CAP),
        '--expect-sha256',PIN,'--seed','8','--delay-scale','1'],cwd=H,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',**flags)
    def reader():
        for line in peer.stdout:
            log.write(line);log.flush()
            try:
                value=json.loads(line[line.index('{'):]);lines.append(value)
                if value.get('rehearsalPeer'):ready.put(value)
            except (ValueError,TypeError):pass
    thread=threading.Thread(target=reader,daemon=True);thread.start()
    forced=False
    try:
        marker=ready.get(timeout=30)
        assert marker['sha256']==PIN and marker['serial']=='601FC87B' and marker['port']!=44818
        endpoint=f"cip://127.0.0.1:{marker['port']}?slot=0&serial=601FC87B"
        command=[str(DART),'-Dfraktal.cip.trace=true','--packages='+str(H/'.dart_tool/package_config.json'),
            str(H/'tool/qualify_cip_canonical.dart'),'--endpoint',endpoint,
            '--output',str(W/'observer_01.json.gz'),'--samples','100']
        with (W/'observer_01.log').open('x',encoding='utf-8') as output:
            completed=subprocess.run(command,cwd=H,stdout=output,stderr=subprocess.STDOUT,timeout=180,**flags)
        with (W/'configuration_peer_01.log').open('x',encoding='utf-8') as output:
            configuration=subprocess.run([str(DART),'--packages='+str(H/'.dart_tool/package_config.json'),
                str(H/'tool/qualify_cip_configuration.dart'),endpoint,str(W/'configuration_peer_01.json.gz')],
                cwd=H,stdout=output,stderr=subprocess.STDOUT,timeout=180,**flags)
    finally:
        peer.stdin.write('stop\n');peer.stdin.flush()
        try:peer_code=peer.wait(timeout=15)
        except subprocess.TimeoutExpired:
            forced=True;peer.terminate();peer.wait(timeout=5)
        thread.join(timeout=5)
report=json.loads(gzip.decompress((W/'observer_01.json.gz').read_bytes()))
configuration_report=json.loads(gzip.decompress((W/'configuration_peer_01.json.gz').read_bytes()))
assert configuration.returncode==0 and configuration_report['passed'] and configuration_report['writes']==0
import sys
sys.path.insert(0,str(W))
from configuration_comparison import compare
frozen=R/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/idle_equivalence.json.gz'
comparison=compare(configuration_report,json.loads(gzip.decompress(frozen.read_bytes())))
with (W/'configuration_peer_comparison_01.json').open('x') as stream:json.dump(comparison,stream,indent=2)

last=lines[-1]
passed=completed.returncode==0 and report['passed'] and len(report['samples'])==100 and len(report['configurationPages'])==4 and not forced and peer_code==0
result=dict(passed=passed,readOnly=True,controllerAccess=False,controllerChanges=0,
    endpoint=endpoint,samples=len(report['samples']),configurationPages=len(report['configurationPages']),
    badSamples=sum(row['bad'] for row in report['samples']),clientExit=completed.returncode,
    peerExit=peer_code,forcedPeerShutdown=forced,peerWrites=last.get('controllerWrites'),
    refusedServices=last.get('refusedServices'),sourceSha256={name:hashlib.sha256((H/name).read_bytes()).hexdigest()
        for name in ['tool/qualify_cip_canonical.dart','test/cip_qualification_test.dart','tool/qualify_cip_configuration.dart','test/cip_configuration_qualification_test.dart']})
with (W/'observer_peer_qualification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
assert passed and result['badSamples']==result['peerWrites']==result['refusedServices']==0

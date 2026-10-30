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
with (W/'header_peer_wire_01.log').open('x',encoding='utf-8') as log:
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
        command=[str(DART),'--packages='+str(H/'.dart_tool/package_config.json'),
            str(W/'header_probe_01.dart'),endpoint,str(W/'header_probe_01.json.gz')]
        with (W/'header_probe_01.log').open('x',encoding='utf-8') as output:
            completed=subprocess.run(command,cwd=H,stdout=output,stderr=subprocess.STDOUT,timeout=180,**flags)
    finally:
        peer.stdin.write('stop\n');peer.stdin.flush()
        try:peer_code=peer.wait(timeout=15)
        except subprocess.TimeoutExpired:
            forced=True;peer.terminate();peer.wait(timeout=5)
        thread.join(timeout=5)
assert completed.returncode==0 and peer_code==0 and not forced
report=json.loads(gzip.decompress((W/'header_probe_01.json.gz').read_bytes()))
assert report['measurementComplete'] and report['controllerChanges']==0
last=lines[-1];assert last['controllerWrites']==last['refusedServices']==0
print(json.dumps(dict(measurementComplete=True,samples=len(report['outcomes']),
    firstRefused=not report['outcomes'][-1]['good'],controllerChanges=0)))

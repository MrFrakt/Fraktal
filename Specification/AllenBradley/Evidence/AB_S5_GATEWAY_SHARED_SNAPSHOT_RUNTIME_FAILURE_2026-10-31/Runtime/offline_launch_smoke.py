"""Exact packaged gateway arguments against a read-only loopback peer; never Echo."""
from pathlib import Path
import json,socket,subprocess,time,urllib.request
from gateway_stage import gateway_arguments,ready,save,D,H,DAR

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    namespace='launch_02'
    package=D/'gateway_package';peer=None;gateway=None;records=[]
    peerlog=(D/(namespace+'_peer_stderr.log')).open('x',encoding='utf-8')
    try:
        peer=subprocess.Popen([str(DAR),'--packages='+str(D/'dart_package_config.json'),
            str(H/'tool/cip_rehearsal_peer.dart'),'--capture',str(H/'test/fixtures/cip_owner_apparatus_v610.json.gz'),
            '--port','0','--delay-scale','0'],cwd=H,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=peerlog,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        first=peer.stdout.readline();status=json.loads(first)
        port=status['port'];assert port!=44818
        endpoint=f'cip://127.0.0.1:{port}?slot=0&serial=601FC87B'
        for name,write in [('echo',True),('echo-view',False)]:
            http=free_port();log=(D/f'{namespace}_{name}.log').open('x',encoding='utf-8')
            try:
                args=gateway_arguments(package/'fraktal_gateway.exe',package,name,http,write,endpoint=endpoint)
                gateway=subprocess.Popen(args,cwd=package,stdout=log,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                value=ready(gateway,http,write)
                records.append(dict(name=name,passed=True,writeAccess=value['writeAccess'],ready=value))
            finally:
                if gateway is not None and gateway.poll() is None:
                    gateway.terminate();gateway.wait(timeout=15)
                gateway=None;log.close()
    finally:
        if gateway is not None and gateway.poll() is None:gateway.terminate();gateway.wait(timeout=15)
        if peer is not None and peer.poll() is None:
            peer.communicate('stop\n',timeout=15)
        peerlog.close()
    save('offline_launch_smoke_02.json',dict(passed=True,syntheticPeer=True,controllerAccess=False,
        writes=0,postures=records,ownedProcessesClosed=True))
    print(json.dumps(dict(passed=True,postures=len(records),controllerAccess=False,writes=0)))
if __name__=='__main__':main()

"""Own only the two temporary S5 gateway processes and the prebuilt HMI test.

The controller session owner performs download/rollback. This helper never
changes Echo power, mode or vendor state. C11 terminates only its own gateway.
"""
from pathlib import Path
import gzip,hashlib,json,os,subprocess,sys,time,urllib.request
from s5_session import authorize
from configuration_comparison import compare
D=Path(__file__).parent
R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
SDK=Path('C:/work/fraktal-toolchains/flutter-3.47.5')
DAR=SDK/'bin/cache/dart-sdk/bin/dart.exe'

def save(name,value):
    target=D/name;temporary=D/(name+'.tmp')
    assert target.parent.resolve()==D.resolve() and not target.exists()
    with temporary.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
        stream.flush();os.fsync(stream.fileno())
    temporary.rename(target)

def ready(process,port,enabled,timeout=90):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('owned gateway exited during startup')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/readyz',timeout=2) as response:
                value=json.load(response)
            assert value['writeAccess']['enabled'] is enabled
            assert value['writeAccess']['roots']==(['Press'] if enabled else [])
            return value
        except (OSError,ValueError):time.sleep(.1)
    raise TimeoutError('owned gateway readiness timed out')

def gateway_arguments(executable,package,name,port,write,*,endpoint='cip://127.0.0.1?slot=0&serial=601FC87B'):
    command=[str(executable),'--plc-endpoint',endpoint,
        '--instance-name',name,'--port',str(port),'--connect-timeout-ms','60000',
        '--security-profile','commissioning-anonymous','--commissioning-ttl-minutes','60',
        '--web-root',str(package/'web')]
    if write:command+=['--write-root','Press']
    return command

def main():
    authorize(json.loads((D/'authorization.json').read_bytes()))
    package=D/'gateway_package'; executable=package/'fraktal_gateway.exe'
    bound=json.loads((D/'gateway_package_hashes.json').read_bytes())['sha256']
    for name,expected in bound.items():
        assert hashlib.sha256((package/name).read_bytes()).hexdigest().upper()==expected
    profile_dir=D/'qualification_app_03'
    bound_profile=json.loads((D/'qualification_app_03_hashes.json').read_bytes())['sha256']
    for name,expected in bound_profile.items():
        assert hashlib.sha256((profile_dir/name).read_bytes()).hexdigest().upper()==expected
    # Refuse port collisions without disturbing an existing process.
    import socket
    for port in [8080,8081]:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',port))
    processes={};logs=[];starts={};restarts=0
    def start(name,port,write):
        starts[name]=starts.get(name,0)+1
        logfile=(D/f'gateway_{name}_{starts[name]:02}.log').open('x',encoding='utf-8')
        logs.append(logfile)
        command=gateway_arguments(executable,package,name,port,write)
        process=subprocess.Popen(command,cwd=package,stdout=logfile,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        processes[name]=process
        ready(process,port,write)
        return process
    def stop(name):
        process=processes.pop(name,None)
        if process is not None and process.poll() is None:
            assert Path(process.args[0]).resolve()==executable.resolve()
            process.terminate() # only our temporary Dart gateway; never Echo
            process.wait(timeout=15)
    test=None;testlog=None;error=None
    try:
        start('echo',8080,True);start('echo-view',8081,False)
        testlog=(D/'gateway_profile.log').open('x',encoding='utf-8')
        command=[str(DAR),str(SDK/'bin/cache/flutter_tools.snapshot'),'drive','--profile','--no-pub',
            '-d','windows','--driver=test_driver/integration_test.dart',
            '--target=integration_test/ab_gateway_acceptance_test.dart',
            '--use-application-binary='+str(profile_dir/'fraktal_hmi.exe')]
        test=subprocess.Popen(command,cwd=H,stdout=testlog,stderr=subprocess.STDOUT,
            env=dict(os.environ,FLUTTER_ROOT=str(SDK)),creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+1200
        while test.poll() is None:
            if time.monotonic()>deadline:raise TimeoutError('S5 profile deadline exceeded')
            if (D/'gateway_config_oracle_requested.json').exists() and not (D/'gateway_configuration_comparison.json').exists():
                result=dict(passed=False,readOnly=True)
                try:
                    code=subprocess.call([sys.executable,str(D/'run_logged.py'),'gateway_config_oracle',
                        sys.executable,str(D/'candidate_equivalence.py'),'--expect-serial','601FC87B',
                        '--output',str(D/'gateway_configuration_oracle.json.gz')],cwd=R)
                    assert code==0,'independent oracle refused'
                    actual=json.loads((D/'gateway_configuration_pages.json').read_bytes())
                    oracle=json.loads(gzip.decompress((D/'gateway_configuration_oracle.json.gz').read_bytes()))
                    result=compare(actual,oracle)
                except Exception as caught:result['error']=f'{type(caught).__name__}: {caught}'
                save('gateway_configuration_comparison.json',result)
            if (D/'gateway_stop_requested.json').exists() and not (D/'gateway_stopped.json').exists():
                stop('echo');save('gateway_stopped.json',dict(stopped=True,onlyOwnedGateway=True))
            if (D/'gateway_restart_requested.json').exists() and not (D/'gateway_restarted.json').exists():
                start('echo',8080,True);restarts+=1
                save('gateway_restarted.json',dict(restarted=True,onlyOwnedGateway=True))
            time.sleep(.05)
        if test.returncode:raise RuntimeError('prebuilt gateway HMI qualification refused; raw log retained')
        result=json.loads((D/'gateway_profile_result.json').read_bytes())
        assert result['passed'] and len(result['cases'])==12
    except Exception as caught:error=f'{type(caught).__name__}: {caught}'
    finally:
        if test is not None and test.poll() is None:
            test.terminate() # only this test application; never Echo
            test.wait(timeout=15)
        for name in list(processes):stop(name)
        if testlog:testlog.close()
        for stream in logs:stream.close()
        save('gateway_stage_result.json',dict(passed=error is None,error=error,
            gatewayRestarts=restarts,controllerPowerOperations=0,echoHardKills=0,
            commissioning=True,productionSecurityClaim=False,ownerBrowserC12Pending=True))
    if error:raise RuntimeError(error)
if __name__=='__main__':main()

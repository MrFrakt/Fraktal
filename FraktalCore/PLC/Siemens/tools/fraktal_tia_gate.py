"""Fresh-source TIA gate. Native/bench stages are explicit and isolated."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
TIA=HERE.parent
REPO=TIA.parents[2]


def execute(command,log,cwd=REPO):
    with log.open('xb') as stream:result=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError('Gate failed: '+log.name)


def compile_fresh(revision,project_dir,station_name,profile,log,hardware=()):
    """Import one generated revision into a fresh reserved project; require a clean compile and exact read-back.

    `hardware` adds driver lines after the CPU exists (an IO system, devices,
    modules): a fixture whose code names hardware constants brings its hardware."""
    from fraktal_tia_program_layout import organize
    sys.path.insert(0,str(TIA/'Tests/Line'))
    from run_bench import DRIVER,DRIVER_SHA256
    if hashlib.sha256(DRIVER.read_bytes()).hexdigest()!=DRIVER_SHA256:raise ValueError('approved driver hash differs')
    if project_dir.exists():raise ValueError('fresh gate engineering directory already exists')
    selected=json.loads(profile.read_bytes())
    project=project_dir/station_name/(station_name+'.ap20')
    organize(revision/'sources',revision/'grouped',project,revision/'native')
    plan=revision/'grouped/import.plan'
    tail=plan.read_text('ascii').split('\n',1)[1]
    creation=['create-project --dir "'+str(project_dir)+'" --name '+station_name,
              'add-device --order "OrderNumber:6ES7 516-3AP03-0AB0/V3.0" --name PLC_1 --station TiaGate',
              'set-ip --plc PLC_1 --ip '+selected['address']+' --mask 255.255.0.0 --item "PROFINET interface_1"',
              'set-ip --plc PLC_1 --ip '+selected['secondary']+' --mask 255.255.255.0 --item "PROFINET interface_2"',
              'master-secret --plc PLC_1 --mode none',
              'service-set --plc PLC_1 --service PlcAccessLevelProvider --prop PlcProtectionAccessLevel --value FullAccess',
              'project-set --prop IsSimulationDuringBlockCompilationEnabled --value true',*hardware,'save']
    plan.write_bytes(('\n'.join(creation)+'\n'+tail.replace('\ncompile --plc PLC_1\n','\nsave\ncompile --plc PLC_1\n')).encode('ascii'))
    execute([sys.executable,'-B',str(TIA/'Spikes/S12_TypeMap/run_plan.py'),str(plan),str(revision/'build.log'),'--driver',str(DRIVER),'--require-clean-compile'],log)
    verifier=importlib.util.spec_from_file_location('native_readback',TIA/'Tests/Line/verify_owner_exports.py')
    module=importlib.util.module_from_spec(verifier);verifier.loader.exec_module(module)
    verified=module.verify(revision/'sources',revision/'native')
    (revision/'owner_verified_private.json').write_text(json.dumps(verified,indent=2)+'\n',encoding='ascii')
    return project


def bench_suite(output,revision,profile,project,prefix=''):
    """Host one reserved isolated test CPU, download the revision and read its native assertions."""
    stop=output/(prefix+'bench.stop');helper=HERE/'Invoke-TiaIsolatedBench.ps1';log=output/(prefix+'host.log')
    with log.open('xb') as stdout,(output/(prefix+'host.stderr')).open('xb') as stderr:
        host=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(helper),'-Profile',str(profile),'-Action','host','-StopFile',str(stop)],stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline=time.monotonic()+60
            while not any(json.loads(line).get('event')=='bench' for line in log.read_text('utf-8-sig').splitlines() if line.startswith('{') and line.endswith('}')):
                if host.poll() is not None or time.monotonic()>deadline:raise RuntimeError('isolated test host did not become ready')
                time.sleep(.25)
            execute([sys.executable,'-B',str(HERE/'fraktal_tia_test.py'),'--profile',str(profile),'--project',str(project),'--revision',str(revision),'--download'],output/(prefix+'native_test.log'))
        finally:
            stop.touch(exist_ok=False)
            try:host.wait(timeout=40)
            except subprocess.TimeoutExpired:raise RuntimeError('test host cleanup did not finish; inspect host log')


def run(output,native=False,bench=False):
    local=Path(os.environ['LOCALAPPDATA'])/'Fraktal'
    output=output.resolve()
    if not output.is_relative_to(local/'TiaSpikes'):raise ValueError('gate output must be a new directory under local Fraktal/TiaSpikes')
    if bench and not native:raise ValueError('bench stage requires native compile')
    output.mkdir(parents=True,exist_ok=False)
    gates=[('lint',[sys.executable,'-B',str(HERE/'tia_lint.py')]),
           ('tools',[sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-t',str(HERE),'-q']),
           ('consistency',[sys.executable,'-B',str(REPO/'tools/check_consistency.py')]),
           ('contracts',[sys.executable,'-B',str(REPO/'tools/check_tia_contracts.py')])]
    for name,command in gates:execute(command,output/(name+'.log'))
    import fraktal_tia_examples as examples
    examples.generate(output/'press')
    replay=examples.verify(output/'press')
    (output/'press_replay.json').write_text(json.dumps(replay,indent=2)+'\n',encoding='ascii')
    fixture=TIA/'Tests/Operations/make_fixture.py'
    execute([sys.executable,'-B',str(fixture),str(output/'native/sources')],output/'generate.log')
    execute([sys.executable,'-B',str(HERE/'tia_lint.py'),str(output/'native/sources')],output/'fixture_lint.log')
    modules=TIA/'Tests/ReusableModules/make_fixture.py'
    execute([sys.executable,'-B',str(modules),str(output/'modules/sources')],output/'modules_generate.log')
    execute([sys.executable,'-B',str(HERE/'tia_lint.py'),str(output/'modules/sources')],output/'modules_lint.log')
    profinet=TIA/'Tests/ProfinetHealth/make_fixture.py'
    execute([sys.executable,'-B',str(profinet),str(output/'profinet/sources')],output/'profinet_generate.log')
    execute([sys.executable,'-B',str(HERE/'tia_lint.py'),str(output/'profinet/sources')],output/'profinet_lint.log')
    if native:
        local_stations=local/'TiaStations'
        spec=importlib.util.spec_from_file_location('profinet_fixture',profinet)
        hardware=importlib.util.module_from_spec(spec);spec.loader.exec_module(hardware)
        # Each fixed profile is reserved for tests; no physical adapter is mapped.
        # (revision, profile, station, project directory, log prefix, hardware lines)
        suites=[(output/'native',TIA/'Tests/Operations/bench.json','FrkTiaGate',output.name,'',()),
                (output/'modules',TIA/'Tests/ReusableModules/bench.json','FrkTiaModules',output.name+'_Modules','modules_',()),
                (output/'profinet',TIA/'Tests/ProfinetHealth/bench.json','FrkTiaProfinet',output.name+'_Profinet','profinet_',hardware.HARDWARE)]
        projects=[compile_fresh(revision,local_stations/directory,station,profile,output/((prefix or 'native_')+'compile.log'),lines)
                  for revision,profile,station,directory,prefix,lines in suites]
        if bench:
            # One isolated test CPU at a time; each is released before the next.
            for (revision,profile,station,directory,prefix,lines),project in zip(suites,projects):
                bench_suite(output,revision,profile,project,prefix)
    with (output/'gate.json').open('x',encoding='ascii',newline='\n') as stream:
        json.dump(dict(result='PASS',native=native,bench=bench,press_sources=replay['replayed_sources'],profile='isolated reference S7-1500',physical_reference_qualified=False),stream,indent=2);stream.write('\n')
    print(json.dumps(dict(result='PASS',native=native,bench=bench,output=str(output))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--native',action='store_true');p.add_argument('--bench',action='store_true')
    a=p.parse_args();run(a.output,a.native,a.bench)

"""Apply reviewable S4b-Q orchestration changes; no controller access."""
from pathlib import Path
D=Path(__file__).parent
p=D/'qualification_session_v2.py';s=p.read_text(encoding='utf-8')
old="        run('desktop_readonly', PY, D / 'desktop_readonly.py')\n        run('idle_equivalence', PY, D / 'candidate_equivalence.py', '--expect-serial', '601FC87B',\n            '--output', D / 'idle_equivalence.json.gz')\n        run('generic_acquire', PY, T / 'fraktal_ab_canonical_acquire.py', '--expect-serial', '601FC87B',\n            '--output', D / 'generic_snapshot.json.gz', '--capture-output', D / 'generic_capture.json.gz')\n        run('candidate_timing', PY, PRIOR / 'measure_timing.py', D / 'candidate_timing.json', '--candidate')"
new="""        from readonly_stages import execute_readonly_stages
        read_errors=[]
        try:
            run('replay_fixture', PY, D / 'replay_fixture.py')
        except Exception as error:
            read_errors.append(dict(stage='replay_fixture',error=f'{type(error).__name__}: {error}'))
        read_errors += execute_readonly_stages(run,python=PY,directory=D,tools=T,timing=D/'measure_timing.py')
        save('readonly_stage_failures.json',dict(readOnly=True,errors=read_errors))
        if read_errors:
            raise RuntimeError('read-only qualification stages failed: '+', '.join(e['stage'] for e in read_errors))"""
assert s.count(old)==1;s=s.replace(old,new)
old="    monitor = None\n    monitor_log = None"
new="""    monitor = None
    monitor_log = None
    cpu = None
    cpu_log = None"""
assert s.count(old)==1;s=s.replace(old,new)
old="        nonlocal monitor,monitor_log"
new="        nonlocal monitor,monitor_log,cpu,cpu_log"
assert s.count(old)==1;s=s.replace(old,new)
old="        wait_for_ready(D/'task_monitor_ready.json',dict(ready=True,readOnly=True,serial='601FC87B'),monitor,timeout=10)"
new=old+"""
        cpu_log=(D/'host_cpu_monitor.log').open('x',encoding='utf-8')
        cpu=subprocess.Popen(['powershell','-NoProfile','-NonInteractive','-File',str(D/'host_cpu_monitor.ps1'),
            '-OutFile',str(D/'host_cpu.csv'),'-ReadyFile',str(D/'host_cpu_ready.json'),
            '-StopFile',str(D/'host_cpu_stop.json')],cwd=ROOT,stdout=cpu_log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        wait_for_ready(D/'host_cpu_ready.json',dict(ready=True,readOnly=True),cpu,timeout=20)"""
assert s.count(old)==1;s=s.replace(old,new)
# Stop the CPU helper even if readiness or the TASK helper failed.
old="    def finish_monitor():\n        if monitor is None:"
new="""    def finish_monitor():
        if cpu is not None:
            with (D/'host_cpu_stop.json').open('x') as stream:json.dump(dict(stop=True),stream)
            try:
                cpu_code=cpu.wait(timeout=15)
            except subprocess.TimeoutExpired:
                cpu.terminate() # this read-only sampler only; never Echo
                cpu.wait(timeout=10)
                cpu_code=1
            cpu_log.close()
            save('host_cpu_monitor_exit.json',dict(exitCode=cpu_code,readOnly=True))
        if monitor is None:"""
assert s.count(old)==1;s=s.replace(old,new)
old="        if code:\n            raise RuntimeError('read-only TASK monitor failed; observations retained')"
new="        if code or (cpu is not None and cpu_code):\n            raise RuntimeError('read-only TASK/CPU monitor failed; observations retained')"
assert s.count(old)==1;s=s.replace(old,new)
old="        if (D / 'deploy_attempt.json').exists():"
new="""        if (D/'candidate_run_requested.json').exists():
            try:
                run('native_read_gates', PY, D/'check_native_read_gates.py')
            except Exception as error:
                if candidate_error is None: candidate_error=f'{type(error).__name__}: {error}'
        if (D / 'deploy_attempt.json').exists():"""
assert s.count(old)==1;s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
prior=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
s=(prior/'measure_timing.py').read_text(encoding='utf-8')
assert s.count(prior.as_posix())==1;s=s.replace(prior.as_posix(),D.as_posix())
with (D/'measure_timing.py').open('x',encoding='utf-8') as f:f.write(s)
print('S4b-Q order/failure isolation, monitor lifecycle and final read gates prepared; no controller access')

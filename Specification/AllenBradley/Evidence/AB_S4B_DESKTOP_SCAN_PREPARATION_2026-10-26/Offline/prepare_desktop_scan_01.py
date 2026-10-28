from pathlib import Path
import json
import shutil

W=Path(__file__).parent
source=(W/'prepare_root_diagnostic_01.py').read_text(encoding='utf-8')
for before,after in {
    "\nD = W.parent / 'retry_root_diagnostic_01'":"\nD = W.parent / 'desktop_scan_01'",
    "\nOLD = W.parent / 'retry_template_01'":"\nOLD = W.parent / 'retry_reader_01'",
    "\"D=W.parent/'retry_root_diagnostic_01'\"":"\"D=W.parent/'desktop_scan_01'\"",
    'missing_approval_cli_root_diagnostic_01':'missing_approval_cli_desktop_scan_01',
    'missing_approval_sdk_root_diagnostic_01':'missing_approval_sdk_desktop_scan_01',
    'root_diagnostic_authorization_checks_01.json':'desktop_scan_authorization_checks_01.json',
    "W / 'root_diagnostic_authorization_checks.py'":"W / 'desktop_scan_authorization_checks.py'",
}.items():
    assert source.count(before)==1,before
    source=source.replace(before,after)
exec(compile(source,str(W/'prepare_root_diagnostic_01.py'),'exec'),{'__file__':__file__})
D=W.parent/'desktop_scan_01'
for source,name in (('task_monitor_template.py','task_monitor.py'),
    ('desktop_launcher_template.py','desktop_readonly.py'),
    ('desktop_readonly_qualification_test.dart','desktop_readonly_qualification_test.dart')):
    shutil.copyfile(W/source,D/name)
path=D/'qualification_session_v2.py'
text=path.read_text(encoding='utf-8')
assert text.count('import sys\n')==1
text=text.replace('import sys\n','import sys\nimport time\n')
needle='    try:\n        os.environ'
assert text.count(needle)==1
monitor='''    monitor = None
    monitor_log = None
    def start_monitor():
        nonlocal monitor,monitor_log
        monitor_log=(D/'task_monitor.log').open('x',encoding='utf-8')
        monitor=subprocess.Popen([PY,str(D/'task_monitor.py')],cwd=ROOT,
            stdout=monitor_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+10
        while not (D/'task_monitor_ready.json').exists():
            if monitor.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError('read-only TASK monitor readiness failed before download')
            time.sleep(.05)
        assert json.loads((D/'task_monitor_ready.json').read_bytes())==dict(ready=True,readOnly=True,serial='601FC87B')

    def finish_monitor():
        if monitor is None:
            return
        with (D/'task_monitor_stop.json').open('x') as stream:
            json.dump(dict(stop=True),stream)
        try:
            code=monitor.wait(timeout=15)
        except subprocess.TimeoutExpired:
            monitor.kill() # only this read-only Python helper, never Echo
            monitor.wait(timeout=10)
            code=1
        monitor_log.close()
        save('task_monitor_exit.json',dict(exitCode=code,readOnly=True))
        if code:
            raise RuntimeError('read-only TASK monitor failed; observations retained')

'''
text=text.replace(needle,monitor+needle)
needle="        run('deploy', SDK, 'deploy-canonical')"
assert text.count(needle)==1
text=text.replace(needle,"        start_monitor()\n"+needle)
needle="        run('idle_equivalence', PY, D / 'candidate_equivalence.py'"
assert text.count(needle)==1
text=text.replace(needle,"        run('desktop_readonly', PY, D / 'desktop_readonly.py')\n"+needle)
needle="    finally:\n        if (D / 'deploy_attempt.json').exists():"
assert text.count(needle)==1
text=text.replace(needle,"""    finally:
        try:
            finish_monitor()
        except Exception as error:
            if candidate_error is None:
                candidate_error=f'{type(error).__name__}: {error}'
            print(json.dumps(dict(monitorError=str(error))),flush=True)
        if (D / 'deploy_attempt.json').exists():""")
path.write_text(text,encoding='utf-8')
approval=D/'authorization.template.json'
value=json.loads(approval.read_bytes())
value['Scope']+=' Read-only TASK monitoring before download through candidate timing; read-only desktop factory/repository/UI qualification after the inherited fixture, including local write-refusal assertions with zero wire writes. No additional PLC write vectors.'
with approval.open('w',encoding='utf-8') as stream:
    json.dump(value,stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(prepared=True,authorized=False,controllerChanges=0,
    nativeTaskMonitor=True,desktopReadOnly=True,plcImageUnchanged=True)))

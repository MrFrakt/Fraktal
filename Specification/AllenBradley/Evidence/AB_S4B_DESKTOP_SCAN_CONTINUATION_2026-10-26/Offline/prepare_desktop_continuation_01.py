from pathlib import Path
import shutil

W=Path(__file__).parent
original=W/'prepare_root_diagnostic_01.py'
source=original.read_text(encoding='utf-8')
for before,after in {
    "\nD = W.parent / 'retry_root_diagnostic_01'":"\nD = W.parent / 'desktop_scan_continue_01'",
    "\nOLD = W.parent / 'retry_template_01'":"\nOLD = W.parent / 'desktop_scan_01'",
    "\"D=W.parent/'retry_root_diagnostic_01'\"":"\"D=W.parent/'desktop_scan_continue_01'\"",
    'missing_approval_cli_root_diagnostic_01':'missing_approval_cli_desktop_continue_01',
    'missing_approval_sdk_root_diagnostic_01':'missing_approval_sdk_desktop_continue_01',
    'root_diagnostic_authorization_checks_01.json':'desktop_continue_authorization_checks_01.json',
    "W / 'root_diagnostic_authorization_checks.py'":"W / 'desktop_continue_authorization_checks.py'",
}.items():
    assert source.count(before)==1,before
    source=source.replace(before,after)
exec(compile(source,str(original),'exec'),{'__file__':__file__})
D=W.parent/'desktop_scan_continue_01'
OLD=W.parent/'desktop_scan_01'
for name in ('task_monitor.py','desktop_readonly.py','desktop_readonly_qualification_test.dart'):
    shutil.copyfile(OLD/name,D/name)
shutil.copyfile(W/'session_ready_template.py',D/'session_ready.py')
for name in ('qualification_session_v2.py','candidate_regressions_v2.py'):
    path=D/name
    text=path.read_text(encoding='utf-8')
    if name=='qualification_session_v2.py':
        before='import time\n'
        after='import time\nfrom session_ready import wait_for_ready\n'
        start=text.index('        deadline=time.monotonic()+10')
        end=text.index('\n\n    def finish_monitor',start)
        text=text[:start]+"        wait_for_ready(D/'task_monitor_ready.json',dict(ready=True,readOnly=True,serial='601FC87B'),monitor,timeout=10)"+text[end:]
    else:
        before='from qualification_session_v2 import authorize\n'
        after=before+'from session_ready import wait_for_ready\n'
        start=text.index('            deadline=time.monotonic()+90')
        end=text.index('\n            result=genealogy.main',start)
        text=text[:start]+"            wait_for_ready(ready,dict(ready=True,readOnly=True,sample=0),process,timeout=90)"+text[end:]
    assert text.count(before)==1,before
    path.write_text(text.replace(before,after),encoding='utf-8')
print('Prepared same-scope continuation with bounded complete-message readiness; not started.')

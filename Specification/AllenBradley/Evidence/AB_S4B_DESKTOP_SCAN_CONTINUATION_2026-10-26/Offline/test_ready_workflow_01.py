from pathlib import Path
import sys

W=Path(__file__).parent
folder=sys.argv.pop(1)
assert folder in ('desktop_scan_01','desktop_scan_continue_01')
source=(W/'test_desktop_scan_workflow_01.py').read_text(encoding='utf-8')
def replace(before,after):
    global source
    assert source.count(before)==1,before
    source=source.replace(before,after)
replace("SOURCE=W.parent/'desktop_scan_01'",f"SOURCE=W.parent/{folder!r}")
replace('import time\n','import time\nimport threading\n')
replace('ready_failure=False):','ready_failure=False,partial_ready=False):')
replace('        spec.loader.exec_module(module)','        sys.path.insert(0,str(SOURCE))\n        spec.loader.exec_module(module)')
replace("""            if not ready_failure:
                (output/'task_monitor_ready.json').write_text(json.dumps(dict(ready=True,readOnly=True,serial='601FC87B')),encoding='utf-8')""","""            if not ready_failure:
                target=output/'task_monitor_ready.json'
                payload=json.dumps(dict(ready=True,readOnly=True,serial='601FC87B'))
                if partial_ready:
                    target.write_text('',encoding='utf-8')
                    threading.Timer(.02,lambda:target.write_text(payload,encoding='utf-8')).start()
                else:
                    target.write_text(payload,encoding='utf-8')""")
replace('class TaskReadTests(unittest.TestCase):',"""    def test_partial_ready_file_waits_for_complete_validated_message(self):
        self.exercise(partial_ready=True)

class TaskReadTests(unittest.TestCase):""")
exec(compile(source,str(W/'test_desktop_scan_workflow_01.py'),'exec'),globals())

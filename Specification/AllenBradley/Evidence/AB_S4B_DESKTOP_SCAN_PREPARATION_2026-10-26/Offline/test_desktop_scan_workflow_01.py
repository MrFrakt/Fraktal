"""Failure-injected orchestration checks; all subprocess/PLC access is mocked."""
from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import sys
import time

W=Path(__file__).parent
SOURCE=W.parent/'desktop_scan_01'

class WorkflowTests(unittest.TestCase):
    def exercise(self, *, desktop_failure=False, monitor_failure=False, ready_failure=False):
        output=W/('workflow_'+uuid.uuid4().hex)
        output.mkdir()
        spec=importlib.util.spec_from_file_location('desktop_scan_workflow',SOURCE/'qualification_session_v2.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.D=output
        approval=json.loads((SOURCE/'authorization.template.json').read_bytes())
        approval.update(CurrentOwnerApproved=True,OwnerInstruction='Offline workflow test only; no controller access')
        for flag in module.FLAGS:
            approval[flag]=True
        (output/'authorization.json').write_text(json.dumps(approval),encoding='utf-8')
        (output/'canonical.sha256').write_text(module.PIN,encoding='utf-8')
        (output/'source_bindings.json').write_text(json.dumps(dict(gatesPassed=True,sha256={})),encoding='utf-8')
        labels=[]
        events=[]
        def digest(path):
            return module.SOURCE if Path(path).suffix.lower()=='.l5x' else module.PIN
        def run(command,**kwargs):
            self.assertEqual(Path(command[1]).name,'run_logged.py')
            label=command[2]
            labels.append(label)
            events.append(label)
            if label=='deploy':
                (output/'deploy_attempt.json').write_text('{}',encoding='utf-8')
            if label=='desktop_readonly' and desktop_failure:
                raise module.subprocess.CalledProcessError(1,command)
            return SimpleNamespace(returncode=0)
        def popen(command,**kwargs):
            self.assertEqual(Path(command[1]).name,'task_monitor.py')
            self.assertEqual(labels[-1],'backup_access')
            events.append('monitor-start')
            if not ready_failure:
                (output/'task_monitor_ready.json').write_text(json.dumps(dict(ready=True,readOnly=True,serial='601FC87B')),encoding='utf-8')
            def wait(timeout):
                self.assertTrue((output/'task_monitor_stop.json').exists())
                events.append('monitor-stop')
                return 1 if monitor_failure else 0
            return SimpleNamespace(poll=lambda:1 if ready_failure else None,wait=wait,
                kill=lambda:self.fail('unexpected kill in non-timeout test'))
        with patch.object(module,'digest',side_effect=digest),patch.object(module,'dumps',return_value=[]), \
             patch.object(module.subprocess,'run',side_effect=run),patch.object(module.subprocess,'Popen',side_effect=popen), \
             patch.dict(module.os.environ):
            code=module.main()
        result=json.loads((output/'session_result.json').read_bytes())
        self.assertTrue(result['authorizationConsumed'])
        self.assertEqual(result['faultClears'],0)
        self.assertEqual(result['powerOperations'],0)
        if ready_failure:
            self.assertNotIn('deploy',labels)
            self.assertNotIn('restore_genealogy',labels)
            self.assertEqual(code,1)
            self.assertFalse(result['passed'])
        else:
            self.assertLess(events.index('monitor-start'),events.index('deploy'))
            self.assertLess(events.index('monitor-stop'),events.index('guard_rollback'))
            self.assertIn('restore_genealogy',labels)
            self.assertIn('baseline_regressions',labels)
            self.assertEqual(labels[-1],'baseline_timing')
            self.assertTrue(result['genealogyRestored'])
            self.assertIsNone(result['rollbackError'])
            self.assertEqual(code,1 if desktop_failure or monitor_failure else 0)
            self.assertEqual(result['passed'],not(desktop_failure or monitor_failure))
        return output

    def test_normal_scope_stops_monitor_before_verified_rollback(self):
        self.exercise()
    def test_desktop_failure_still_stops_monitor_and_restores_genealogy(self):
        self.exercise(desktop_failure=True)
    def test_monitor_failure_cannot_skip_genealogy_cleanup(self):
        self.exercise(monitor_failure=True)
    def test_monitor_readiness_failure_stops_before_download(self):
        self.exercise(ready_failure=True)

class TaskReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(SOURCE))
        spec=importlib.util.spec_from_file_location('task_monitor_check',SOURCE/'task_monitor.py')
        cls.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
    def test_valid_dint_scalars_are_preserved(self):
        values=[100,960,10033,1]
        responses=[SimpleNamespace(TagName=tag,Status='Success',Value=value)
            for tag,value in zip(self.module.TAGS,values)]
        result=self.module.acquire(SimpleNamespace(Read=lambda tags:responses),time.monotonic())
        self.assertTrue(result['available'])
        self.assertEqual(list(result['values'].values()),values)
    def test_download_socket_error_is_retained_without_ending_monitor(self):
        def read(tags):
            raise OSError('connection reset during download')
        result=self.module.acquire(SimpleNamespace(Read=read),time.monotonic())
        self.assertFalse(result['available'])
        self.assertIn('OSError',result['error'])
        self.assertNotIn('values',result)
    def test_partial_or_wrong_type_reads_cannot_become_native_samples(self):
        for responses in (None,[],[SimpleNamespace(TagName=tag,Status='Success',Value=True) for tag in self.module.TAGS]):
            result=self.module.acquire(SimpleNamespace(Read=lambda tags:responses),time.monotonic())
            self.assertFalse(result['available'])
            self.assertNotIn('values',result)

if __name__=='__main__':
    unittest.main()

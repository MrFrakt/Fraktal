from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace
import threading
import unittest
import uuid

W=Path(__file__).parent
spec=importlib.util.spec_from_file_location('ready_protocol',W/'session_ready_template.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReadyTests(unittest.TestCase):
    def setUp(self):
        self.folder=W/('ready_test_'+uuid.uuid4().hex)
        self.folder.mkdir()
        self.path=self.folder/'ready.json'
        self.expected=dict(ready=True,readOnly=True,serial='601FC87B')
        self.process=SimpleNamespace(poll=lambda:None)
    def test_complete_message_is_accepted(self):
        self.path.write_text(json.dumps(self.expected),encoding='utf-8')
        self.assertEqual(module.wait_for_ready(self.path,self.expected,self.process,timeout=.1),self.expected)
    def test_empty_then_complete_file_is_accepted_within_original_deadline(self):
        self.path.write_text('',encoding='utf-8')
        timer=threading.Timer(.02,lambda:self.path.write_text(json.dumps(self.expected),encoding='utf-8'))
        timer.start()
        try:
            self.assertEqual(module.wait_for_ready(self.path,self.expected,self.process,timeout=.2),self.expected)
        finally:
            timer.join()
    def test_permanently_partial_message_times_out(self):
        self.path.write_text('{"ready":',encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError,'deadline'):
            module.wait_for_ready(self.path,self.expected,self.process,timeout=.02)
    def test_complete_wrong_target_is_refused(self):
        self.path.write_text(json.dumps(dict(self.expected,serial='OTHER')),encoding='utf-8')
        with self.assertRaises(ValueError):
            module.wait_for_ready(self.path,self.expected,self.process,timeout=.1)
    def test_boolean_integer_coercion_is_refused(self):
        self.path.write_text(json.dumps(dict(self.expected,readOnly=1)),encoding='utf-8')
        with self.assertRaises(ValueError):
            module.wait_for_ready(self.path,self.expected,self.process,timeout=.1)
    def test_exited_helper_cannot_authorize_work_from_an_old_marker(self):
        self.path.write_text(json.dumps(self.expected),encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError,'exited'):
            module.wait_for_ready(self.path,self.expected,SimpleNamespace(poll=lambda:1),timeout=.1)

if __name__=='__main__':
    unittest.main()

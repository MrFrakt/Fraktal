import json,unittest
from unittest.mock import Mock,patch
from session_ready import wait_for_ready
class Readiness(unittest.TestCase):
    def test_windows_lock_and_partial_json_retry_then_validate(self):
        path=Mock();path.read_bytes.side_effect=[PermissionError('writer owns file'),b'{',b'{"ready":true}']
        process=Mock();process.poll.return_value=None
        self.assertEqual(wait_for_ready(path,dict(ready=True),process,timeout=1),dict(ready=True))
        self.assertEqual(path.read_bytes.call_count,3)
    def test_persistent_lock_keeps_same_deadline(self):
        path=Mock();path.read_bytes.side_effect=PermissionError('writer owns file')
        process=Mock();process.poll.return_value=None
        with self.assertRaisesRegex(RuntimeError,'deadline'):wait_for_ready(path,dict(ready=True),process,timeout=.02)
    def test_wrong_message_or_exited_helper_never_passes(self):
        path=Mock();path.read_bytes.return_value=b'{"ready":false}'
        process=Mock();process.poll.return_value=None
        with self.assertRaises(ValueError):wait_for_ready(path,dict(ready=True),process,timeout=1)
        process.poll.return_value=0
        with self.assertRaisesRegex(RuntimeError,'exited'):wait_for_ready(path,dict(ready=True),process,timeout=1)
if __name__=='__main__':unittest.main()

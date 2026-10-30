"""Simulate failures through the actual orchestration; no processes or PLC calls."""
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
import qualification_session_v2 as owner
class Process:
    def wait(self,**kwargs):return 0
class Workflow(unittest.TestCase):
    def test_candidate_failures_always_restore(self):
        readonly=['configuration_comparison','idle_equivalence','generic_acquire','desktop_profile','candidate_timing']
        for failure in ['deploy','candidate_regressions']+readonly+[None]:
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary);calls=[]
                value=json.loads((owner.D/'authorization.template.json').read_bytes())
                value.update(CurrentOwnerApproved=True,OwnerInstruction='Simulation only')
                value.update({key:True for key in owner.FLAGS})
                (directory/'authorization.json').write_text(json.dumps(value))
                (directory/'canonical.sha256').write_text(owner.PIN)
                (directory/'source_bindings.json').write_text(json.dumps(dict(gatesPassed=True,sha256={})))
                def fake_run(args,**kwargs):
                    label=args[2];calls.append(label)
                    if label=='deploy':
                        (directory/'deploy_attempt.json').write_text('{}')
                        (directory/'candidate_run_requested.json').write_text('{}')
                    if label==failure:raise RuntimeError('injected '+label)
                def fake_digest(path):return owner.SOURCE if str(path).endswith('.L5X') else owner.PIN
                with patch.object(owner,'D',directory),patch.object(owner,'digest',fake_digest),\
                     patch.object(owner,'dumps',lambda:[]),patch.object(owner,'wait_for_ready',lambda *a,**k:None),\
                     patch.object(owner.subprocess,'run',fake_run),patch.object(owner.subprocess,'Popen',lambda *a,**k:Process()),\
                     patch.dict(owner.os.environ,{},clear=False):
                    code=owner.main()
                result=json.loads((directory/'session_result.json').read_bytes())
                self.assertTrue(result['genealogyRestored']);self.assertIsNone(result['rollbackError'])
                self.assertEqual(code,0 if failure is None else 1)
                for label in ['restore_genealogy','restore_original_medium','baseline_regressions','final_checks','preflight_final']:
                    self.assertIn(label,calls)
                if failure in readonly or failure is None:
                    self.assertEqual([c for c in calls if c in readonly],readonly)
                else:self.assertFalse(any(c in calls for c in readonly))
                self.assertLess(calls.index('restore_genealogy'),calls.index('baseline_regressions'))
if __name__=='__main__':unittest.main(verbosity=2)

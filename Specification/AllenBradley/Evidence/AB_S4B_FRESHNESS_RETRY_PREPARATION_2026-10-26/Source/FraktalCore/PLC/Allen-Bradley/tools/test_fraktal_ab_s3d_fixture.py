"""Reset observations wrap the existing command; cleanup remains available."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_s3d_fixture_execute as fixture


class AlarmFixtureTests(unittest.TestCase):
    def runner(self):
        events=[]
        class Parent:
            def command(self,kind,**args):events.append(('command',kind));return {'accepted':True}
            def check(self,ok,message):
                if not ok:raise RuntimeError(message)
        with patch.object(fixture.previous,'paired_run',return_value=Parent):
            run=object.__new__(fixture.paired_run(Path('unused.json')))
        run.app=SimpleNamespace(name='Mixer');run.comm=object();run.evidence={}
        run.alarm_pair=lambda phase:events.append(('read',phase))
        return run,events

    def test_before_after_observation_adds_no_reset_command(self):
        run,events=self.runner()
        with patch.object(fixture.execute,'read_scalar',return_value=1):
            answer=run.command(fixture.mailbox.OPERATOR_RESET)
        self.assertEqual(events,[('read','before'),('command',fixture.mailbox.OPERATOR_RESET),('read','after')])
        self.assertTrue(answer['accepted'])

    def test_failed_observation_cannot_block_parent_cleanup(self):
        run,events=self.runner();run.evidence['error']='an earlier capture failed'
        with patch.object(fixture.execute,'read_scalar',side_effect=AssertionError('cleanup must skip observation')):
            run.command(fixture.mailbox.OPERATOR_RESET)
        self.assertEqual(events,[('command',fixture.mailbox.OPERATOR_RESET)])


if __name__=='__main__':unittest.main()

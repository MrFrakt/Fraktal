"""Read-only observation failure cannot issue an extra fixture write."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_s3c_fixture_execute as fixture


class SequenceFixtureTests(unittest.TestCase):
    def runner(self,path):
        run=object.__new__(fixture.paired_run(path))
        run.app=SimpleNamespace(name='Press');run.comm=object();run.evidence={}
        return run

    def test_sequence_observation_follows_the_original_record(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'run.json');events=[]
            values={'Press/SequenceStepCount':1,'Press/SequenceSteps[1]/Visited':True}
            with patch.object(fixture.genealogy.GenealogyRun,'record',side_effect=lambda *a,**k:events.append('record') or {'row':1}), \
                 patch.object(fixture.previous,'capture_gate',side_effect=lambda *a:events.append('read') or dict(passed=True,pair=dict(canonical=dict(values=values)))):
                result=run.record('ST','OK',0,0)
            self.assertEqual(events,['record','read']);self.assertEqual(result,{'row':1})
            self.assertEqual(run.evidence['s3cSequencePairs'][0]['case'],'OK')

    def test_mode_clear_is_required_and_failed_pair_is_retained(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'run.json')
            with patch.object(fixture.genealogy.GenealogyRun,'record',return_value={}), \
                 patch.object(fixture.previous,'capture_gate',return_value=dict(passed=True,pair=dict(canonical=dict(values={'Press/SequenceStepCount':1})))):
                with self.assertRaisesRegex(RuntimeError,'clear the chart'):run.record('LD','mode_change',0,0)
            self.assertEqual(len(list(Path(directory).glob('*.json.gz'))),1)


if __name__=='__main__':unittest.main()

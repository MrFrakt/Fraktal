"""S3b observations add reads; inherited writes and cleanup stay authoritative."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_s3b_fixture_execute as fixture


class ConditionFixtureTests(unittest.TestCase):
    def runner(self,path):
        cls=fixture.paired_run(path)
        run=object.__new__(cls)
        run.app=SimpleNamespace(name='Press')
        run.comm=SimpleNamespace(Read=lambda tag:SimpleNamespace(Status='Success',Value=1))
        run.evidence={}
        return run

    def test_condition_pair_precedes_the_original_release_write(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'fixture.json');events=[]
            report=dict(passed=True,pair=dict(canonical=dict(values={
                'Press/PressRam/Status/Diagnostic/ReasonCode':1,
                'Press/PressRam/Status/Diagnostic/Since':'1998-01-01T00:00:00.000Z'})))
            with patch.object(fixture.execute,'read_module',return_value=dict(OutImm_Reason=1,OutImm_Held=1)), \
                 patch.object(fixture.equivalence,'run',side_effect=lambda comm:events.append('pair') or report), \
                 patch.object(fixture.genealogy.GenealogyRun,'set',side_effect=lambda *args:events.append('write')):
                run.set(fixture.execute.HOLD['PressRam'],0)
            self.assertEqual(events,['pair','write'])
            self.assertEqual(run.evidence['s3bConditionPairs'][0]['languageOrdinal'],1)

    def test_failed_observation_blocks_release_but_not_parent_cleanup(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'fixture.json')
            with patch.object(fixture.execute,'read_module',return_value=dict(OutImm_Reason=1,OutImm_Held=1)), \
                 patch.object(fixture.equivalence,'run',side_effect=ValueError('unstable scan')) as capture, \
                 patch.object(fixture.genealogy.GenealogyRun,'set') as write:
                with self.assertRaisesRegex(RuntimeError,'equivalence failed'):
                    run.set(fixture.execute.HOLD['PressRam'],0)
                write.assert_not_called()
                run.evidence['error']='parent recorded the failed observation'
                run.set(fixture.execute.HOLD['PressRam'],0)
                write.assert_called_once()
                capture.assert_called_once()
            self.assertEqual(len(list(Path(directory).glob('*.json.gz'))),1)

    def test_unobserved_inputs_use_only_the_original_write(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'fixture.json')
            with patch.object(fixture.equivalence,'run') as capture, \
                 patch.object(fixture.genealogy.GenealogyRun,'set') as write:
                run.set('an_existing_fixture_input',1)
                write.assert_called_once_with('an_existing_fixture_input',1)
                capture.assert_not_called()


if __name__=='__main__':unittest.main()

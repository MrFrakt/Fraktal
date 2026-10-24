"""S3a observations must preserve the original fixture's command surface."""
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_s3a_fixture_execute as fixture


class PairedFixtureTests(unittest.TestCase):
    def runner(self, path):
        cls=fixture.paired_run(path)
        run=object.__new__(cls)
        run.app=SimpleNamespace(name='Rotor');run.comm=object();run.evidence={}
        return run

    def test_observation_precedes_exactly_the_original_decision_answer(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'acceptance.json');calls=[]
            report=dict(passed=True,pair=dict(canonical=dict(values={'Rotor/Decision/Prompt':'std.prompt'})))
            with patch.object(fixture.equivalence,'run',side_effect=lambda comm:(calls.append('read') or report)), \
                 patch.object(fixture.genealogy.GenealogyRun,'command',side_effect=lambda *a,**k:(calls.append('command') or 'ok')):
                self.assertEqual(run.command(fixture.mailbox.DECISION_ANSWER,IntValue=1),'ok')
            self.assertEqual(calls,['read','command'])
            pair=Path(run.evidence['s3aDecisionPairs'][0]['output'])
            self.assertEqual(json.loads(gzip.open(pair,'rt').read()),report)

    def test_failed_pair_is_retained_and_cannot_issue_the_original_answer(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'acceptance.json')
            with patch.object(fixture.equivalence,'run',side_effect=ValueError('unstable scan')), \
                 patch.object(fixture.genealogy.GenealogyRun,'command') as command:
                with self.assertRaisesRegex(RuntimeError,'equivalence failed'):
                    run.command(fixture.mailbox.DECISION_ANSWER,IntValue=1)
                command.assert_not_called()
            pair=Path(run.evidence['s3aDecisionPairs'][0]['output'])
            self.assertEqual(json.loads(gzip.open(pair,'rt').read())['error'],'unstable scan')

    def test_other_commands_are_unchanged_and_do_not_create_pair_files(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'acceptance.json')
            with patch.object(fixture.equivalence,'run') as acquire, \
                 patch.object(fixture.genealogy.GenealogyRun,'command',return_value='original') as command:
                self.assertEqual(run.command(fixture.mailbox.STOP),'original')
                command.assert_called_once_with(fixture.mailbox.STOP)
                acquire.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()),[])


if __name__=='__main__':unittest.main()

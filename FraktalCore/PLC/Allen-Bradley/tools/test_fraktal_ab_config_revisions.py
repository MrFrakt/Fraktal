"""The pre-collapse configuration revisions (O12): recorded for every declaration
in this tree, and still what the generator computes until increment C0b."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import fraktal_ab_config_revisions as revisions

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / 'fixtures' / 'config_revisions' / 'pre_collapse.json'


class PreCollapseRevisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_every_declaration_in_the_tree_is_recorded(self):
        self.assertEqual(self.fixture['schema'], revisions.SCHEMA)
        self.assertEqual([r['declaration'] for r in self.fixture['declarations']], revisions.declarations())

    def test_each_record_is_its_own_revision_and_what_its_build_accepts(self):
        for row in self.fixture['declarations']:
            with self.subTest(row['declaration']):
                self.assertEqual(row['configRevision'], int(row['legacyContentHash'][:6], 16))
                self.assertIn(row['configRevision'], row['acceptedRevisions'])
                self.assertEqual(row['acceptedRevisions'], sorted(set(row['acceptedRevisions'])))

    def test_the_generator_still_computes_the_recorded_revisions(self):
        env = {k: v for k, v in os.environ.items() if k != 'FRAKTAL_AB_DECLARATION'}
        for row in self.fixture['declarations']:
            with self.subTest(row['declaration']):
                done = subprocess.run([sys.executable, str(HERE / 'fraktal_ab_config_revisions.py'),
                                       '--declaration', row['declaration']],
                                      capture_output=True, text=True, cwd=HERE, env=env)
                self.assertEqual(done.returncode, 0, done.stderr[-2000:])
                self.assertEqual(json.loads(done.stdout), row)


if __name__ == '__main__':
    unittest.main()

"""Driver unit tests: pure logic plus capture compatibility with the sealed reader.

No Studio session is started here; live qualification is recorded as dated
evidence under Specification/AllenBradley/Evidence/.
"""
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import fraktal_ab_studio_driver as driver  # noqa: E402
import fraktal_ab_studio_capacity as capacity  # noqa: E402

FIXTURE = HERE / 'fixtures/canonical/studio_capacity_reference_01.json.gz'


class SummaryParsingTests(unittest.TestCase):
    def test_complete_summary_is_parsed_with_last_match_winning(self):
        text = ('Verifying...\n'
                'Complete - 1 error(s), 2 warning(s)\n'
                'Complete - 0 error(s), 0 warning(s)')
        self.assertEqual(driver.parse_summary(text), (0, 0))
        self.assertEqual(
            driver.parse_summary('Complete - 3 error(s), 1 warning(s)'), (3, 1))

    def test_incomplete_or_missing_summary_is_refused(self):
        self.assertIsNone(driver.parse_summary('Verifying...'))
        self.assertIsNone(driver.parse_summary(''))
        self.assertIsNone(driver.parse_summary(None))
        self.assertIsNone(driver.parse_summary('Complete - 0 error(s)'))

    def test_count_button_texts_parse(self):
        self.assertEqual(driver.parse_count_button('0 Errors'), (0, 'errors'))
        self.assertEqual(driver.parse_count_button('12 Warnings'), (12, 'warnings'))
        self.assertEqual(driver.parse_count_button('3 Messages'), (3, 'messages'))
        self.assertIsNone(driver.parse_count_button('Offline'))
        self.assertIsNone(driver.parse_count_button(''))
        self.assertIsNone(driver.parse_count_button(None))


class CommandPolicyTests(unittest.TestCase):
    def test_online_commands_are_refused_by_name(self):
        for command in (32081, 32082, 32085, 32086, 32087, 32088, 32089, 32093):
            with self.subTest(command=command):
                with self.assertRaisesRegex(driver.StudioDriverError, 'online command'):
                    driver.postable_command(command)

    def test_only_the_two_offline_commands_are_postable(self):
        self.assertEqual(driver.postable_command(32049), 'Logic > Verify Controller')
        self.assertEqual(driver.postable_command(32023), 'Edit > Controller Properties')

    def test_any_other_command_is_refused(self):
        for command in (0, 1, 32050, 32006, 32004, 57665, 32131):
            with self.subTest(command=command):
                with self.assertRaisesRegex(driver.StudioDriverError, 'allow-list'):
                    driver.postable_command(command)


class SavePromptTests(unittest.TestCase):
    def test_save_prompts_are_recognised_across_capitalisation(self):
        self.assertTrue(driver.is_save_prompt(['Save changes to project before closing?']))
        self.assertTrue(driver.is_save_prompt([None, 'do you want to SAVE CHANGES?']))

    def test_other_dialogs_are_not_answered_as_save_prompts(self):
        self.assertFalse(driver.is_save_prompt(['Importing...', 'Cancel']))
        self.assertFalse(driver.is_save_prompt([]))
        self.assertFalse(driver.is_save_prompt([None]))


class SourceGuardTests(unittest.TestCase):
    def test_repository_inputs_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            inside = repo / 'sub' / 'project.ACD'
            inside.parent.mkdir()
            inside.write_bytes(b'x')
            with self.assertRaisesRegex(driver.StudioDriverError, 'inside the repository'):
                driver.assert_safe_source(inside, repo_root=repo)

    def test_outside_inputs_with_wrong_suffix_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'project.zip'
            bad.write_bytes(b'x')
            with self.assertRaisesRegex(driver.StudioDriverError, 'existing'):
                driver.assert_safe_source(bad, repo_root=Path(tmp) / 'elsewhere')
            with self.assertRaisesRegex(driver.StudioDriverError, 'existing'):
                driver.assert_safe_source(Path(tmp) / 'missing.ACD',
                                          repo_root=Path(tmp) / 'elsewhere')

    def test_outside_adcs_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / 'project.ACD'
            good.write_bytes(b'x')
            resolved = driver.assert_safe_source(good, repo_root=Path(tmp) / 'repo')
            self.assertEqual(resolved, good.resolve())


class CaptureCompatibilityTests(unittest.TestCase):
    """The driver's capture shape must stay acceptable to the sealed reader."""

    @classmethod
    def setUpClass(cls):
        cls.sealed = json.loads(gzip.decompress(FIXTURE.read_bytes()).decode('utf-8-sig'))
        cls.pin = cls.sealed['SourceSha256']

    def build_from_sealed_rows(self):
        meta = {key: self.sealed[key] for key in self.sealed if key not in ('Snapshots', 'Error')}
        return driver.build_capture(meta, self.sealed['Snapshots'], None)

    def test_sealed_rows_through_the_driver_builder_pass_the_sealed_reader(self):
        report = capacity.normalize(self.build_from_sealed_rows(), self.pin)
        self.assertTrue(report['Measured'] and report['VerifiedFit'])
        owner = json.loads((HERE.parents[3] / 'Specification/AllenBradley/Evidence/'
                            'AB_S3A_CANONICAL_RUNTIME_2026-10-21/Runtime/'
                            'capacity_review.json').read_text())
        for key in ('UsedStandardBlocks', 'AvailableBlocks', 'TotalBlocks',
                    'DisplayedUsagePercent'):
            self.assertEqual(report[key], owner[key])

    def test_capture_schema_is_unchanged(self):
        capture = self.build_from_sealed_rows()
        self.assertEqual(capture['Schema'], 'fraktal.ab.studio-capacity-capture')
        self.assertEqual(capture['SchemaVersion'], 1)
        self.assertEqual(sorted(capture), sorted(self.sealed))

    def test_driver_error_is_carried_like_the_qualified_collector(self):
        capture = self.build_from_sealed_rows()
        capture['Error'] = 'something failed'
        with self.assertRaisesRegex(ValueError, 'did not complete'):
            capacity.normalize(capture, self.pin)


class RevisionGuardTests(unittest.TestCase):
    def test_unqualified_revisions_are_refused_before_anything_is_posted(self):
        for revision in (33, 34, 36, 39, 40):
            with self.subTest(revision=revision):
                with self.assertRaisesRegex(driver.StudioDriverError, 'not qualified'):
                    driver.assert_revision_qualified(revision, 'verify')
                with self.assertRaisesRegex(driver.StudioDriverError, 'not qualified'):
                    driver.assert_revision_qualified(revision, 'capacity')

    def test_import_is_restricted_to_the_revision_its_dialog_was_read_from(self):
        driver.assert_revision_qualified(38, 'import')
        with self.assertRaisesRegex(driver.StudioDriverError, 'not qualified'):
            driver.assert_revision_qualified(37, 'import')


class CapacityCollectorCommandTests(unittest.TestCase):
    def test_driver_collector_invokes_the_hidden_driver(self):
        command = capacity.collector_command(
            'driver', Path('C:/work/x.ACD'), 'AB' * 32, Path('C:/out/cap.json'))
        self.assertEqual(command[1:4], [str(capacity.Path(capacity.__file__).with_name(
            'fraktal_ab_studio_driver.py')), 'capacity', '--acd'])
        self.assertIn('--revision', command)
        self.assertEqual(command[command.index('--revision') + 1], '38')

    def test_revision_is_derived_from_a_custom_studio_path(self):
        revision = capacity.studio_revision(
            Path('C:/Program Files (x86)/Rockwell Software/Studio 5000/'
                 'Logix Designer/ENU/v37/Bin/LogixDesigner.Exe'))
        self.assertEqual(revision, 37)
        self.assertEqual(capacity.studio_revision(None), 38)

    def test_powershell_collector_command_is_unchanged(self):
        command = capacity.collector_command(
            'powershell', Path('C:/work/x.ACD'), 'AB' * 32, Path('C:/out/cap.json'),
            Path('C:/some/v38/Bin/LogixDesigner.Exe'))
        self.assertEqual(command[:3], ['powershell', '-NoProfile', '-File'])
        self.assertTrue(command[3].endswith('Invoke-AbStudioCapacity.ps1'))
        self.assertEqual(command[-2:], ['-StudioPath', 'C:\\some\\v38\\Bin\\LogixDesigner.Exe'])

    def test_unknown_collectors_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'unknown collector'):
            capacity.collector_command('sendkeys', Path('x.ACD'), 'AB' * 32, Path('y.json'))


@unittest.skipUnless(sys.platform == 'win32', 'menu resource walk needs Windows')
class MenuResourceTests(unittest.TestCase):
    RESOURCE = (driver.STUDIO_ROOT / 'v38' / 'Bin' / 'LogixACENU.dll')

    @unittest.skipUnless(RESOURCE.is_file(), 'LogixACENU.dll v38 not installed')
    def test_controller_properties_command_matches_the_qualified_id(self):
        self.assertEqual(driver.properties_command(self.RESOURCE, 38), 32023)

    def test_unqualified_revisions_are_refused_even_when_the_resource_resolves(self):
        if not self.RESOURCE.is_file():
            self.skipTest('LogixACENU.dll v38 not installed')
        original = dict(driver.KNOWN_PROPERTIES_COMMANDS)
        try:
            driver.KNOWN_PROPERTIES_COMMANDS.clear()
            with self.assertRaisesRegex(driver.StudioDriverError, 'not qualified'):
                driver.properties_command(self.RESOURCE, 38)
        finally:
            driver.KNOWN_PROPERTIES_COMMANDS.update(original)


if __name__ == '__main__':
    unittest.main()

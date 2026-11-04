"""S6 classification is a fail-closed engineering inventory, never a deleter."""
from pathlib import Path
import tempfile
import unittest

import fraktal_ab_legacy_consumers as census


class Classification(unittest.TestCase):
    def test_first_match_keeps_oracle_execute_and_its_test_out_of_harness_class(self):
        for name in ('fraktal_ab_s3f_fixture_execute', 'fraktal_ab_press_s3k_equivalence'):
            self.assertEqual(census.classify(name, 'tool', affected=True), 'MO')
            self.assertEqual(census.classify('test_' + name, 'test', affected=True), 'MO')
        self.assertEqual(census.classify('fraktal_ab_phase6_execute', 'tool', affected=True), 'HX')
        self.assertEqual(census.classify('test_fraktal_ab_phase6_execute', 'test', affected=True), 'UT')

    def test_generator_and_adapter_tests_are_structure_tests(self):
        for owners, role in ((census.GENERATORS, 'GN'), (census.ADAPTERS, 'AD')):
            for name in owners:
                self.assertEqual(census.classify(name, 'tool', affected=True), role)
                self.assertEqual(census.classify('test_' + name, 'test', affected=True), 'UT')
        self.assertEqual(census.classify('fraktal_ab_projection', 'tool', affected=True), 'RT')

    def test_unknown_affected_sources_and_inconsistent_kinds_are_refused(self):
        for name, kind in (('foreign_helper', 'tool'), ('test_other', 'test'),
                           ('fraktal_ab_helper', 'unknown'), ('test_fraktal_ab_helper', 'tool')):
            with self.subTest(name=name), self.assertRaises(ValueError):
                census.classify(name, kind, affected=True)
        self.assertIsNone(census.classify('fraktal_ab_unrelated', 'tool', affected=False))


class Inventory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = self.root / 'FraktalCore/PLC/Allen-Bradley/tools'
        self.tools.mkdir(parents=True)
        for name in census.EXTERNAL_RUNTIME:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n', encoding='utf-8')

    def source(self, name, text):
        (self.tools / (name + '.py')).write_text(text, encoding='utf-8')

    def test_alias_reads_and_dependents_are_counted_without_executing_sources(self):
        self.source('fraktal_ab_generate', 'raise RuntimeError("must never import")\n')
        self.source('fraktal_ab_reader', 'from fraktal_ab_generate import unit_context_members as fields\n')
        self.source('fraktal_ab_helper', 'import fraktal_ab_reader as reader\n')
        self.source('test_fraktal_ab_helper', 'import fraktal_ab_helper\n')
        self.source('fraktal_ab_other', 'VALUE = 1\n')
        result = census.inventory(self.root)
        self.assertEqual(result['summary']['directLegacyReferences'], 1)
        self.assertEqual(result['summary']['legacyImportDependents'], 3)
        rows = {r['module']: r for r in result['consumers']}
        self.assertEqual(rows['fraktal_ab_generate']['classification'], 'GN')
        self.assertEqual(rows['fraktal_ab_helper']['classification'], 'HL')
        self.assertEqual(rows['test_fraktal_ab_helper']['classification'], 'UT')
        self.assertEqual(rows['fraktal_ab_reader']['importedBy'], ['fraktal_ab_helper'])
        self.assertEqual([r['module'] for r in result['unaffected']], ['fraktal_ab_other'])
        self.assertFalse(result['controllerAccess'])
        self.assertFalse(result['retirementAcceptance'])

    def test_pure_retirement_oracle_is_not_lost_outside_old_legacy_read_census(self):
        self.source('fraktal_ab_canonical_equivalence', 'VALUE = 1\n')
        self.source('test_fraktal_ab_canonical_equivalence', 'import fraktal_ab_canonical_equivalence\n')
        result = census.inventory(self.root)
        self.assertEqual(result['summary']['directLegacyReferences'], 0)
        self.assertEqual(result['summary']['classifiedPythonModules'], 2)
        self.assertEqual({r['classification'] for r in result['consumers']}, {'MO'})

    def test_exclusive_helper_bundle_follows_oracle_but_shared_and_cli_helpers_stay(self):
        self.source('fraktal_ab_shared', 'VALUE = 1\n')
        self.source('fraktal_ab_private', 'VALUE = 1\n')
        self.source('test_fraktal_ab_private', 'import fraktal_ab_private\n')
        self.source('fraktal_ab_s2_equivalence', 'import fraktal_ab_private\nimport fraktal_ab_shared\n')
        self.source('fraktal_ab_phase1_execute', 'import fraktal_ab_shared\n')
        # Explicit owners do not make their imported dependencies legacy
        # consumers. An actual legacy read supplies the migration seed.
        for name in ('fraktal_ab_private', 'fraktal_ab_shared', 'fraktal_ab_cli'):
            self.source(name, 'def read_layout(): pass\nread_layout()\n')
        rows = {r['module']: r for r in census.inventory(self.root)['consumers']}
        self.assertEqual(rows['fraktal_ab_private']['helperFollows'], 'MO')
        self.assertEqual(rows['test_fraktal_ab_private']['helperFollows'], 'MO')
        self.assertIsNone(rows['fraktal_ab_shared']['helperFollows'])
        self.assertIsNone(rows['fraktal_ab_cli']['helperFollows'])

    def test_unresolved_dynamic_import_is_explicit_and_never_executed(self):
        self.source('fraktal_ab_phase1_execute', 'import importlib\nimportlib.import_module(selected)\n')
        row = census.inventory(self.root)['consumers'][0]
        self.assertEqual(row['dynamicImports'], [dict(line=2, literal=None)])
        self.assertEqual(row['action'], 'verify-canonical-or-standalone-probe')

    def test_missing_external_retirement_artifact_stops_inventory(self):
        self.source('fraktal_ab_projection', 'VALUE=1\n')
        (self.root / census.EXTERNAL_RUNTIME[0]).unlink()
        with self.assertRaisesRegex(ValueError, 'artifact missing'):
            census.inventory(self.root)

    def test_cli_refuses_existing_output(self):
        self.source('fraktal_ab_projection', 'VALUE=1\n')
        path = self.root / 'result.json'
        path.write_text('original', encoding='utf-8')
        with self.assertRaises(SystemExit):
            census.main(['--root', str(self.root), '--output', str(path)])
        self.assertEqual(path.read_text(encoding='utf-8'), 'original')


if __name__ == '__main__':
    unittest.main()

"""O12: the configuration document revision, and every pre-collapse revision still accepted."""

import dataclasses
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import fraktal_ab_canonical_publication as pub
import fraktal_ab_declaration as decl
import fraktal_ab_document_revision as document
import fraktal_ab_genealogy_s6_host_demo as genealogy
import fraktal_ab_press_demo as press
import fraktal_ab_sets as sets

HERE = Path(__file__).resolve().parent
PROBE = ('import json, fraktal_ab_station as s, fraktal_ab_sets as sets, fraktal_ab_document_revision as d; '
         'a = s.application(); print(json.dumps([d.revision(a), list(d.predecessors(a)), sets.accepted_revisions(a)]))')


def with_value(app, change, record_change=None):
    """`app` with its first editable value changed by `change(member)`, and
    optionally that value's record by `record_change(record)`."""
    for r_index, record in enumerate(app.records):
        for m_index, member in enumerate(record.members):
            if member.editable:
                members = list(record.members)
                members[m_index] = change(member)
                record = dataclasses.replace(record, members=tuple(members))
                if record_change:
                    record = record_change(record)
                records = list(app.records)
                records[r_index] = record
                return dataclasses.replace(app, records=tuple(records))
    raise AssertionError('no editable value')


class Identity(unittest.TestCase):
    def setUp(self):
        self.app = press.application()

    def test_the_revision_is_the_identity_and_the_header_publishes_it(self):
        identity = document.identity(self.app)
        self.assertRegex(identity, r'^[0-9A-F]{16}$')
        self.assertEqual(document.revision(self.app), int(identity[:6], 16))
        app = genealogy.application()
        self.assertEqual(pub.manifest_values(app)['LegacyContentHash'], document.identity(app),
                         'configRev = LegacyContentHash[:6] must hold for the reader')

    def test_a_change_that_leaves_every_value_meaning_the_same_keeps_it(self):
        base = document.identity(self.app)
        for name, variant in (
                ('no signal tower', dataclasses.replace(self.app, signal_tower=None)),
                ('host services', dataclasses.replace(self.app, canonical_host_services=True)),
                ('records reversed', dataclasses.replace(self.app, records=tuple(reversed(self.app.records)))),
                ('a range narrowed', with_value(self.app, lambda m: dataclasses.replace(m, maximum=m.maximum - 1))),
                ('a write level raised', with_value(self.app, lambda m: dataclasses.replace(m, min_write_level=4)))):
            with self.subTest(name):
                self.assertEqual(document.identity(variant), base)

    def test_a_change_to_what_a_value_means_moves_it(self):
        base = document.identity(self.app)
        for name, variant in (
                ('a key renamed', with_value(self.app, lambda m: dataclasses.replace(m, write_key=m.write_key + '2'))),
                ('a kind changed', with_value(self.app, lambda m: dataclasses.replace(
                    m, kind='duration_ms' if m.kind != 'duration_ms' else 'scalar'))),
                ('its record schema bumped', with_value(self.app, lambda m: m, lambda r: dataclasses.replace(
                    r, schema_version=r.schema_version + 1))),
                ('another root', dataclasses.replace(self.app, name='Other'))):
            with self.subTest(name):
                self.assertNotEqual(document.identity(variant), base)

    def test_documents_carry_the_revision(self):
        doc = sets.values_document(self.app, 'S', 1, lambda *_: 0, '', 0, 0)
        self.assertEqual(doc[0]['configRev'], document.revision(self.app))
        self.assertTrue(all(r['rev'] == document.revision(self.app) for r in doc[1:]))


class Predecessors(unittest.TestCase):
    def test_each_declaration_in_the_tree_accepts_exactly_its_recorded_revisions(self):
        record = json.loads(document.RECORD.read_text(encoding='utf-8'))['declarations']
        env = {k: v for k, v in os.environ.items() if k != 'FRAKTAL_AB_DECLARATION'}
        for row in record:
            with self.subTest(row['declaration']):
                done = subprocess.run([sys.executable, '-c', PROBE], capture_output=True, text=True, cwd=HERE,
                                      env=dict(env, FRAKTAL_AB_DECLARATION=row['declaration']))
                self.assertEqual(done.returncode, 0, done.stderr[-2000:])
                own, predecessors, accepted = json.loads(done.stdout)
                self.assertEqual(predecessors, row['acceptedRevisions'],
                                 'exactly its own pre-collapse build, never another declaration\'s')
                self.assertEqual(accepted, sorted({own, *row['acceptedRevisions']}))

    def test_the_record_is_the_one_written_before_the_collapse(self):
        self.assertEqual(len(document._record()), 27)
        for name, revisions in document._record().items():
            with self.subTest(name):
                self.assertIn(document.saved_revision(name), revisions)
        with self.assertRaises(ValueError):
            document.recorded('fraktal_ab_never_recorded', '0' * 16)

    def test_a_station_outside_the_tree_declares_its_own(self):
        elsewhere = dataclasses.replace(press.application(), name='Elsewhere', config_predecessors=None)
        mine = decl.ConfigPredecessors(identity=document.identity(elsewhere), revisions=(0x123456,))
        app = dataclasses.replace(elsewhere, config_predecessors=mine)
        self.assertEqual(document.validate(app), [])
        self.assertEqual(sets.accepted_revisions(app), sorted({document.revision(app), 0x123456}))
        for bad in ((0x1000000,), (-1,), ('12',), (True,)):
            with self.subTest(bad):
                wrong = dataclasses.replace(app, config_predecessors=dataclasses.replace(mine, revisions=bad))
                self.assertEqual(len(document.validate(wrong)), 1)
                self.assertEqual(document.accepted(wrong), [document.revision(app)])

    def test_predecessors_do_not_survive_a_change_of_meaning(self):
        """A record schema bump is migrate-or-fault: documents saved before refuse,
        and the declaration that still claims them does not validate."""
        app = press.application()
        old = app.config_predecessors.revisions
        changed = with_value(app, lambda m: m, lambda r: dataclasses.replace(r, schema_version=r.schema_version + 1))
        self.assertEqual(changed.config_predecessors, app.config_predecessors, 'replace carries them over')
        self.assertEqual(document.predecessors(changed), ())
        self.assertEqual(sets.accepted_revisions(changed), [document.revision(changed)])
        self.assertTrue(any('changed meaning' in f for f in decl.validate(changed)))
        self.assertTrue(set(old).isdisjoint(sets.accepted_revisions(changed)))


if __name__ == '__main__':
    unittest.main()

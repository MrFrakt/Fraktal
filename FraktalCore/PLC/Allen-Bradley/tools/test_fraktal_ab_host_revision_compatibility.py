"""Execute the shared revision guard at the V6.11 host-services boundary.

The host-services opt-in changes build identity, never the editable value
schema, so a set or live document saved by the same declaration without it
must still load: the genealogy baseline's documents are what the first V6.11
download restores. A changed value shape or a foreign station still refuses.

Since O12 the document revision no longer moves with the opt-in at all. What
documents saved before carry is the pre-collapse record, so the revisions
here are taken from it, never recomputed from the V5 content later
increments change.
"""
from dataclasses import replace
import json
import unittest
import fraktal_ab_declaration as decl
import fraktal_ab_document_revision as docrev
import fraktal_ab_genealogy_demo as baseline
import fraktal_ab_genealogy_s4b_owner_demo as predecessor
import fraktal_ab_genealogy_s6_host_demo as candidate
import fraktal_ab_manifest as manifest
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st

RECORD = {row['declaration']: row for row in
          json.loads(docrev.RECORD.read_text(encoding='utf-8'))['declarations']}


class HostServiceRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.old, cls.base = candidate.application(), predecessor.application(), baseline.application()
        cls.saved = RECORD['fraktal_ab_genealogy_s6_host_demo']
        cls.saved_old = RECORD['fraktal_ab_genealogy_s4b_owner_demo']
        cls.saved_base = RECORD['fraktal_ab_genealogy_demo']

    def rejected(self, app, revision):
        model = st.Controller(dict(Revision=revision, Rejected=0))
        model.run('Rejected := ' + sets.revision_rejected(app, 'Revision') + ';')
        return bool(model.tags['Rejected'])

    def test_the_opt_in_changes_build_identity_but_not_the_document_revision(self):
        self.assertEqual(self.app.records, self.old.records)
        self.assertEqual(manifest.content_hash(replace(self.app, canonical_host_services=False)),
                         manifest.content_hash(self.old))
        self.assertNotEqual(manifest.content_hash(self.app), manifest.content_hash(self.old))
        self.assertEqual(docrev.revision(self.app), docrev.revision(self.old))

    def test_documents_saved_without_host_services_still_load(self):
        for revision in (docrev.revision(self.app), self.saved['configRevision'],
                         self.saved_old['configRevision'], self.saved_base['configRevision']):
            with self.subTest(revision=revision):
                self.assertFalse(self.rejected(self.app, revision))

    def test_every_revision_the_predecessor_accepted_is_still_accepted(self):
        self.assertLessEqual(set(self.saved_old['acceptedRevisions']), set(sets.accepted_revisions(self.app)))

    def test_changed_configuration_shape_and_foreign_station_do_not_inherit_the_revision(self):
        record = next(r for r in self.app.records if r.station_cfg)
        changed = replace(record, schema_version=record.schema_version + 1,
                          members=record.members + (decl.scalar('CompatibilityAddedField'),))
        app = replace(self.app, records=tuple(changed if r is record else r for r in self.app.records))
        for revision in (self.saved_old['configRevision'], self.saved_base['configRevision']):
            with self.subTest(revision=revision):
                self.assertTrue(self.rejected(app, revision))
                self.assertTrue(self.rejected(replace(self.app, name='OtherStation'), revision))

    def test_unknown_revisions_and_the_future_remain_refused(self):
        for revision in (0, 1, -1, 0x7fffffff, self.saved_old['configRevision'] ^ 0x13579):
            with self.subTest(revision=revision):
                self.assertTrue(self.rejected(self.app, revision))
        # An image built before the collapse never learns the new revision.
        self.assertNotIn(docrev.revision(self.app), self.saved_old['acceptedRevisions'])

    def test_the_nested_guard_decides_as_the_whole_conjunction_within_the_built_size(self):
        alias = sets.scratch_names(self.app)[1]
        lines = sets.revision_guard(self.app, 'Revision', 'Reason', 42)
        self.assertGreater(len(sets.accepted_revisions(self.app)), sets.GUARD_TERMS)
        # 2,284 characters is the longest single guard v38 has built.
        self.assertLessEqual(max(len(line) for line in lines), 2284)
        accepted = sets.accepted_revisions(self.app)
        for revision in (*accepted, 0, -1, 0x7fffffff, accepted[0] - 1, accepted[-1] + 1):
            with self.subTest(revision=revision):
                model = st.Controller(dict(Revision=revision, Reason=0, **{alias: 0}))
                model.run('\n'.join(lines))
                self.assertEqual(model.tags['Reason'] == 42, self.rejected(self.app, revision))
        # A declaration within the built size keeps the single-line guard.
        self.assertLessEqual(len(sets.accepted_revisions(self.base)), sets.GUARD_TERMS)
        single = sets.revision_guard(self.base, 'Revision', 'Reason', 42)
        self.assertEqual(sum(line.startswith('IF ') for line in single), 1)

    def test_native_guard_snapshots_the_long_operand_without_changing_it(self):
        alias = sets.scratch_names(self.app)[1]
        for revision, expected in [(self.saved_base['configRevision'], 0), (0, 42)]:
            model = st.Controller(dict(Revision=revision, Reason=0, **{alias: 0}))
            lines = sets.revision_guard(self.app, 'Revision', 'Reason', 42)
            model.run('\n'.join(lines))
            self.assertEqual((model.tags['Revision'], model.tags['Reason']), (revision, expected))


if __name__ == '__main__':
    unittest.main()

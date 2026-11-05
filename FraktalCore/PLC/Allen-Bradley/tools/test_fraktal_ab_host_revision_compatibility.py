"""Execute the shared revision guard at the V6.11 host-services boundary.

The host-services opt-in changes build identity, never the editable value
schema, so a set or live document saved by the same declaration without it
must still load: the genealogy baseline's documents are what the first V6.11
download restores. A changed value shape or a foreign station still refuses.
"""
from dataclasses import replace
import unittest
import fraktal_ab_declaration as decl
import fraktal_ab_genealogy_demo as baseline
import fraktal_ab_genealogy_s4b_owner_demo as predecessor
import fraktal_ab_genealogy_s6_host_demo as candidate
import fraktal_ab_manifest as manifest
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st


class HostServiceRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.old, cls.base = candidate.application(), predecessor.application(), baseline.application()

    def rejected(self, app, revision):
        model = st.Controller(dict(Revision=revision, Rejected=0))
        model.run('Rejected := ' + sets.revision_rejected(app, 'Revision') + ';')
        return bool(model.tags['Rejected'])

    def test_the_opt_in_changes_identity_but_not_the_value_schema(self):
        self.assertEqual(self.app.records, self.old.records)
        self.assertEqual(manifest.content_hash(replace(self.app, canonical_host_services=False)),
                         manifest.content_hash(self.old))
        self.assertNotEqual(manifest.config_revision(self.app), manifest.config_revision(self.old))

    def test_documents_saved_without_host_services_still_load(self):
        for revision in (manifest.config_revision(self.app), manifest.config_revision(self.old),
                         manifest.config_revision(self.base)):
            with self.subTest(revision=revision):
                self.assertFalse(self.rejected(self.app, revision))

    def test_every_revision_the_predecessor_accepts_is_still_accepted(self):
        import re
        old = {int(v) for v in re.findall(r'<> (\d+)', sets.revision_rejected(self.old, 'X'))}
        new = {int(v) for v in re.findall(r'<> (\d+)', sets.revision_rejected(self.app, 'X'))}
        self.assertLessEqual(old, new)

    def test_changed_configuration_shape_and_foreign_station_do_not_inherit_the_revision(self):
        record = next(r for r in self.app.records if r.station_cfg)
        changed = replace(record, schema_version=record.schema_version + 1,
                          members=record.members + (decl.scalar('CompatibilityAddedField'),))
        app = replace(self.app, records=tuple(changed if r is record else r for r in self.app.records))
        for revision in (manifest.config_revision(self.old), manifest.config_revision(self.base)):
            with self.subTest(revision=revision):
                self.assertTrue(self.rejected(app, revision))
                self.assertTrue(self.rejected(replace(self.app, name='OtherStation'), revision))

    def test_unknown_revisions_and_the_future_remain_refused(self):
        for revision in (0, 1, -1, 0x7fffffff, manifest.config_revision(self.old) ^ 0x13579):
            with self.subTest(revision=revision):
                self.assertTrue(self.rejected(self.app, revision))
        self.assertTrue(self.rejected(self.old, manifest.config_revision(self.app)))

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
        # Every earlier declaration keeps its single-line guard byte for byte.
        self.assertEqual(len(sets.revision_guard(self.old, 'Revision', 'Reason', 42)), 2)

    def test_native_guard_snapshots_the_long_operand_without_changing_it(self):
        alias = sets.scratch_names(self.app)[1]
        for revision, expected in [(manifest.config_revision(self.base), 0), (0, 42)]:
            model = st.Controller(dict(Revision=revision, Reason=0, **{alias: 0}))
            lines = sets.revision_guard(self.app, 'Revision', 'Reason', 42)
            model.run('\n'.join(lines))
            self.assertEqual((model.tags['Revision'], model.tags['Reason']), (revision, expected))


if __name__ == '__main__':
    unittest.main()

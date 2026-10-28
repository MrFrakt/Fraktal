"""Execute the shared revision guard at the S3k publication-only boundary."""
from dataclasses import replace
import unittest
import fraktal_ab_declaration as decl
import fraktal_ab_genealogy_demo as baseline
import fraktal_ab_genealogy_s3k_demo as candidate
import fraktal_ab_manifest as manifest
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st


class PublicationRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=candidate.application();cls.old=baseline.application()
        cls.old_revision=manifest.config_revision(cls.old)

    def rejected(self,app,revision):
        model=st.Controller(dict(Revision=revision,Rejected=0))
        model.run('Rejected := '+sets.revision_rejected(app,'Revision')+';')
        return bool(model.tags['Rejected'])

    def test_identical_configuration_records_accept_the_exact_previous_publication(self):
        self.assertEqual(self.app.records,self.old.records)
        previous=replace(self.app,canonical_publication_stage=12)
        self.assertEqual(manifest.content_hash(previous),manifest.content_hash(self.old))
        self.assertNotEqual(manifest.config_revision(self.app),self.old_revision)
        self.assertFalse(self.rejected(self.app,self.old_revision))
        self.assertFalse(self.rejected(self.app,manifest.config_revision(self.app)))

    def test_changed_configuration_shape_and_foreign_station_do_not_inherit_the_revision(self):
        record=next(r for r in self.app.records if r.station_cfg)
        changed=replace(record,schema_version=record.schema_version+1,
            members=record.members+(decl.scalar('CompatibilityAddedField'),))
        app=replace(self.app,records=tuple(changed if r is record else r for r in self.app.records))
        self.assertTrue(self.rejected(app,self.old_revision))
        self.assertTrue(self.rejected(replace(self.app,name='OtherStation'),self.old_revision))

    def test_unknown_and_invalid_revisions_remain_refused(self):
        for revision in (0,1,-1,0x7fffffff,self.old_revision^0x13579):
            with self.subTest(revision=revision):self.assertTrue(self.rejected(self.app,revision))

    def test_older_profiles_do_not_accept_the_future_s3k_publication(self):
        self.assertTrue(self.rejected(self.old,manifest.config_revision(self.app)))

    def test_native_guard_snapshots_the_long_operand_without_changing_it(self):
        alias=sets.scratch_names(self.app)[1]
        for revision,expected in [(self.old_revision,0),(0,42)]:
            model=st.Controller(dict(Revision=revision,Reason=0,**{alias:0}))
            lines=sets.revision_guard(self.app,'Revision','Reason',42)
            model.run('\n'.join(lines))
            self.assertEqual((model.tags['Revision'],model.tags['Reason']),(revision,expected))
            self.assertLess(len(lines[-1]),3000)


if __name__=='__main__':unittest.main()

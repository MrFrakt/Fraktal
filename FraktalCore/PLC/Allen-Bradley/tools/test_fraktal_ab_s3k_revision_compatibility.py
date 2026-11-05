"""Execute the shared revision guard at the S3k publication-only boundary.

Since O12 the document revision no longer moves with the publication stage;
what documents saved before carry is the pre-collapse record, so the
revisions here come from it.
"""
from dataclasses import replace
import json
import unittest
import fraktal_ab_declaration as decl
import fraktal_ab_document_revision as docrev
import fraktal_ab_genealogy_demo as baseline
import fraktal_ab_genealogy_s3k_demo as candidate
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st

RECORD = {row['declaration']: row for row in
          json.loads(docrev.RECORD.read_text(encoding='utf-8'))['declarations']}


class PublicationRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=candidate.application();cls.old=baseline.application()
        cls.old_revision=RECORD['fraktal_ab_genealogy_demo']['configRevision']
        cls.saved=RECORD['fraktal_ab_genealogy_s3k_demo']

    def rejected(self,app,revision):
        model=st.Controller(dict(Revision=revision,Rejected=0))
        model.run('Rejected := '+sets.revision_rejected(app,'Revision')+';')
        return bool(model.tags['Rejected'])

    def test_identical_configuration_records_accept_the_exact_previous_publication(self):
        self.assertEqual(self.app.records,self.old.records)
        self.assertEqual(docrev.revision(self.app),docrev.revision(self.old))
        self.assertNotEqual(self.saved['configRevision'],self.old_revision)
        for revision in (self.old_revision,self.saved['configRevision'],docrev.revision(self.app)):
            with self.subTest(revision=revision):self.assertFalse(self.rejected(self.app,revision))

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

    def test_older_profiles_did_not_accept_the_future_s3k_publication(self):
        self.assertNotIn(self.saved['configRevision'],RECORD['fraktal_ab_genealogy_demo']['acceptedRevisions'])

    def test_native_guard_snapshots_the_long_operand_without_changing_it(self):
        alias=sets.scratch_names(self.app)[1]
        for revision,expected in [(self.old_revision,0),(0,42)]:
            model=st.Controller(dict(Revision=revision,Reason=0,**{alias:0}))
            lines=sets.revision_guard(self.app,'Revision','Reason',42)
            model.run('\n'.join(lines))
            self.assertEqual((model.tags['Revision'],model.tags['Reason']),(revision,expected))
            self.assertLess(len(lines[-1]),3000)


if __name__=='__main__':unittest.main()

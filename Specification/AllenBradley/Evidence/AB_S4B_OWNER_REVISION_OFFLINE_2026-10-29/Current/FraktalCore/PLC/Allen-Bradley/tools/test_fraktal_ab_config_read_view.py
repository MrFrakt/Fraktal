"""Execute the real V6.8 publisher against independent configuration oracles."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

import fraktal_ab_config_read_view as view
import fraktal_ab_canonical_config as owner
import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s4b_demo as profile
import fraktal_ab_models as models
import fraktal_ab_generate as gen
import fraktal_ab_canonical_manifest as wire
import test_fraktal_ab_canonical_config as base
import test_fraktal_ab_canonical_text as table_suite
from test_fraktal_ab_read_coherence import physical


class ReadViewTests(table_suite.TableDrivenConfigurationTests):
    def setUp(self):
        app=profile.application()
        with patch.object(base.demo,'application',lambda:app):super().setUp()
        self.controller.tags[view.tag(app)]=self.value(view.VIEW,dict(SchemaVersion=1,RootIdentity=app.name,
            DefinitionCount=view.capacities(app)[0],DefinitionCapacity=view.capacities(app)[0],ValueCapacity=view.capacities(app)[1]))
        self.controller.tags[view.work_tag(app)]=self.value(view.work_type(app))
        self.read=self.controller.tags[view.tag(app)]
        # The core publisher fills these earlier in the same scan; exercise the
        # real R2 owner/read-view code here, not an unrelated model-catalog loop.
        self.root['AvailableModels'][:len(app.models)]=[self.value(pub.string_type(64),m.code) for m in app.models]

    def scan(self):
        super().scan();self.execute(view.cyclic(self.app))

    def row(self,row,kind):
        return {m.name:self.text(row[m.name]) if m.kind.startswith(pub.PREFIX+'String') else
            bool(row[m.name]) if m.kind=='BOOL' else float(row[m.name]) if m.kind=='LREAL' else row[m.name]
            for m in self.schema[kind]}

    def test_every_live_and_model_row_equals_the_existing_independent_page_oracle(self):
        self.scan();definitions=[self.row(r,view.DEFINITION) for r in self.read['Definitions']]
        expected=self.expected(0)
        self.assertEqual(definitions,[dict(DefinitionIndex=i,**{k:v for k,v in e.items() if k not in ('ValueText','Readable')}) for i,e in enumerate(expected)])
        wanted=[dict(DefinitionIndex=i,ModelOrdinal=0,ModelCode='',ValueText=e['ValueText'],Readable=e['Readable'],Revision=self.work['Revision']) for i,e in enumerate(expected)]
        for bank,model in enumerate(self.app.models,1):
            wanted += [dict(DefinitionIndex=i,ModelOrdinal=bank,ModelCode=model.code,ValueText=e['ValueText'],Readable=e['Readable'],Revision=self.work['Revision'])
                for i,e in enumerate(self.expected(bank)) if e['ModelScoped']]
        actual=[self.row(r,view.VALUE) for r in self.read['Values'][:self.read['ValueCount']]]
        self.assertEqual(actual,wanted)

    def test_cold_first_scan_withholds_publication_and_wipes_until_next_scan(self):
        self.controller.tags['S:FS']=True
        for row in self.read['Values']:
            row['Readable']=True
            row['ValueText']['LEN']=4
            row['ValueText']['DATA']=[77]*len(row['ValueText']['DATA'])
        self.scan()
        self.assertFalse(self.controller.tags[pub.header_tag(self.app)]['Valid'])
        self.assertEqual(self.read['ValueCount'],0)
        self.assertEqual(self.controller.tags[view.work_tag(self.app)]['Initialized'],0)
        self.assertTrue(all(not row['Readable'] and not any(row['ValueText']['DATA']) for row in self.read['Values']))
        self.controller.tags['S:FS']=False
        # The enclosing canonical owner starts each scan with Valid=1.
        self.controller.tags[pub.header_tag(self.app)]['Valid']=1
        self.test_every_live_and_model_row_equals_the_existing_independent_page_oracle()
        self.assertTrue(self.controller.tags[pub.header_tag(self.app)]['Valid'])

    def test_retained_first_scan_applies_access_drop_without_deferral(self):
        self.scan()
        self.assertEqual(self.controller.tags[view.work_tag(self.app)]['Initialized'],1)
        self.levels['Readable']=[0]*len(self.levels['Readable'])
        self.controller.tags['S:FS']=True
        self.scan()
        self.assertGreater(self.read['ValueCount'],0)
        self.assertTrue(all(not row['Readable'] and not any(row['ValueText']['DATA']) for row in self.read['Values']))

    def test_invalid_catalogue_is_still_refused_on_a_cold_first_scan(self):
        self.controller.tags['S:FS']=True
        self.controller.tags[models.tag(self.app)]['Count']=(self.app.model_capacity or len(self.app.models))+1
        self.scan()
        self.assertFalse(self.controller.tags[pub.header_tag(self.app)]['Valid'])
        self.assertEqual(self.read['ValueCount'],0)

    def test_independent_migration_reference_matches_all_new_paths(self):
        import fraktal_ab_s4b_equivalence as oracle
        self.scan()
        additional=dict(records=self.records,models=self.controller.tags[gen.model_cfg_tag(self.app)],levels=self.levels,
            query=dict(Revision=self.work['Revision']),read_view_codes=[m.code for m in self.app.models])
        expected=oracle.reference(self.app,additional);root=view.canonical_root(self.app)+'/'
        actual={root+m.name:self.text(self.read[m.name]) if m.name=='RootIdentity' else self.read[m.name]
                for m in self.schema[view.VIEW] if not m.count}
        for group,kind,count in (('Definitions',view.DEFINITION,self.read['DefinitionCount']),('Values',view.VALUE,self.read['ValueCount'])):
            for i,row in enumerate(self.read[group][:count]):actual.update({root+f'{group}[{i}]/'+n:v for n,v in self.row(row,kind).items()})
        self.assertEqual(set(expected),oracle.view_paths(self.app,additional['read_view_codes']))
        self.assertEqual(actual,expected)

    def test_access_drop_wipes_full_value_buffers_and_does_not_publish_a_private_cache(self):
        self.scan();self.assertTrue(any(self.text(row['ValueText']) for row in self.read['Values']))
        self.levels['Readable']=[0]*len(self.levels['Readable']);self.scan()
        for row in self.read['Values']:
            self.assertFalse(row['Readable']);self.assertEqual(row['ValueText']['LEN'],0)
            self.assertEqual(set(row['ValueText']['DATA']),{0})
        # The current canonical page follows the same full-buffer rule, including
        # unused tail slots. It cannot retain a previously readable value.
        for row in self.root['HmiResponse']['ConfigPage']['Entries']:
            self.assertEqual(set(row['ValueText']['DATA']),{0})
        self.assertTrue(any(self.work['ValueCache']))
        self.assertIn('ExternalAccess="None"',''.join(view.tags(self.app,lambda name,kind,values,**kw:f'{name} ExternalAccess="{kw.get("access","Read Only")}"')))

    def test_changed_values_and_banks_refresh_once_with_clean_string_tails(self):
        self.scan();original=deepcopy(self.read);self.scan();self.assertEqual(self.read,original)
        self.controller.tags[gen.model_cfg_tag(self.app)][1]['PressDwellMs']=913
        self.scan();self.assertNotEqual(self.read['Revision'],original['Revision'])
        for row in self.read['Values'][:self.read['ValueCount']]:
            self.assertEqual(set(row['ValueText']['DATA'][row['ValueText']['LEN']:]),{0})
        self.test_every_live_and_model_row_equals_the_existing_independent_page_oracle()

    def test_invalid_catalogue_count_is_masked_instead_of_indexing_outside_the_model_bank(self):
        self.scan();self.controller.tags[models.tag(self.app)]['Count']=(self.app.model_capacity or len(self.app.models))+1
        self.scan();self.assertEqual(self.read['ValueCount'],0)
        self.assertFalse(self.controller.tags[pub.header_tag(self.app)]['Valid'])
        self.assertTrue(all(not r['Readable'] and not any(r['ValueText']['DATA']) for r in self.read['Values']))


class ReadServiceWireTests(unittest.TestCase):
    def test_new_manifest_hashes_the_view_service_and_extents_with_no_root_layout_change(self):
        import fraktal_ab_genealogy_s4_demo as old
        app=profile.application();header=pub.manifest_values(app);normalized=wire.normalize(physical(header))
        self.assertEqual(header['SchemaMinor'],8)
        self.assertEqual(normalized['readServices'],view.descriptors(app))
        self.assertEqual(len(normalized['dataProducts']),2)
        self.assertEqual(pub.root_type(app),pub.root_type(old.application()))
        self.assertEqual(pub.schema(app)[pub.root_type(app)],pub.schema(old.application())[pub.root_type(app)])
        bad=deepcopy(header);bad['ReadServices'][0]['CanonicalRoot']='Other/View'
        with self.assertRaisesRegex(ValueError,'hash/revision'):wire.normalize(physical(bad))

    def test_disabled_flag_is_empty_and_incompatible_or_malformed_profiles_refuse(self):
        app=profile.application()
        self.assertEqual(view.validate(app),[])
        self.assertEqual(view.products(replace(app,canonical_config_read_view=False)),[])
        for candidate in (replace(app,canonical_config_read_view='yes'),replace(app,canonical_read_coherence=False),replace(app,canonical_table_driven=False)):
            self.assertTrue(view.validate(candidate))
        with self.assertRaises(ValueError):view.validate_descriptors(view.descriptors(app)*2)


if __name__=='__main__':unittest.main()

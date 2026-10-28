"""V6.7 is additive metadata; existing values, guards and profiles stay intact."""
from copy import deepcopy
from dataclasses import replace
import unittest

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s3k_demo as previous
import fraktal_ab_genealogy_s4_demo as candidate
import fraktal_ab_read_coherence as coherence


def physical(value):
    if isinstance(value, str):
        data=value.encode()
        return dict(string=True, width=max(255,len(data)), LEN=len(data), bytes=data.hex())
    if isinstance(value, list):return [physical(item) for item in value]
    if isinstance(value, dict):return {key:physical(item) for key,item in value.items()}
    return value


class ReadCoherenceTests(unittest.TestCase):
    def test_descriptor_covers_root_and_product_using_the_existing_scan_guard(self):
        app=candidate.application();rows=coherence.rows(app)
        self.assertEqual({row['CanonicalPrefix'] for row in rows},
            {app.name,*(p['CanonicalRoot'] for p in __import__('fraktal_ab_canonical_fieldbus').products(app))})
        self.assertTrue(all(row['RevisionSymbol']==pub.generation_tag(app) for row in rows))
        self.assertTrue(all(row['Protocol']==1 and row['MutationPeriodUs']==app.task_period_ms*1000 for row in rows))
        self.assertEqual(coherence.validate(app),[])

    def test_flag_does_not_change_the_root_schema_or_cyclic_publication(self):
        old,new=previous.application(),candidate.application()
        self.assertEqual(pub.root_type(old),pub.root_type(new))
        left,right=pub.schema(old),pub.schema(new)
        self.assertEqual(left[pub.root_type(old)],right[pub.root_type(new)])
        self.assertEqual(pub.begin_scan(old),pub.begin_scan(new))
        self.assertEqual(pub.cyclic(old),pub.cyclic(new))
        self.assertEqual(pub.manifest_values(old)['SchemaMinor'],6)
        self.assertEqual(pub.manifest_values(new)['SchemaMinor'],7)

    def test_physical_manifest_validates_and_hashes_the_new_table(self):
        app=candidate.application();header=pub.manifest_values(app)
        normalized=wire.normalize(physical(header))
        self.assertEqual(normalized['readCoherenceBindings'],coherence.rows(app))
        self.assertEqual(normalized['schemaMinor'],7)
        damaged=deepcopy(header)
        damaged['ReadCoherenceBindings'][0]['RevisionSymbol']='DifferentGuard'
        with self.assertRaisesRegex(ValueError,'hash/revision'):
            wire.normalize(physical(damaged))

    def test_binding_validation_rejects_bad_scope_protocol_and_period(self):
        rows=coherence.rows(candidate.application())
        for field,value in [('CanonicalPrefix','Root/../Other'),('RevisionSymbol',''),
                            ('Protocol',2),('Protocol',True),('MutationPeriodUs',0),
                            ('MutationPeriodUs',60000001)]:
            modified=deepcopy(rows);modified[0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                coherence.validate_rows(modified)
        with self.assertRaises(ValueError):coherence.validate_rows(rows+[rows[0]])
        nested=deepcopy(rows);nested.append(dict(rows[0],CanonicalPrefix=rows[0]['CanonicalPrefix']+'/Child'))
        with self.assertRaises(ValueError):coherence.validate_rows(nested)
        with self.assertRaises(ValueError):coherence.validate_rows(rows,expected_prefixes={'Other'})

    def test_table_counts_and_profile_requirements_fail_closed(self):
        app=candidate.application();header=pub.manifest_values(app)
        for count in (0,True,1025):
            damaged=deepcopy(header);damaged['ReadCoherenceBindingsCount']=count
            with self.subTest(count=count),self.assertRaises(ValueError):wire.normalize(physical(damaged))
        self.assertTrue(coherence.validate(replace(app,canonical_read_coherence='yes')))
        self.assertTrue(coherence.validate(replace(app,canonical_publication_stage=12)))


if __name__=='__main__':unittest.main()

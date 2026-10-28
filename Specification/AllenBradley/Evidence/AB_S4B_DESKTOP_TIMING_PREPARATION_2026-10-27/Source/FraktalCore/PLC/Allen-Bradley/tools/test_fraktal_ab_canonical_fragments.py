"""V6.2 metadata records join disjoint native fields without station knowledge."""
from copy import deepcopy
import struct
import unittest

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_reader as reader
from test_fraktal_ab_canonical_reader import synthetic,member
from test_fraktal_ab_canonical_publication import fixture,string


def capture():
    c=synthetic();m=c['manifest'];m.update(schemaMinor=2,fragmentRevision=7,
        bindings=[dict(SourceSymbol='Definitions',TargetRoot='Mixer')])
    c['coherenceBefore']=c['coherenceAfter']=['SYNTHETIC',1,7]
    c['templates'] += [dict(handle=0x701,name='Definition',byteSize=4,members=[member('Extra',0xC4,0)]),
        dict(handle=0x702,name='Metadata',byteSize=8,members=[member('Kids',0xa701,0,2)])]
    c['symbols'].append(dict(name='Definitions',handle=0x702,arrayRank=0))
    c['records'].append(dict(tag='Definitions',rawHex=struct.pack('<ii',123,456).hex()))
    m['annotations']['Mixer/Kids[*]/Extra']=dict(logicalType='DURATION')
    return c


class FragmentTests(unittest.TestCase):
    def test_disjoint_fields_join_the_same_paths_without_extra_modules(self):
        doc=reader.snapshot(capture())
        self.assertEqual(doc['values']['Mixer/Kids[1]/Extra'],123)
        self.assertEqual(doc['values']['Mixer/Kids[2]/Extra'],456)
        self.assertEqual(doc['values']['Mixer/Kids[2]/Value'],-9)
        self.assertEqual(doc['types']['Mixer/Kids[1]/Extra'],'Int32')
        self.assertEqual(doc['moduleCount'],1)
        self.assertFalse(any(path.startswith('Definitions/') for path in doc['values']))

    def test_metadata_revision_is_part_of_acquisition_coherence(self):
        c=capture();c['coherenceAfter'][-1]=8
        with self.assertRaisesRegex(ValueError,'changed'):reader.snapshot(c)
        for value in (-1,True,1<<31):
            c=capture();c['manifest']['fragmentRevision']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'revision'):reader.snapshot(c)

    def test_colliding_leaves_and_mismatched_extents_are_refused(self):
        c=capture();c['templates'][-2]['members'][0]['name']='Value'
        with self.assertRaisesRegex(ValueError,'collision'):reader.snapshot(c)
        c=capture();c['templates'][-1]['members'][0]['info']=1
        c['templates'][-1]['byteSize']=4;c['records'][-1]['rawHex']=struct.pack('<i',123).hex()
        with self.assertRaisesRegex(ValueError,'shape mismatch'):reader.snapshot(c)

    def test_fragment_cannot_create_a_module_or_alias_a_root(self):
        c=capture();c['templates'][-2]['members'][0]['name']='Status'
        with self.assertRaisesRegex(ValueError,'identity'):reader.snapshot(c)
        c=capture();c['manifest']['bindings'][0]['SourceSymbol']='Mixer'
        with self.assertRaisesRegex(ValueError,'source/root'):reader.snapshot(c)

    def test_missing_duplicate_and_unbound_records_are_refused(self):
        for mutate in (lambda c:c['records'].pop(),
                       lambda c:c['manifest']['bindings'].append(deepcopy(c['manifest']['bindings'][0])),
                       lambda c:c['records'].append(dict(tag='Stray',rawHex='00')),
                       lambda c:c['manifest']['bindings'][0].update(TargetRoot='Unknown')):
            c=capture();mutate(c)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):reader.snapshot(c)

    def test_fragment_schema_is_validated_below_empty_live_views(self):
        c=capture();m=c['manifest'];m['annotations']['Mixer/Kids'].update(countPath='Mixer/End')
        raw=bytearray.fromhex(c['records'][0]['rawHex']);struct.pack_into('<i',raw,80,0)
        c['records'][0]['rawHex']=raw.hex()
        self.assertFalse(any('/Kids[' in p for p in reader.snapshot(c)['values']))
        m['annotations']['Mixer/Kids[*]/Extra']['logicalType']='TIMESTAMP'
        with self.assertRaisesRegex(ValueError,'logical/native'):reader.snapshot(c)

    def test_older_minor_cannot_smuggle_bindings(self):
        c=capture();c['manifest']['schemaMinor']=1
        with self.assertRaisesRegex(ValueError,'V6.2'):reader.snapshot(c)


class FragmentWireTests(unittest.TestCase):
    def record(self):
        r=fixture();r.update(SchemaMinor=2,PublicationStage=5,FragmentRevision=0,
            BindingsCount=1,BindingsCapacity=1,Bindings=[dict(SourceSymbol=string('Defs',80),TargetRoot=string('Mixer',80))])
        for field in r['Fields']:field.update(CountPath=string('',255),Indices=string('',255))
        fields=[{k:wire.text(v) if isinstance(v,dict) else v for k,v in f.items()} for f in r['Fields']]
        digest=wire.content_hash(fields,wire.text(r['LegacyContentHash']),5,minor=2,
            bindings=[dict(SourceSymbol='Defs',TargetRoot='Mixer')])
        r.update(ContentHash=string(digest,80),ConfigRevision=wire.revision(digest))
        return r

    def test_bindings_are_hashed_but_the_data_revision_is_live(self):
        r=self.record();first=wire.normalize(r);r['FragmentRevision']=17
        second=wire.normalize(r)
        self.assertEqual(first['contentHash'],second['contentHash'])
        self.assertEqual(second['fragmentRevision'],17)
        r['Bindings'][0]['SourceSymbol']=string('Other',80)
        with self.assertRaisesRegex(ValueError,'hash'):wire.normalize(r)

    def test_ambiguous_counts_and_sources_are_refused(self):
        for mutate in (lambda r:r.update(BindingsCount=0),lambda r:r.update(BindingsCapacity=2),
                       lambda r:r.update(FragmentRevision=-1),
                       lambda r:r['Bindings'][0].update(SourceSymbol=string('Bad.Path',80))):
            r=self.record();mutate(r)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):wire.normalize(r)


if __name__=='__main__':unittest.main()

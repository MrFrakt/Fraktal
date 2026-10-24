"""Generic V6.1 array-view invariants, independent of any station declaration."""
from copy import deepcopy
import struct
import unittest

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_reader as reader
from test_fraktal_ab_canonical_reader import synthetic
from types import SimpleNamespace
from test_fraktal_ab_canonical_publication import fixture, string, wire_fixture
from test_fraktal_ab_canonical_reader import member


def view(count=2):
    c=synthetic();c['manifest']['schemaMinor']=1
    c['manifest']['annotations']['Mixer/Kids']['countPath']='Mixer/End'
    raw=bytearray.fromhex(c['records'][0]['rawHex']);struct.pack_into('<i',raw,80,count)
    c['records'][0]['rawHex']=raw.hex()
    return c


class ArrayViewTests(unittest.TestCase):
    def test_live_count_changes_view_without_changing_its_schema_or_storage(self):
        documents=[reader.snapshot(view(count)) for count in (2,1,0,2)]
        self.assertEqual([len([p for p in d['values'] if '/Kids[' in p]) for d in documents],[4,2,0,4])
        self.assertEqual(documents[0]['values']['Mixer/Kids[2]/Value'],-9)
        self.assertEqual(documents[0]['contentHash'],documents[2]['contentHash'])
        self.assertEqual(documents[0]['values'],documents[3]['values'])

    def test_sparse_indices_preserve_core_indices_and_hide_unselected_storage(self):
        c=view();a=c['manifest']['annotations']
        del a['Mixer/Kids']['countPath'];a['Mixer/Kids']['indices']=[1]
        a['Mixer/Bits']['indices']=[0,2]
        d=reader.snapshot(c)
        self.assertNotIn('Mixer/Kids[1]/Value',d['values'])
        self.assertEqual(d['values']['Mixer/Kids[2]/Value'],-9)
        self.assertNotIn('Mixer/Bits[1]',d['values'])
        self.assertTrue(d['values']['Mixer/Bits[2]'])

    def test_static_prefix_requires_view_minor_and_never_changes_physical_stride(self):
        c=view();a=c['manifest']['annotations']['Mixer/Kids'];del a['countPath'];a['elementCount']=1
        d=reader.snapshot(c);self.assertEqual(d['values']['Mixer/Kids[1]/Value'],7)
        self.assertNotIn('Mixer/Kids[2]/Value',d['values'])
        c['manifest']['schemaMinor']=0
        with self.assertRaisesRegex(ValueError,'Template extent'):reader.snapshot(c)

    def test_invalid_count_references_counts_and_selections_fail_closed(self):
        for count in (-1,3):
            with self.subTest(count=count),self.assertRaisesRegex(ValueError,'live array count'):reader.snapshot(view(count))
        for reference in ('Unknown/End','Mixer/Bits','Mixer/Status','Mixer/Kids[*]/Value','Mixer/Stamp','Mixer/Absent'):
            c=view();c['manifest']['annotations']['Mixer/Kids']['countPath']=reference
            with self.subTest(reference=reference),self.assertRaisesRegex(ValueError,'count reference'):reader.snapshot(c)
        for indices in ([1,1],[1,0],[-1],[2],[False],[.5]):
            c=view();a=c['manifest']['annotations']['Mixer/Kids'];del a['countPath'];a['indices']=indices
            with self.subTest(indices=indices),self.assertRaisesRegex(ValueError,'index selection'):reader.snapshot(c)
        c=view();c['manifest']['annotations']['Mixer/Kids']['indices']=[0]
        with self.assertRaisesRegex(ValueError,'count reference'):reader.snapshot(c)
        c=view();a=c['manifest']['annotations']['Mixer/Kids'];del a['countPath'];a['indices']=[]
        self.assertFalse(any('/Kids[' in p for p in reader.snapshot(c)['values']))

    def test_empty_view_still_validates_annotations_below_unused_elements(self):
        c=view(0);c['manifest']['annotations']['Mixer/Kids[*]/Value']={'logicalType':'TIMESTAMP'}
        with self.assertRaisesRegex(ValueError,'logical/native'):reader.snapshot(c)
        c=view(0);c['manifest']['annotations']['Mixer/Kids[*]/Absent']={'logicalType':'ENUM'}
        with self.assertRaisesRegex(ValueError,'absent'):reader.snapshot(c)

    def test_minor_zero_cannot_smuggle_view_metadata(self):
        c=view();c['manifest']['schemaMinor']=0
        with self.assertRaisesRegex(ValueError,'unsupported annotation'):reader.snapshot(c)


class WireViewTests(unittest.TestCase):
    def record(self):
        r=fixture();r.update(SchemaMinor=1,PublicationStage=3)
        for row in r['Fields']:row.update(CountPath=string('',255),Indices=string('',255))
        self.rehash(r)
        return r

    def rehash(self,r):
        fields=[{k:wire.text(v) if isinstance(v,dict) else v for k,v in row.items()} for row in r['Fields']]
        digest=wire.content_hash(fields,wire.text(r['LegacyContentHash']),r['PublicationStage'],minor=r['SchemaMinor'])
        r.update(ContentHash=string(digest,80),ConfigRevision=wire.revision(digest))

    def test_view_fields_are_hashed_and_versioned_while_v60_remains_readable(self):
        self.assertEqual(wire.normalize(fixture())['schemaMinor'],0)
        r=self.record();self.assertEqual(wire.normalize(r)['schemaMinor'],1)
        row=r['Fields'][0];row.update(LowerBound=1,ElementCount=8,CountPath=string('Mixer/LiveCount',255))
        self.rehash(r);d=wire.normalize(r)
        self.assertEqual(d['annotations']['Mixer/Flag']['countPath'],'Mixer/LiveCount')
        row['CountPath']=string('Mixer/Other',255)
        with self.assertRaisesRegex(ValueError,'hash'):wire.normalize(r)

    def test_wire_selection_requires_sorted_unique_in_range_indices(self):
        for text in ('[2,0]','[0,0]','[8]','[-1]','[01]','0,','[true]','[1.0]','null'):
            r=self.record();r['Fields'][0].update(ElementCount=8,Indices=string(text,255));self.rehash(r)
            with self.subTest(text=text),self.assertRaises(ValueError):wire.normalize(r)
        r=self.record();r['Fields'][0].update(ElementCount=7,Indices=string('[0,3,6]',255));self.rehash(r)
        self.assertEqual(wire.normalize(r)['annotations']['Mixer/Flag']['indices'],[0,3,6])

    def test_physical_v61_loader_uses_extended_row_strides_and_string_widths(self):
        r=self.record();r['Fields'][0].update(ElementCount=8,LowerBound=1,CountPath=string('Mixer/LiveCount',255));self.rehash(r)
        templates,old=wire_fixture()
        fields=next(t for t in templates if t['handle']==0x210)
        fields.update(byteSize=828,members=fields['members']+[member('CountPath',0x8202,308),member('Indices',0x8202,568)])
        header=next(t for t in templates if t['handle']==0x220);header['byteSize']=1856
        raw=bytearray(1856);raw[:200]=old[:200]
        struct.pack_into('<ii',raw,8,1,3)
        def put(offset,value):
            data=bytes.fromhex(value['bytes']);struct.pack_into('<i',raw,offset,len(data));raw[offset+4:offset+4+len(data)]=data
        put(20,r['ContentHash']);struct.pack_into('<i',raw,104,r['ConfigRevision'])
        for i,row in enumerate(r['Fields']):
            at=200+i*828
            for key,offset in [('CanonicalPath',0),('LogicalType',260),('EffectiveAccess',280),('CountPath',308),('Indices',568)]:put(at+offset,row[key])
            struct.pack_into('<ii',raw,at+300,row['LowerBound'],row['ElementCount'])
        comm=SimpleNamespace(Read=lambda name:SimpleNamespace(Status='Success',Value=bytes(raw)))
        self.assertEqual(wire.read_manifest(comm,[dict(name='AnyName',handle=0x220,arrayRank=0)],templates),wire.normalize(r))


if __name__=='__main__':unittest.main()

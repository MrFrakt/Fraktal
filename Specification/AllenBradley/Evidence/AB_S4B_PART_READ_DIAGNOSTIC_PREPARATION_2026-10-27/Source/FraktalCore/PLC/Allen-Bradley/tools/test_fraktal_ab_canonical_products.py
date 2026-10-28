"""Generic V6.5 products: no station, tag-name pattern or Core-type dispatcher."""
from copy import deepcopy
import struct
from types import SimpleNamespace
import unittest

import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_manifest as wire
from test_fraktal_ab_canonical_reader import member
from test_fraktal_ab_canonical_type_manifest import capture as old_capture,record as old_record,row
from test_fraktal_ab_canonical_publication import string


def capture():
    c=old_capture();m=c['manifest'];m.update(schemaMinor=5,dataProducts=[
        dict(SourceSymbol='UnusualExport',CoreType='UnknownFutureCoreType',CanonicalRoot='OtherProduct/Tree')])
    c['templates'].append(dict(handle=0x790,name='ArbitraryRecord',byteSize=12,
        members=[member('Count',0xC3,0),member('Items',0x20C4,4,2)]))
    c['symbols'].append(dict(name='UnusualExport',handle=0x790,arrayRank=0))
    c['records'].append(dict(tag='UnusualExport',rawHex=struct.pack('<h2xii',1,11,22).hex()))
    m['typeAnnotations'].append(row('ArbitraryRecord','Items','',1,2,'Count'))
    return c


def record():
    r=old_record();r.update(SchemaMinor=5,DataProductsCount=1,DataProductsCapacity=1,
        DataProducts=[dict(SourceSymbol=string('UnusualExport',40),CoreType=string('UnknownFutureCoreType',40),CanonicalRoot=string('OtherProduct/Tree'))])
    a=[{k:wire.text(v) if isinstance(v,dict) else v for k,v in item.items()} for item in r['TypeAnnotations']]
    products=[{k:wire.text(v) for k,v in item.items()} for item in r['DataProducts']]
    digest=wire.content_hash(None,wire.text(r['LegacyContentHash']),2,minor=5,bindings=[],services=[],
                             type_annotations=a,path_exceptions=[],products=products)
    r.update(ContentHash=string(digest,80),ConfigRevision=wire.revision(digest));return r


class ProductReaderTests(unittest.TestCase):
    def test_product_discovered_only_by_binding_with_own_counts_and_native_types(self):
        doc=reader.snapshot(capture())
        self.assertEqual(doc['values']['OtherProduct/Tree/Count'],1)
        self.assertEqual(doc['types']['OtherProduct/Tree/Count'],'Int16')
        self.assertEqual(doc['values']['OtherProduct/Tree/Items[1]'],11)
        self.assertNotIn('OtherProduct/Tree/Items[2]',doc['values'])
        self.assertEqual(doc['moduleCount'],1)
        self.assertFalse(any(p.startswith('UnusualExport/') for p in doc['values']))

    def test_empty_live_view_still_requires_valid_array_schema(self):
        c=capture();c['records'][-1]['rawHex']=struct.pack('<h2xii',0,11,22).hex()
        self.assertFalse(any('/Items[' in p for p in reader.snapshot(c)['values']))
        c['manifest']['typeAnnotations'][-1]['ElementCount']=0
        with self.assertRaises(ValueError):reader.snapshot(c)

    def test_malformed_duplicate_overlap_missing_sample_and_module_alias_refused(self):
        mutations=[lambda c:c['manifest']['dataProducts'].append(deepcopy(c['manifest']['dataProducts'][0])),
                   lambda c:c['manifest']['dataProducts'][0].update(CanonicalRoot='Mixer/Other'),
                   lambda c:c['manifest']['dataProducts'][0].update(SourceSymbol='Mixer'),
                   lambda c:c['manifest']['dataProducts'][0].update(CanonicalRoot='Bad[*]/Tree'),
                   lambda c:c['records'].pop(),lambda c:c['symbols'][-1].update(arrayRank=1),
                   lambda c:c['manifest'].update(schemaMinor=4)]
        for mutate in mutations:
            c=capture();mutate(c)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):reader.snapshot(c)

    def test_product_counts_fail_closed_on_overflow(self):
        c=capture();c['records'][-1]['rawHex']=struct.pack('<h2xii',3,11,22).hex()
        with self.assertRaisesRegex(ValueError,'count exceeds'):reader.snapshot(c)

    def test_live_loader_reads_named_product_and_keeps_only_read_operations(self):
        c=capture();objects,sizes=reader.template_objects(c['templates']);calls=[]
        symbols=[SimpleNamespace(TagName=s['name'],DataTypeValue=s['handle'],Struct=1,Array=0) for s in c['symbols']]
        raw={r['tag']:bytes.fromhex(r['rawHex']) for r in c['records']}
        class Comm:
            UDT=objects
            def GetDeviceProperties(self):return SimpleNamespace(Status='Success',Value=SimpleNamespace(SerialNumber='0x12345678'))
            def GetTagList(self,*,allTags):return SimpleNamespace(Status='Success',Value=symbols)
            def Read(self,name):calls.append(name);return SimpleNamespace(Status='Success',Value=raw[name])
            def _cip_message(self,service,cls,handle,attrs):
                if (service,cls,attrs)!=(3,0x6c,[5]):raise AssertionError('unexpected service')
                return handle
        comm=Comm();comm.conn=SimpleNamespace(send=lambda h:(0,bytes(46)+struct.pack('<BBBBHHHI',0x83,0,0,0,1,5,0,sizes[h])))
        doc,recorded=reader.read_document(comm,lambda *args:c['manifest'],expect_serial='12345678')
        self.assertEqual(set(calls),{'Mixer','UnusualExport'});self.assertEqual(len(calls),2)
        self.assertEqual(doc,reader.snapshot(c));self.assertTrue(recorded['readOnly'])


class ProductWireTests(unittest.TestCase):
    def test_product_table_is_hashed_and_unknown_core_type_is_descriptive(self):
        r=record();m=wire.normalize(r)
        self.assertEqual(m['dataProducts'][0]['CoreType'],'UnknownFutureCoreType')
        r['DataProducts'][0]['CanonicalRoot']=string('Different/Tree')
        with self.assertRaisesRegex(ValueError,'hash'):wire.normalize(r)

    def test_bad_counts_and_duplicate_sources_and_roots_refused(self):
        mutations=[lambda r:r.update(DataProductsCount=0),lambda r:r.update(DataProductsCapacity=True),
                   lambda r:r['DataProducts'][0].update(SourceSymbol=string('Bad.Tag',40)),
                   lambda r:r['DataProducts'][0].update(CoreType=string('',40)),
                   lambda r:r.update(DataProductsCount=2,DataProductsCapacity=2,DataProducts=r['DataProducts']*2)]
        for mutate in mutations:
            r=record();mutate(r)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):wire.normalize(r)

    def test_zero_products_omits_the_array_and_keeps_exact_hash(self):
        r=record();r.update(DataProductsCount=0,DataProductsCapacity=0);r.pop('DataProducts')
        a=[{k:wire.text(v) if isinstance(v,dict) else v for k,v in item.items()} for item in r['TypeAnnotations']]
        digest=wire.content_hash(None,wire.text(r['LegacyContentHash']),2,minor=5,bindings=[],services=[],type_annotations=a,path_exceptions=[],products=[])
        r.update(ContentHash=string(digest,80),ConfigRevision=wire.revision(digest))
        self.assertEqual(wire.normalize(r)['dataProducts'],[])


if __name__=='__main__':unittest.main()

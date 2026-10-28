"""V6.4 type lookup, exact old/new snapshots, and malformed-metadata refusal."""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import struct
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_type_manifest as engineering
from test_fraktal_ab_canonical_reader import synthetic, member
from test_fraktal_ab_canonical_publication import string


def row(kind, member_name, logical='', lower=0, extent=0, count='', access=''):
    return dict(TypeName=kind, MemberName=member_name, LogicalType=logical,
                LowerBound=lower, ElementCount=extent, CountMember=count, EffectiveAccess=access)


def capture():
    c=synthetic()
    c['manifest'].pop('annotations')
    c['manifest'].update(schemaMinor=4,bindings=[],services=[],fragmentRevision=0,
        typeAnnotations=[row('Module','Duration','DURATION'),row('Module','Stamp','TIMESTAMP'),
                         row('Module','Bits','BOOL',0,3),row('Module','Kids','',1,2)],pathExceptions=[])
    c['coherenceBefore']=c['coherenceAfter']=['SYNTHETIC',1,0]
    return c


def record():
    m=capture()['manifest']
    annotations,exceptions=m['typeAnnotations'],m['pathExceptions']
    old='0123456789ABCDEF'
    digest=wire.content_hash(None,old,2,minor=4,bindings=[],services=[],
                             type_annotations=annotations,path_exceptions=exceptions)
    encode=lambda item:{k:string(v,255 if k in ('CanonicalPath','Indices') else
                                16 if k in ('LogicalType','EffectiveAccess') else 40)
                         if isinstance(v,str) else v for k,v in item.items()}
    return dict(Magic=wire.MAGIC,SchemaMajor=6,SchemaMinor=4,PublicationStage=2,Valid=True,Truncated=False,
                ContentHash=string(digest,80),LegacyContentHash=string(old,80),ConfigRevision=wire.revision(digest),
                TypeAnnotationsCount=len(annotations),TypeAnnotationsCapacity=len(annotations),
                TypeAnnotations=list(map(encode,annotations)),PathExceptionsCount=0,PathExceptionsCapacity=0,
                BindingsCount=0,BindingsCapacity=0,ServicesCount=0,ServicesCapacity=0,FragmentRevision=0)


class TypeReaderTests(unittest.TestCase):
    def test_identical_values_types_and_views(self):
        before,after=reader.snapshot(synthetic()),reader.snapshot(capture())
        self.assertEqual(before,after)

    def test_instance_inherits_template_facts_and_sparse_path_selection(self):
        c=capture();c['manifest']['typeAnnotations'].append(row('Child','Value','BITSTRING32'))
        doc=reader.snapshot(c)
        self.assertEqual(doc['values']['Mixer/Kids[2]/Value'],0xfffffff7)
        self.assertEqual(doc['types']['Mixer/Kids[1]/Value'],'UInt32')
        c['manifest']['pathExceptions']=[dict(CanonicalPath='Mixer/Kids',Indices='[1]')]
        doc=reader.snapshot(c)
        self.assertNotIn('Mixer/Kids[1]/Value',doc['values'])
        self.assertIn('Mixer/Kids[2]/Value',doc['values'])

    def test_sibling_count_changes_paths_without_changing_capacity(self):
        c=capture();c['manifest']['typeAnnotations'][-1]['CountMember']='End'
        raw=bytearray.fromhex(c['records'][0]['rawHex']);struct.pack_into('<i',raw,80,1)
        c['records'][0]['rawHex']=raw.hex()
        doc=reader.snapshot(c)
        self.assertIn('Mixer/Kids[1]/Value',doc['values'])
        self.assertNotIn('Mixer/Kids[2]/Value',doc['values'])
        struct.pack_into('<i',raw,80,3);c['records'][0]['rawHex']=raw.hex()
        with self.assertRaisesRegex(ValueError,'count exceeds'):reader.snapshot(c)

    def test_schema_validated_below_empty_view(self):
        c=capture();c['manifest']['pathExceptions']=[dict(CanonicalPath='Mixer/Kids',Indices='[]')]
        c['manifest']['typeAnnotations'].append(row('Child','Value','TIMESTAMP'))
        with self.assertRaisesRegex(ValueError,'logical/native'):reader.snapshot(c)

    def test_fragment_array_resolves_native_sibling_count(self):
        c=capture()
        c['manifest']['typeAnnotations'][-1]['CountMember']='End'
        kids=c['templates'][-1]['members'].pop(-2)
        c['templates'].append(dict(handle=0x702,name='Fragment',byteSize=16,
                                  members=[dict(kids,offset=0)]))
        raw=bytearray.fromhex(c['records'][0]['rawHex']);struct.pack_into('<i',raw,80,1)
        c['records'][0]['rawHex']=raw.hex()
        c['symbols'].append(dict(name='Extra',handle=0x702,arrayRank=0))
        c['records'].append(dict(tag='Extra',rawHex=raw[56:72].hex()))
        c['manifest']['bindings']=[dict(SourceSymbol='Extra',TargetRoot='Mixer')]
        c['manifest']['typeAnnotations'][-1]['TypeName']='Fragment'
        doc=reader.snapshot(c)
        self.assertEqual(doc['values']['Mixer/Kids[1]/Value'],7)
        self.assertNotIn('Mixer/Kids[2]/Value',doc['values'])

    def test_missing_nested_extent_is_refused_below_empty_view(self):
        c=capture();c['manifest']['pathExceptions']=[dict(CanonicalPath='Mixer/Kids',Indices='[]')]
        c['templates'][2]['members'][1]=member('Items',0x20C4,4,1)
        with self.assertRaisesRegex(ValueError,'logical extent'):reader.snapshot(c)

    def test_absent_and_duplicate_annotations_and_exceptions_refused(self):
        mutations=[lambda c:c['manifest']['typeAnnotations'].append(row('Missing','Value','ENUM')),
                   lambda c:c['manifest']['typeAnnotations'].append(deepcopy(c['manifest']['typeAnnotations'][0])),
                   lambda c:c['manifest']['typeAnnotations'].pop(),
                   lambda c:c['manifest']['typeAnnotations'][0].update(LogicalType='BOOL'),
                   lambda c:c['manifest']['pathExceptions'].append(dict(CanonicalPath='Mixer/Absent',Indices='[]')),
                   lambda c:c['manifest']['pathExceptions'].append(dict(CanonicalPath='Mixer/Kids',Indices='[2]')),
                   lambda c:c['manifest']['typeAnnotations'][-1].update(CountMember='Stamp'),
                   lambda c:c['manifest'].update(annotations={})]
        for mutate in mutations:
            c=capture();mutate(c)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):reader.snapshot(c)

    def test_nested_instances_use_their_own_count(self):
        c=capture()
        c['templates'][2].update(byteSize=12,members=[member('Used',0xC4,0),member('Items',0x20C4,4,2)])
        c['templates'][-1]['byteSize']=84;c['templates'][-1]['members'][-1]['offset']=80
        raw=bytearray.fromhex(c['records'][0]['rawHex'])[:84]
        struct.pack_into('<iiiiii',raw,56,1,11,12,2,21,22)
        c['records'][0]['rawHex']=raw.hex()
        c['manifest']['typeAnnotations'].append(row('Child','Items','',1,2,'Used'))
        doc=reader.snapshot(c)
        self.assertEqual(doc['values']['Mixer/Kids[1]/Items[1]'],11)
        self.assertNotIn('Mixer/Kids[1]/Items[2]',doc['values'])
        self.assertEqual(doc['values']['Mixer/Kids[2]/Items[2]'],22)


class TypeWireTests(unittest.TestCase):
    def test_hash_covers_both_tables_and_revision(self):
        r=record();m=wire.normalize(r)
        self.assertEqual(m['schemaMinor'],4);self.assertNotIn('annotations',m)
        r['TypeAnnotations'][0]['LogicalType']=string('ENUM',16)
        with self.assertRaisesRegex(ValueError,'hash'):wire.normalize(r)

    def test_sparse_exception_hash_is_not_optional(self):
        r=record();r.update(PathExceptionsCount=1,PathExceptionsCapacity=1,
            PathExceptions=[dict(CanonicalPath=string('Mixer/Kids'),Indices=string('[0]'))])
        with self.assertRaisesRegex(ValueError,'hash'):wire.normalize(r)

    def test_bad_counts_identifiers_defaults_and_types_refused(self):
        mutations=[lambda r:r.update(TypeAnnotationsCount=0),lambda r:r.update(TypeAnnotationsCapacity=True),
                   lambda r:r.update(BindingsCount=1),lambda r:r.update(PathExceptions=[]),
                   lambda r:r['TypeAnnotations'][0].update(TypeName=string('A'*41,41)),
                   lambda r:r['TypeAnnotations'][0].update(EffectiveAccess=string('None',16)),
                   lambda r:r['TypeAnnotations'][0].update(LogicalType=string('',16)),
                   lambda r:r['TypeAnnotations'][0].update(LowerBound=1),
                   lambda r:r['TypeAnnotations'][-1].update(CountMember=string('Mixer/Count',40))]
        for mutate in mutations:
            r=record();mutate(r)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):wire.normalize(r)

    def test_manifest_discovered_by_shape_with_arbitrary_symbol_name(self):
        r=record()
        templates=[dict(handle=1,members=[dict(name=k) for k in r])]
        comm=SimpleNamespace(Read=lambda name:SimpleNamespace(Status='Success',Value=b'wire'))
        with patch.object(reader,'decode_record',return_value=r):
            self.assertEqual(wire.read_manifest(comm,[dict(name='Unexpected',handle=1)],templates),wire.normalize(r))


class TypeEngineeringTests(unittest.TestCase):
    def test_every_stage_preserves_all_path_facts(self):
        for suffix in ('canonical','s3a','s3b','s3c','s3d','s3e','s3f','s3g','s3h','s3i'):
            app=importlib.import_module('fraktal_ab_genealogy_'+suffix+'_demo').application()
            current=replace(app,canonical_type_manifest=True)
            self.assertEqual(pub.validate(current),[])
            definitions=pub.schema(current)
            rows,exceptions=engineering.tables(current,definitions)
            annotations,paths=wire.type_tables(rows,exceptions)
            found={}
            def walk(kind,path):
                for m in definitions[kind]:
                    key=path+'/'+m.name
                    a=deepcopy(annotations.get((kind,m.name),{}))
                    expected=dict(LogicalType=a.get('logicalType',''),EffectiveAccess=a.get('effectiveAccess','Read Only'),
                                  LowerBound=a.get('lowerBound',0),ElementCount=a.get('elementCount',0))
                    if app.canonical_publication_stage>=3:
                        expected.update(CountPath=path+'/'+a['countMember'] if a.get('countMember') else '',
                            Indices=json.dumps(paths[key]['indices'],separators=(',',':')) if key in paths else '')
                    if m.count or m.kind not in definitions:found[key]=dict(CanonicalPath=key,**expected)
                    if m.kind in definitions:walk(m.kind,key+('[*]' if m.count else ''))
            walk(pub.root_type(current),app.name)
            if app.canonical_publication_stage>=5:
                from fraktal_ab_canonical_sequence import DEFINITIONS
                walk(DEFINITIONS,app.name)
            if app.canonical_publication_stage>=6:
                from fraktal_ab_canonical_alarms import METADATA
                walk(METADATA,app.name)
            self.assertEqual(found,{r['CanonicalPath']:r for r in pub.field_rows(app)},suffix)
            header=ET.fromstring(pub.tags(current)[1])
            self.assertIsNone(header.find(".//ArrayMember[@Name='Fields']"))
            plain=pub.manifest_values(current)
            def encode(value):
                if isinstance(value,str):return string(value)
                if isinstance(value,list):return [encode(v) for v in value]
                if isinstance(value,dict):return {k:encode(v) for k,v in value.items()}
                return value
            physical=encode(plain)
            for name in ('Bindings','Services','PathExceptions'):
                if not physical[name+'Count']:physical.pop(name,None)
            normalized=wire.normalize(physical)
            self.assertEqual(normalized['contentHash'],plain['ContentHash'])

    def test_opt_in_validation_and_non_sibling_count_refusal(self):
        from fraktal_ab_genealogy_s3i_demo import application
        app=replace(application(),canonical_type_manifest=True)
        self.assertTrue(pub.validate(replace(app,canonical_type_manifest=1)))
        self.assertTrue(pub.validate(replace(app,canonical_publication_stage=0)))
        definitions=pub.schema(app)
        root=pub.root_type(app)
        definitions[root]=tuple(replace(m,count_path='Other/Count') if m.count else m for m in definitions[root])
        with self.assertRaisesRegex(ValueError,'sibling'):engineering.tables(app,definitions)


if __name__=='__main__':unittest.main()

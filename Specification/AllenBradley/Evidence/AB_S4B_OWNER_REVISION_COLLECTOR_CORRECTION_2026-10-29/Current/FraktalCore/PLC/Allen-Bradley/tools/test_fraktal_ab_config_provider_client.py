"""Generic V6.3 negotiation, native widths and sequence-last failure behavior."""
from copy import deepcopy
from pathlib import Path
import ast
import struct
from types import SimpleNamespace as Reply
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_reader as reader
import fraktal_ab_config_provider_client as client
import fraktal_ab_config_provider_wire as protocol
from test_fraktal_ab_canonical_publication import fixture,string
from test_fraktal_ab_canonical_fragments import capture


def binding_capture():
    service=dict(Kind=1,Version=1,BuildRevision=11,RequestSymbol='ChosenRequest',RequestMember='Provider',ResponseSymbol='ChosenAnswer')
    fields=[dict(name=n,atomic=0xC4,info=count,array=1 if count else 0,struct=False)
            for n,count in protocol.layout()]
    return dict(manifest=dict(services=[service]),symbols=[dict(name='ChosenRequest',handle=1),dict(name='ChosenAnswer',handle=3)],
        templates=[dict(handle=1,members=[dict(name='Provider',handle=2,struct=True,array=0)]),
                   dict(handle=2,members=fields),dict(handle=3,members=[])])


def packet():return protocol.payload(sequence=1,request_sequence=3,login_sequence=9,build_revision=11,operation=30)


class ProviderClientTests(unittest.TestCase):
    def test_client_and_wire_have_no_engineering_or_source_tree_dependencies(self):
        forbidden={'fraktal_ab_station','fraktal_ab_declaration','fraktal_ab_generate','fraktal_ab_projection',
                   'fraktal_ab_canonical_unit_core','fraktal_ab_config_provider','fraktal_ab_canonical_publication'}
        for module in (client,protocol):
            tree=ast.parse(Path(module.__file__).read_text())
            names={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
            names.update(a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names)
            self.assertFalse(names&forbidden)

    def test_binding_uses_published_names_and_refuses_wrong_shapes(self):
        source=binding_capture();service,_=client.binding(source)
        self.assertEqual(service['RequestSymbol'],'ChosenRequest')
        for mutate in (lambda c:c['manifest']['services'][0].update(Version=2),
                       lambda c:c['templates'][1]['members'][0].update(atomic=0xC3),
                       lambda c:c['templates'][1]['members'][-1].update(info=1),
                       lambda c:c['templates'][0]['members'][0].update(array=1)):
            bad=deepcopy(source);mutate(bad)
            with self.assertRaises(ValueError):client.binding(bad)

    def test_plan_is_bounded_and_only_final_write_commits(self):
        service,_=client.binding(binding_capture());plan=client.write_plan(service,packet())
        self.assertEqual(plan[0],('ChosenRequest.Provider.Commit',0))
        self.assertEqual(plan[-1],('ChosenRequest.Provider.Commit',1))
        self.assertEqual([v for p,v in plan[:-1] if p.endswith('.Commit')],[0])
        self.assertTrue(all(not isinstance(v,list) or len(v)<=80 for _,v in plan))
        bad=packet();bad['Count']=True
        with self.assertRaises(ValueError):client.write_plan(service,bad)

    def test_interrupted_payload_and_wrong_serial_never_commit(self):
        source=binding_capture();source['manifest']['services'][0]['RequestMember']='Provider'
        state=dict(values={'Root/Access/LoginResultSequence':9})
        class Connection:
            def __init__(self,serial):self.serial=serial;self.writes=[]
            def GetDeviceProperties(self):return Reply(Status='Success',Value=Reply(SerialNumber=self.serial))
            def Read(self,name):return Reply(Status='Success',Value=b'raw')
            def Write(self,name,value):
                self.writes.append((name,value));return Reply(Status='Failure' if len(self.writes)==3 else 'Success')
        for serial in ('0x601fc87b','0x12345678'):
            comm=Connection(serial)
            with patch.object(client,'read_document',return_value=(state,source)),patch.object(client,'decode_record',return_value=dict(AckSequence=0)):
                with self.assertRaises(ValueError):client.publish(comm,expect_serial='601FC87B',root='Root',request_sequence=3,operation=30)
            self.assertFalse(any(p.endswith('.Commit') and v!=0 for p,v in comm.writes))
            if serial!='0x601fc87b':self.assertEqual(comm.writes,[])

    def test_utf8_widths_and_64bit_created_input_are_exact(self):
        header=dict(set='\u00e9',root='Root',model='',kind=1,schema=65535,records=64,configRev=0xffffffff,created=0xffffffff,clock=1)
        p=protocol.payload(sequence=1,request_sequence=3,login_sequence=9,build_revision=11,operation=30,headers=[header])
        self.assertEqual(p['TextLength'][0],2);self.assertEqual(p['TextBytes'][:2],[195,169])
        self.assertEqual(p['CreatedSeconds'][0],-1);self.assertEqual(p['ConfigRevision'][0],-1)
        for invalid in ('x'*81,'\x00','\ud800'):
            header['set']=invalid
            with self.assertRaises((ValueError,UnicodeError)):protocol.payload(sequence=1,request_sequence=3,login_sequence=9,build_revision=11,operation=30,headers=[header])


class ServiceManifestTests(unittest.TestCase):
    def record(self):
        row=fixture();row.update(SchemaMinor=3,PublicationStage=8,FragmentRevision=0,BindingsCount=1,BindingsCapacity=1,
            Bindings=[dict(SourceSymbol=string('Definitions',80),TargetRoot=string('Mixer',80))],
            ServicesCount=1,ServicesCapacity=1,Services=[dict(Kind=1,Version=1,BuildRevision=11,
                RequestSymbol=string('ChosenRequest',80),RequestMember=string('Provider',80),ResponseSymbol=string('ChosenAnswer',80))])
        for field in row['Fields']:field.update(CountPath=string(''),Indices=string(''))
        normalized_fields=[{k:wire.text(v) if isinstance(v,dict) else v for k,v in r.items()} for r in row['Fields']]
        bindings=[dict(SourceSymbol='Definitions',TargetRoot='Mixer')]
        services=[dict(Kind=1,Version=1,BuildRevision=11,RequestSymbol='ChosenRequest',RequestMember='Provider',ResponseSymbol='ChosenAnswer')]
        digest=wire.content_hash(normalized_fields,'0123456789ABCDEF',8,minor=3,bindings=bindings,services=services)
        row.update(ContentHash=string(digest,80),ConfigRevision=wire.revision(digest));return row

    def test_descriptor_is_hash_bound_and_unknown_version_fails_closed(self):
        record=self.record();self.assertEqual(wire.normalize(record)['services'][0]['BuildRevision'],11)
        for mutate in (lambda r:r['Services'][0].update(BuildRevision=12),
                       lambda r:r['Services'][0].update(Version=2),
                       lambda r:r['Services'].append(deepcopy(r['Services'][0]))):
            bad=deepcopy(record);mutate(bad)
            with self.assertRaises(ValueError):wire.normalize(bad)

    def test_uint16_annotation_checks_range_and_is_rejected_by_old_minor(self):
        for number in (0,32768,65535,-1,65536):
            c=capture();c['manifest']['schemaMinor']=3
            c['manifest']['annotations']['Mixer/End']=dict(logicalType='UINT16')
            raw=bytearray.fromhex(c['records'][0]['rawHex']);struct.pack_into('<i',raw,80,number);c['records'][0]['rawHex']=raw.hex()
            if 0<=number<=65535:
                doc=reader.snapshot(c);self.assertEqual(doc['values']['Mixer/End'],number);self.assertEqual(doc['types']['Mixer/End'],'UInt16')
            else:
                with self.assertRaises(ValueError):reader.snapshot(c)
        c['manifest']['schemaMinor']=2
        with self.assertRaises(ValueError):reader.snapshot(c)


if __name__=='__main__':unittest.main()

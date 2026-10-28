"""Generic V6.6 discovery/encoding with unrelated Symbol names and no values."""
from copy import deepcopy
import struct
import unittest
import fraktal_ab_command_binding as binding
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_manifest as wire
from test_fraktal_ab_canonical_reader import member
from test_fraktal_ab_canonical_type_manifest import capture as old_capture,row


def capture():
    c=old_capture();templates=c['templates'];root=next(t for t in templates if t['name']=='Module')
    req,reply,args,payload,status=0x910,0x911,0x912,0x913,0x914
    strings={};cursor=4;fields=[member('Kind',0xc4,0)]
    for i,(name,width) in enumerate(binding.WIDTHS.items()):
        handle=0x920+i;size=(width+7)//4*4;strings[name]=handle
        templates.append(dict(handle=handle,name='ArgString'+str(width)+'_'+str(i),byteSize=size,
            members=[member('LEN',0xc4,0),member('DATA',0x20c2,4,width)]))
        fields.append(member(name,0x8000|handle,cursor));cursor+=size
    fields += [member('IntValue',0xc4,cursor),member('BoolValue',0xc1,cursor+4,5),member('DurationMs',0xc4,cursor+8)]
    size=cursor+12
    templates.extend([
        dict(handle=req,name='LiveRequest',byteSize=4,members=[member('Sequence',0xc4,0)]),
        dict(handle=reply,name='LiveReply',byteSize=4,members=[member('AckSequence',0xc4,0)]),
        dict(handle=args,name='InputArguments',byteSize=size,members=fields),
        dict(handle=payload,name='WriteEnvelope',byteSize=size+12,structureHandle=0xb123,
            members=[member('SchemaVersion',0xc4,0),member('ManifestRevision',0xc4,4),member('StagedSequence',0xc4,8),member('Args',0x8000|args,12)]),
        dict(handle=status,name='InputStatus',byteSize=4,members=[member('CoreSerial',0xc4,0)])])
    root['members'] += [member('HmiRequest',0x8000|req,root['byteSize']),member('HmiResponse',0x8000|reply,root['byteSize']+4)]
    root['byteSize']+=8;c['records'][0]['rawHex']+='00'*8
    c['symbols'] += [dict(name='UnrelatedWriteObject',handle=payload,arrayRank=0),dict(name='OnlyTheCommit',atomic=0xc4,arrayRank=0),
        dict(name='StableAnswer',handle=reply,arrayRank=0),dict(name='ProtocolStatus',handle=status,arrayRank=0)]
    templates.append(dict(handle=0x915,name='PublishedKeys',byteSize=264,
        members=[member('NumericKey',0xc4,0),member('PortableKey',0x8000|strings['TargetPath'],4)]))
    c['symbols'].append(dict(name='KeyRows',handle=0x915,arrayRank=1))
    descriptor=dict(Version=1,RootSymbol='Mixer',PayloadSymbol='UnrelatedWriteObject',ArgumentsMember='Args',
        CommitSymbol='OnlyTheCommit',ResponseSymbol='StableAnswer',StatusSymbol='ProtocolStatus',ReadRole='CommandOnly',
        ConnectionBytes=4000,MaximumPayloadBytes=1024,CapabilitiesSymbol='',CapabilitiesCount=0,KeysSymbol='KeyRows',KeysCount=1)
    c['manifest'].update(schemaMinor=6,dataProducts=[],commandBindings=[descriptor],
        commandOperations=[dict(Kind=k,Supported=k!=0,RequiresSetStage=False,RefusalKey='' if k else 'empty') for k in range(39)])
    c['manifest']['typeAnnotations'] += [row('InputArguments','Kind','ENUM'),row('InputArguments','DurationMs','BITSTRING32')]
    return c


class CommandBindingTests(unittest.TestCase):
    def test_discovery_adds_nine_argument_schemas_without_reading_values(self):
        c=capture();doc=reader.snapshot(c)
        self.assertEqual(len(doc['commandArguments']),9)
        self.assertEqual(doc['commandArguments']['Mixer/HmiRequest/BoolValue']['nativeType'],'Boolean')
        self.assertEqual(doc['commandArguments']['Mixer/HmiRequest/Secret']['byteCapacity'],32)
        self.assertNotIn('Mixer/HmiRequest/Secret',doc['values'])
        self.assertIn('Mixer/HmiRequest/Sequence',doc['values'])

    def test_payload_records_are_refused_before_any_secret_bytes_are_decoded(self):
        for raw in ('','00'*784,b'uncommitted secret beyond LEN'.hex()):
            c=capture();c['records'].append(dict(tag='UnrelatedWriteObject',rawHex=raw))
            with self.assertRaisesRegex(ValueError,'command-only payload'):reader.snapshot(c)

    def test_real_bool_width_envelope_bounds_commit_and_operation_schema_are_enforced(self):
        mutations=[lambda c:next(t for t in c['templates'] if t['name']=='InputArguments')['members'][-2].update(code=0xc4,atomic=0xc4),
            lambda c:next(s for s in c['symbols'] if s['name']=='OnlyTheCommit').update(atomic=0xc1),
            lambda c:c['manifest']['commandOperations'].pop(),
            lambda c:c['manifest']['commandBindings'][0].update(ReadRole='Live'),
            lambda c:next(t for t in c['templates'] if t['name']=='WriteEnvelope').update(byteSize=2048),
            lambda c:next(t for t in c['templates'] if t['name']=='WriteEnvelope')['members'][-1].update(offset=0)]
        for mutate in mutations:
            c=capture();mutate(c)
            with self.assertRaises(ValueError):reader.snapshot(c)

    def test_encoder_uses_template_offsets_bool_bit_and_attribute_one_crc_without_station_maps(self):
        c=capture();d=c['manifest']['commandBindings'][0]
        arguments={n:False if n=='BoolValue' else '' if n in binding.WIDTHS else 0 for n in binding.ARGUMENTS}
        arguments.update(Kind=3,BoolValue=True,Secret='test-only-secret',DurationMs=0xffffffff,IntValue=-2147483648)
        plan=binding.write_plan(c,d,arguments,0xffffffff,connection_bytes=4000)
        self.assertLess(len(plan.payload_request)+110,4000)
        self.assertNotIn('test-only-secret',repr(plan));self.assertNotIn(plan.payload_request.hex(),repr(plan))
        path_bytes=plan.payload_request[1]*2;at=2+path_bytes
        self.assertEqual(struct.unpack_from('<HHH',plan.payload_request,at),(0x2a0,0xb123,1))
        raw=plan.payload_request[at+6:]
        decoded=reader.decode_record(raw,0x913,c['templates'])
        self.assertEqual(decoded['StagedSequence'],-1)
        self.assertEqual(decoded['Args']['BoolValue'],True)
        self.assertEqual(decoded['Args']['DurationMs'],-1)
        self.assertEqual(bytes.fromhex(decoded['Args']['Secret']['bytes']),b'test-only-secret')
        with self.assertRaises(ValueError):binding.write_plan(c,d,arguments,1,connection_bytes=500)
        arguments['BoolValue']=1
        with self.assertRaises(ValueError):binding.write_plan(c,d,arguments,1,connection_bytes=4000)

    def test_v66_command_metadata_hash_changes_when_a_write_endpoint_changes(self):
        c=capture();m=c['manifest'];d=m['commandBindings']
        first=wire.content_hash(None,'0123456789ABCDEF',13,minor=6,bindings=[],services=[],type_annotations=m['typeAnnotations'],
            path_exceptions=[],products=[],commands=d,operations=m['commandOperations'])
        d[0]['CommitSymbol']='DifferentCommit'
        second=wire.content_hash(None,'0123456789ABCDEF',13,minor=6,bindings=[],services=[],type_annotations=m['typeAnnotations'],
            path_exceptions=[],products=[],commands=d,operations=m['commandOperations'])
        self.assertNotEqual(first,second)


if __name__=='__main__':unittest.main()

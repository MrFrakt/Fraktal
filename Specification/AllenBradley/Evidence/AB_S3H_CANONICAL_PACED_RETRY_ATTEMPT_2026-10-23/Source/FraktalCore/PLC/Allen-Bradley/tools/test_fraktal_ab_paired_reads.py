"""MSP vectors preserve complete UDTs and refuse partial/malformed replies."""
import struct
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import fraktal_ab_paired_reads as batching


def reply(values):
    offset=2+2*len(values);offsets=[];segments=[]
    for value in values:
        offsets.append(offset)
        segment=b'\xcc\x00\x00\x00\xa0\x02\x34\x12'+value
        segments.append(segment);offset+=len(segment)
    return (0,b'\0'*46+b'\x8a\x00\x00\x00'+struct.pack('<H',len(values))+
            struct.pack('<'+'H'*len(offsets),*offsets)+b''.join(segments))


class PairedReadTests(unittest.TestCase):
    def comm(self,limit=500):
        def ioi(name,kind):
            data=name.encode('ascii')
            return bytes((0x91,len(data)))+data+(b'\0' if len(data)%2 else b'')
        def read_service(path,count):return bytes((0x4c,len(path)//2))+path+struct.pack('<H',count)
        return SimpleNamespace(ConnectionSize=limit,_build_ioi=ioi,_add_read_service=read_service,
                               _build_multi_service_header=lambda:b'\x0a\x02\x20\x02\x24\x01')

    def test_complete_first_dint_is_preserved(self):
        raw=struct.pack('<iii',1,123,-456)
        result=batching.decode_batch(reply([raw]),['Context'],{'Context':len(raw)})
        self.assertEqual(result['Context'].Value,raw)
        self.assertEqual(struct.unpack_from('<i',result['Context'].Value)[0],1)

    def test_batched_offsets_and_each_payload_are_independent(self):
        result=batching.decode_batch(reply([b'abcd',b'12345678']),['A','B'],{'A':4,'B':8})
        self.assertEqual((result['A'].Value,result['B'].Value),(b'abcd',b'12345678'))

    def test_partial_and_failed_services_never_pass(self):
        status,raw=reply([b'abcd'])
        variants=[(1,raw),(0,raw[:48]+b'\x06'+raw[49:]),(0,raw[:56]+b'\x06'+raw[57:])]
        for variant in variants:
            with self.subTest(variant=variant),self.assertRaises(ValueError):
                batching.decode_batch(variant,['A'],{'A':4})

    def test_bad_offsets_counts_and_sizes_are_refused(self):
        _,raw=reply([b'abcd'])
        for broken in (raw[:50]+b'\x02\x00'+raw[52:],raw[:52]+b'\x00\x00'+raw[54:],raw+b'x'):
            with self.subTest(broken=broken),self.assertRaises(ValueError):
                batching.decode_batch((0,broken),['A'],{'A':4})

    def test_response_budget_splits_batches_and_retains_fragmented_reader(self):
        read_plan=batching.plan(self.comm(),['A','B','Large','C'],{'A':300,'B':300,'Large':1000,'C':100})
        self.assertEqual([item['kind'] for item in read_plan],['batch','batch','single','batch'])
        for item in read_plan:
            if item['kind']=='batch':
                self.assertEqual(item['request'][:6],b'\x0a\x02\x20\x02\x24\x01')
                self.assertLess(len(item['request']),500)

    def test_acquisition_does_not_decode_inside_the_window(self):
        wire=reply([b'abcd'])
        comm=self.comm();comm.conn=SimpleNamespace(send=lambda request:wire)
        read_plan=batching.plan(comm,['A'],{'A':4})
        self.assertEqual(batching.acquire(comm,read_plan),[wire])
        self.assertEqual(batching.decode(read_plan,[wire],{'A':4})['A'].Value,b'abcd')

    def test_recorded_echo_batches_preserve_all_eight_complete_contexts(self):
        path=Path(__file__).parent/'fixtures/canonical/batch_transport_01.json.gz'
        capture=json.loads(gzip.decompress(path.read_bytes()))
        result={}
        for item,frame in zip(capture['plan'],capture['frames'],strict=True):
            result.update(batching.decode_batch((frame['status'],bytes.fromhex(frame['rawHex'])),item['tags'],capture['sizes']))
        self.assertEqual(len(result),8)
        for tag,answer in result.items():
            self.assertEqual(answer.Value.hex(),capture['decoded'][tag])
            self.assertEqual(struct.unpack_from('<i',answer.Value)[0],1)


if __name__=='__main__':unittest.main()

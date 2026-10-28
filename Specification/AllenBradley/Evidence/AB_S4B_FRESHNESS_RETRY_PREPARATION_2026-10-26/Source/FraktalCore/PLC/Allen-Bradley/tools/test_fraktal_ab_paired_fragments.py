"""Complete native UDT bytes after packet partitioning; no response repair."""
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import fraktal_ab_paired_fragments as fragments
import fraktal_ab_paired_reads as batching
import fraktal_ab_s2_equivalence as shared


def reply(data,status=6,kind=b'\xa0\x02\x34\x12'):
    return status,b'\0'*46+bytes((0xd2,0,status,0))+kind+data


class FragmentTests(unittest.TestCase):
    def comm(self):
        c=SimpleNamespace(ConnectionSize=500,_build_ioi=lambda tag,kind:b'\x91\x04Root',requests=[])
        def send(packet):
            c.requests.append(packet)
            offset=struct.unpack_from('<I',packet,len(packet)-4)[0]
            return reply(b'abcdefghij'[offset:offset+4],0 if offset+4>=10 else 6)
        c.conn=SimpleNamespace(send=send)
        c.Read=lambda name:SimpleNamespace(Status='Success',Value=b'o')
        return c

    def test_wire_offsets_and_out_of_order_reassembly_cover_exact_record(self):
        c=self.comm();items=fragments.packets(c,'Root',10)
        self.assertEqual([i['offset'] for i in items],[0,4,8])
        self.assertEqual([struct.unpack_from('<I',i['request'],len(i['request'])-4)[0] for i in items],[0,4,8])
        items=items[::2]+items[1::2]
        replies=batching.acquire(c,items)
        self.assertEqual(batching.decode(items,replies,{'Root':10})['Root'].Value,b'abcdefghij')

    def test_gaps_duplicates_wrong_type_and_premature_terminal_are_refused(self):
        c=self.comm();items=fragments.packets(c,'Root',10);replies=batching.acquire(c,items)
        for planned,received in ((items[:-1],replies[:-1]),(items+[items[0]],replies+[replies[0]]),
             (items,[reply(b'abcd',0),*replies[1:]]),
             (items,[reply(b'abcd',6,b'\xa0\x02\x99\x99'),*replies[1:]]),
             (items,[reply(b'abc'),*replies[1:]])):
            with self.assertRaises(ValueError):fragments.decode(planned,received,{'Root':10})

    def test_four_connections_partition_each_packet_exactly_once(self):
        c=self.comm();items=fragments.packets(c,'Root',10)
        with patch.object(fragments,'packets',return_value=items):
            plans=fragments.partition(c,['Root'],{'Root':1000},connections=4)
        self.assertEqual(len(plans),4)
        self.assertEqual(sorted(i['offset'] for p in plans for i in p),[0,4,8])
        for count in (1,9,True):
            with self.assertRaises(ValueError):fragments.partition(c,['Root'],{'Root':1000},connections=count)

    def test_socket_multiplex_closes_same_generation_before_any_payload_decode(self):
        import fraktal_ab_paired_socket_reads as sockets
        events=[];channels=[self.comm() for _ in range(4)];items=fragments.packets(channels[0],'Root',10)
        plans=([items[0]],[items[1]],[items[2]],[dict(kind='single',tags=['Other'])])
        original_decode=batching.decode
        generations=iter((6,8,8))
        def generation():events.append('generation');return next(generations)
        def acquire(owners,read_plans):
            self.assertEqual(owners,channels);events.append('wire')
            return [batching.acquire(c,p) for c,p in zip(owners,read_plans,strict=True)]
        def decode(plan,replies,sizes):
            self.assertEqual(events,['generation','generation','wire','generation'])
            return original_decode(plan,replies,sizes)
        with patch.object(fragments,'partition',return_value=plans),patch.object(sockets,'acquire',side_effect=acquire),patch.object(batching,'decode',side_effect=decode):
            result=shared._scan_reads(channels[0],['Root','Other'],generation,raw_sizes={'Root':10,'Other':1},secondary_comm=channels[1],secondary_tags=['Other'],fragment_large=True,extra_comms=channels[2:],socket_reads=True)
        self.assertEqual(result['readConnections'],4)
        self.assertEqual([r.Value for r in result['rawResponses']],[b'abcdefghij',b'o'])

    def test_four_owners_join_before_proof_closes_and_reassembly(self):
        events=[];channels=[self.comm() for n in range(4)];items=fragments.packets(channels[0],'Root',10)
        plans=([items[0]],[items[1]],[items[2]],[dict(kind='single',tags=['Other'])])
        original_acquire=batching.acquire;original_decode=batching.decode
        def generation():events.append('generation');return 8
        def acquire(comm,plan):events.append(('wire',next(i for i,c in enumerate(channels) if c is comm)));return original_acquire(comm,plan)
        def decode(plan,replies,sizes):
            self.assertEqual(events[0],events[-1],'generation')
            self.assertEqual(sorted(e[1] for e in events if isinstance(e,tuple)),[0,1,2,3])
            return original_decode(plan,replies,sizes)
        with patch.object(fragments,'partition',return_value=plans),patch.object(batching,'acquire',side_effect=acquire),patch.object(batching,'decode',side_effect=decode):
            result=shared._scan_reads(channels[0],['Root','Other'],generation,raw_sizes={'Root':10,'Other':1},secondary_comm=channels[1],secondary_tags=['Other'],fragment_large=True,extra_comms=channels[2:])
        self.assertEqual(result['readConnections'],4)
        self.assertEqual([r.Value for r in result['rawResponses']],[b'abcdefghij',b'o'])

    def test_every_fragment_acquires_before_closing_generation_and_decodes_after(self):
        events=[];c=self.comm();second=self.comm();items=fragments.packets(c,'Root',10)
        original_decode=batching.decode;original_acquire=batching.acquire
        def generation():events.append('generation');return 8
        def acquire(comm,plan):events.append('wire');return original_acquire(comm,plan)
        def decode(plan,replies,sizes):
            self.assertEqual(events[0],events[-1],'generation')
            self.assertEqual(events.count('wire'),2)
            return original_decode(plan,replies,sizes)
        cached=SimpleNamespace(Status='Success',Value=b'x')
        plans=(items[::2]+[dict(kind='single',tags=['Other'])],items[1::2])
        with patch.object(fragments,'partition',return_value=plans), \
             patch.object(batching,'acquire',side_effect=acquire),patch.object(batching,'decode',side_effect=decode):
            result=shared._scan_reads(c,['Root','Other','Metadata'],generation,raw_sizes={'Root':10,'Other':1,'Metadata':1},
                cached_records={'Metadata':cached},secondary_comm=second,secondary_tags=['Other'],fragment_large=True)
        self.assertTrue(result['sameStateVerified'])
        self.assertEqual(result['rawResponses'][0].Value,b'abcdefghij')


if __name__=='__main__':unittest.main()

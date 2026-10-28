"""The scan proof must close before inspecting, decoding or copying payloads."""
import unittest
from threading import Event
from unittest.mock import patch
from types import SimpleNamespace

from fraktal_ab_s2_equivalence import _scan_reads


class ReadWindowTests(unittest.TestCase):
    def test_payloads_are_not_inspected_inside_the_window(self):
        events=[]
        class Payload:
            @property
            def Value(self):
                raise AssertionError('payload inspected inside read window')
        class Comm:
            def Read(self,name):
                events.append(name)
                return Payload()
        def generation():
            events.append('generation')
            return 2
        result=_scan_reads(Comm(),('root','legacy'),generation)
        self.assertEqual(events,['generation','root','legacy','generation'])
        self.assertTrue(result['sameStateVerified'])
        self.assertEqual(len(result['rawResponses']),2)

    def test_rejected_scan_values_are_discarded(self):
        generations=iter((2,4,6,6))
        reads=iter(('old root','old legacy','new root','new legacy'))
        result=_scan_reads(SimpleNamespace(Read=lambda name:next(reads)),('root','legacy'),lambda:next(generations))
        self.assertEqual(result['rawResponses'],['new root','new legacy'])
        self.assertEqual(result['stateEvidence']['generation'],6)
        self.assertEqual(len(result['stateEvidence']['attempts']),2)

    def test_duplicate_or_empty_read_plan_is_refused_before_io(self):
        for tags in ((),('root','root')):
            with self.subTest(tags=tags),self.assertRaises(ValueError):
                _scan_reads(None,tags,None)

    def test_revision_cached_metadata_is_rejoined_after_live_scan_proof(self):
        metadata=SimpleNamespace(Status='Success',Value=b'defs')
        live=SimpleNamespace(Status='Success',Value=b'live')
        events=[]
        def generation():events.append('generation');return 8
        def plan(comm,tags,sizes):
            self.assertEqual(tags,['root']);return [{'kind':'single','tags':tags}]
        def acquire(comm,plan):events.append('live');return [live]
        def decode(plan,replies,sizes):
            self.assertEqual(events,['generation','live','generation'])
            return {'root':replies[0]}
        with patch('fraktal_ab_paired_reads.plan',side_effect=plan),patch('fraktal_ab_paired_reads.acquire',side_effect=acquire),patch('fraktal_ab_paired_reads.decode',side_effect=decode):
            result=_scan_reads(None,['definitions','root'],generation,raw_sizes={'definitions':4,'root':4},cached_records={'definitions':metadata})
        self.assertEqual(result['rawResponses'],[metadata,live])
        self.assertEqual(result['stateEvidence']['generation'],8)
        self.assertEqual(result['readPlan'],[{'kind':'single','tags':['root']}])

    def test_invalid_cache_is_refused_before_io(self):
        good=SimpleNamespace(Status='Success',Value=b'defs')
        for cache in ({'other':good},{'root':good,'definitions':good},{'definitions':SimpleNamespace(Status='Success',Value=b'short')},{'definitions':SimpleNamespace(Status='Failed',Value=b'defs')}):
            with self.subTest(cache=cache),self.assertRaises(ValueError):
                _scan_reads(None,['root','definitions'],None,raw_sizes={'root':4,'definitions':4},cached_records=cache)
        with self.assertRaises(ValueError):
            _scan_reads(None,['root','definitions'],None,cached_records={'definitions':good})

    def test_parallel_connections_are_both_inside_generation_window(self):
        primary=object();secondary=object();started=Event();events=[]
        def generation():events.append('generation');return 10
        def plan(comm,tags,sizes):return [dict(kind='batch',tags=tags)]
        def acquire(comm,plan):
            if comm is secondary:
                started.set();events.append('secondary')
            else:
                self.assertTrue(started.wait(1));events.append('primary')
            return [SimpleNamespace(Status='Success',Value=comm)]
        def decode(plan,replies,sizes):
            self.assertEqual(events[0],events[-1],'generation')
            self.assertCountEqual(events[1:-1],['primary','secondary'])
            return {item['tags'][0]:reply for item,reply in zip(plan,replies,strict=True)}
        with patch('fraktal_ab_paired_reads.plan',side_effect=plan),patch('fraktal_ab_paired_reads.acquire',side_effect=acquire),patch('fraktal_ab_paired_reads.decode',side_effect=decode):
            result=_scan_reads(primary,['legacy','root'],generation,raw_sizes={'legacy':4,'root':4},secondary_comm=secondary,secondary_tags=['legacy'])
        self.assertEqual([r.Value for r in result['rawResponses']],[secondary,primary])
        self.assertEqual(result['readConnections'],2)
        self.assertTrue(result['sameStateVerified'])

    def test_invalid_secondary_partition_is_refused_before_io(self):
        comm=object()
        for secondary,tags in ((None,['legacy']),(comm,['legacy']),(object(),['other']),(object(),['root','legacy'])):
            with self.subTest(tags=tags),self.assertRaises(ValueError):
                _scan_reads(comm,['root','legacy'],None,raw_sizes={'root':4,'legacy':4},secondary_comm=secondary,secondary_tags=tags)


if __name__=='__main__':unittest.main()

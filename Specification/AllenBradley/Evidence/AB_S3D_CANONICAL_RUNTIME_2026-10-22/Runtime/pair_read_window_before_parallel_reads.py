"""The scan proof must close before inspecting, decoding or copying payloads."""
import unittest
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


if __name__=='__main__':unittest.main()

"""The scan proof must close before inspecting, decoding or copying payloads."""
import unittest
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


if __name__=='__main__':unittest.main()

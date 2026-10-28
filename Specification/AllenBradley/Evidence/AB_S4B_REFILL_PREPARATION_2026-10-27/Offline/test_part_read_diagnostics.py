from pathlib import Path
import itertools,json,struct,sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_part as part
from part_read_diagnostics import trace_part_reads


class PartReadDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'trace.jsonl'
        self.app=SimpleNamespace(name='Fixture')
        self.clock=itertools.count(step=10).__next__

    def records(self):return [json.loads(line) for line in self.path.read_text().splitlines()]

    def test_original_reader_controls_calls_arguments_and_return_value(self):
        sentinel=object()
        comm=SimpleNamespace(Read=Mock(return_value=SimpleNamespace(Status='Success',Value=struct.pack('<2i',2,8)+b'PRIVATE_PART_UID')))
        def original(proxy,app,attempts=3):
            self.assertIs(app,self.app);self.assertEqual(attempts,2)
            for _ in range(3):proxy.Read(part.tag(app))
            return sentinel
        with patch.object(part,'read',original):
            with trace_part_reads(self.path,clock=self.clock):
                self.assertIs(part.read(comm,self.app,2),sentinel)
            self.assertIs(part.read,original)
        self.assertEqual(comm.Read.call_count,3)
        record=self.records()[0]
        self.assertTrue(record['passed']);self.assertEqual(record['attemptBudget'],2)
        self.assertEqual([r['phase'] for r in record['reads']],['before','body','after'])
        self.assertTrue(all(r['schemaVersion']==2 and r['dataRevision']==8 and r['elapsedUs']==10 for r in record['reads']))
        self.assertNotIn('PRIVATE',self.path.read_text())

    def test_all_original_attempts_recorded_and_identical_refusal_rethrown(self):
        refusal=part.PartBad('unchanged refusal')
        revisions=[2,4,4,6,8,8,10,12,12]
        comm=SimpleNamespace(Read=Mock(side_effect=[SimpleNamespace(Status='Success',Value=struct.pack('<2i',2,r)) for r in revisions]))
        def original(proxy,app,attempts=3):
            for _ in range(attempts*3):proxy.Read(part.tag(app))
            raise refusal
        with patch.object(part,'read',original):
            with self.assertRaises(part.PartBad) as caught:
                with trace_part_reads(self.path,clock=self.clock):part.read(comm,self.app)
            self.assertIs(caught.exception,refusal);self.assertIs(part.read,original)
        self.assertEqual(comm.Read.call_count,9)
        record=self.records()[0]
        self.assertFalse(record['passed']);self.assertEqual(record['errorType'],'PartBad')
        self.assertEqual([r['dataRevision'] for r in record['reads']],revisions)
        self.assertEqual([r['attempt'] for r in record['reads']],[1]*3+[2]*3+[3]*3)

    def test_network_exception_is_unchanged_and_recorded(self):
        refusal=TimeoutError('unchanged network refusal')
        comm=SimpleNamespace(Read=Mock(side_effect=refusal))
        def original(proxy,app,attempts=3):return proxy.Read(part.tag(app))
        with patch.object(part,'read',original):
            with self.assertRaises(TimeoutError) as caught:
                with trace_part_reads(self.path,clock=self.clock):part.read(comm,self.app)
            self.assertIs(caught.exception,refusal);self.assertIs(part.read,original)
        self.assertEqual(self.records()[0]['reads'][0]['readErrorType'],'TimeoutError')

    def test_existing_evidence_refused_before_installation_or_reads(self):
        self.path.write_text('preserve')
        original=part.read
        with self.assertRaises(FileExistsError):
            with trace_part_reads(self.path):self.fail('must refuse')
        self.assertIs(part.read,original);self.assertEqual(self.path.read_text(),'preserve')

    def test_failed_and_short_replies_forwarded_without_payload_disclosure(self):
        replies=[SimpleNamespace(Status='Failure',Value=b'secret'),SimpleNamespace(Status='Success',Value=b'1234')]
        comm=SimpleNamespace(Read=Mock(side_effect=replies))
        def original(proxy,app,attempts=3):
            return [proxy.Read(part.tag(app)),proxy.Read(part.tag(app))]
        with patch.object(part,'read',original):
            with trace_part_reads(self.path,clock=self.clock):self.assertEqual(part.read(comm,self.app),replies)
        self.assertNotIn('schemaVersion',self.records()[0]['reads'][0])
        self.assertNotIn('dataRevision',self.records()[0]['reads'][1])
        self.assertNotIn('secret',self.path.read_text())

    def test_each_call_has_its_own_attempt_numbering(self):
        comm=SimpleNamespace(Read=Mock(return_value=SimpleNamespace(Status='Success',Value=struct.pack('<2i',2,12))))
        def original(proxy,app,attempts=3):return proxy.Read(part.tag(app))
        with patch.object(part,'read',original):
            with trace_part_reads(self.path,clock=self.clock):
                part.read(comm,self.app);part.read(comm,self.app)
        self.assertEqual([r['call'] for r in self.records()],[1,2])
        self.assertEqual([r['reads'][0]['attempt'] for r in self.records()],[1,1])


if __name__=='__main__':unittest.main()

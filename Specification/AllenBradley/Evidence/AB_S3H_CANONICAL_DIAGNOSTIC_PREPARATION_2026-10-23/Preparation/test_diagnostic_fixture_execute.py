from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import gzip,json,unittest
from unittest.mock import patch
import diagnostic_fixture_execute as diagnostic


class DiagnosticTests(unittest.TestCase):
    def evidence(self,path):return json.loads(gzip.decompress(path.read_bytes()))

    def test_current_exact_image_diagnostic_authorization_is_required_before_fixture(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'canonical.sha256').write_text('PIN')
            (root/'authorization.json').write_text(json.dumps(dict(CurrentOwnerApproved=False,
                ReadTimingDiagnosticsAuthorized=False,Serial='601FC87B',CanonicalSha256='PIN',
                FaultClearAuthorized=False,ClockSetAuthorized=False)))
            with patch.object(diagnostic,'__file__',str(root/'wrapper.py')),patch.object(diagnostic.fixture,'main') as fixture:
                with self.assertRaisesRegex(SystemExit,'current exact-image diagnostic'):diagnostic.main()
            fixture.assert_not_called()

    def test_success_keeps_proof_result_and_does_not_read_tasks(self):
        comm=SimpleNamespace(Read=lambda tags:self.fail('no task reads on success'))
        replies=[[(6,b'raw')]];plan=[[dict(kind='fragment',request=b'read',tags=['Root'])]]
        pair=dict(sameStateVerified=True,stateEvidence=dict(generation=2,attempts=[dict(before=2,after=2)]))
        def scan(c,tags,generation,**options):
            self.assertEqual(options,dict(socket_reads=True));self.assertEqual(generation(),2)
            self.assertEqual(diagnostic.sockets.acquire([c],plan),replies)
            self.assertEqual(generation(),2);return pair
        with TemporaryDirectory() as folder,patch.object(diagnostic.sockets,'acquire',return_value=replies) as acquire:
            target=Path(folder)/'pass.json.gz'
            actual=diagnostic.instrument(scan,comm,['Root'],lambda:2,destination=target,socket_reads=True)
            self.assertIs(actual,pair);self.assertIs(diagnostic.sockets.acquire,acquire)
            evidence=self.evidence(target);self.assertTrue(evidence['acquisitionPassed'])
            self.assertEqual(len(evidence['generationPolls']),2);self.assertEqual(len(evidence['readWindows']),1)
            self.assertEqual(evidence['lastAttemptFrames'][0]['rawHex'],b'raw'.hex())

    def test_failure_preserves_original_error_and_100_poll_history_with_read_only_task_sample(self):
        error=ValueError('no completed PLC scan held across the paired read window')
        error.attempts=[dict(before=2,waitingFreshScan=True)]*100
        calls=[]
        def read(tags):
            calls.append(tags);return [SimpleNamespace(TagName=n,Status='Success',Value=123) for n in tags]
        comm=SimpleNamespace(Read=read)
        def scan(c,tags,generation,**options):
            for _ in range(100):generation()
            raise error
        original=diagnostic.sockets.acquire
        with TemporaryDirectory() as folder:
            target=Path(folder)/'fail.json.gz'
            with self.assertRaises(ValueError) as caught:
                diagnostic.instrument(scan,comm,['Root'],lambda:2,destination=target)
            self.assertIs(caught.exception,error);self.assertIs(diagnostic.sockets.acquire,original)
            evidence=self.evidence(target)
            self.assertEqual(evidence['attempts'],error.attempts);self.assertEqual(len(evidence['generationPolls']),100)
            self.assertEqual(calls,[list(diagnostic.TASK_TAGS)]);self.assertEqual(len(evidence['taskAfterFailure']),8)
            self.assertFalse(evidence['acquisitionPassed']);self.assertFalse(evidence['acceptanceChanged'])

    def test_failed_task_read_never_masks_original_failure(self):
        error=ValueError('original proof failure')
        def read(tags):raise OSError('diagnostic read unavailable')
        def scan(*args,**options):raise error
        with TemporaryDirectory() as folder:
            target=Path(folder)/'fail.json.gz'
            with self.assertRaises(ValueError) as caught:
                diagnostic.instrument(scan,SimpleNamespace(Read=read),['Root'],lambda:2,destination=target)
            self.assertIs(caught.exception,error)
            self.assertIn('diagnostic read unavailable',self.evidence(target)['taskReadError'])


if __name__=='__main__':unittest.main()

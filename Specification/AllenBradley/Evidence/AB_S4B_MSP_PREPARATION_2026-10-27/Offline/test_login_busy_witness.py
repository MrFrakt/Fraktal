"""A short-lived busy state must be proved before expensive full discovery."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import login_busy_witness as witness


def reply(value,status='Success'):
    return SimpleNamespace(Value=value,Status=status)


class ReadOnly:
    def __init__(self,generations=None,bodies=None):
        self.generations=iter(generations or [2,4,6,6])
        self.bodies=iter(bodies or [(False,0),(True,1)])
        self.events=[]

    def Read(self,path):
        self.events.append(('read',path))
        if isinstance(path,list):
            self._assert_paths(path)
            values=next(self.bodies)
            return [v if hasattr(v,'Status') else reply(v) for v in values]
        if path!='FRK_Press_CanonicalGeneration':
            raise AssertionError('unexpected read '+path)
        return reply(next(self.generations))

    def _assert_paths(self,paths):
        assert paths==['Press.Access.LoginBusy','FRK_Press_AccessState.LoginBusy'],paths

    def Write(self,*args):
        raise AssertionError('the witness cannot write')


class BusyWitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)/'witness.json'
        self.app=SimpleNamespace(name='Press')
        self.seed=dict(manifest=dict(contentHash='pinned'))
        patcher=patch.object(witness,'snapshot',return_value=dict(types={'Press/Access/LoginBusy':'Boolean'}))
        patcher.start();self.addCleanup(patcher.stop)
        patcher=patch('fraktal_ab_canonical_equivalence.time.sleep')
        patcher.start();self.addCleanup(patcher.stop)

    def probe(self,comm=None):
        return witness.BusyWitness(comm or ReadOnly(),self.app,self.seed)

    def test_true_pair_requires_equal_even_scan_and_keeps_raw_values_types(self):
        report=self.probe().capture(self.output)
        self.assertTrue(report['passed'])
        self.assertFalse(report['fullComparison'])
        self.assertEqual(report['pair']['stateEvidence']['generation'],6)
        self.assertEqual([r['value'] for r in report['pair']['rawReads']],[True,1])
        self.assertEqual(report['pair']['canonical']['types'],{'Press/Access/LoginBusy':'Boolean'})
        self.assertEqual(json.loads(self.output.read_bytes()),report)

    def test_completed_refusal_cannot_pass_busy_requirement(self):
        with self.assertRaisesRegex(ValueError,'not observed'):
            self.probe(ReadOnly(bodies=[(False,0),(False,0)])).capture(self.output)
        self.assertFalse(json.loads(self.output.read_bytes())['passed'])

    def test_disagreement_cannot_pass_even_if_canonical_is_busy(self):
        with self.assertRaisesRegex(ValueError,'not observed'):
            self.probe(ReadOnly(bodies=[(False,0),(True,0)])).capture(self.output)
        report=json.loads(self.output.read_bytes())
        self.assertFalse(report['valueEquivalent'])

    def test_changed_scan_discards_body_and_accepts_only_later_guarded_pair(self):
        comm=ReadOnly([2,4,6,8,10,10],[(False,0),(True,0),(True,1)])
        report=self.probe(comm).capture(self.output)
        proof=report['pair']['stateEvidence']
        self.assertEqual(proof['generation'],10)
        self.assertEqual(proof['attempts'][-2],dict(before=6,after=8))

    def test_odd_counter_never_supplies_accepted_body(self):
        comm=ReadOnly([2,3,4,4])
        report=self.probe(comm).capture(self.output)
        self.assertEqual(report['pair']['stateEvidence']['generation'],4)
        self.assertEqual(sum(isinstance(p,list) for _,p in comm.events),2)

    def test_frozen_counter_exhausts_original_poll_budget_without_body_or_writes(self):
        comm=ReadOnly([2]+[4]*100)
        with self.assertRaisesRegex(ValueError,'no completed PLC scan'):
            self.probe(comm).capture(self.output)
        report=json.loads(self.output.read_bytes())
        self.assertEqual(len(report['attempts']),100)
        self.assertEqual(sum(isinstance(p,list) for _,p in comm.events),1)

    def test_invalid_or_uninitialized_generation_is_refused_before_writes(self):
        for generation in (0,True,None,2147483647):
            with self.subTest(generation=generation),self.assertRaisesRegex(ValueError,'initialized'):
                self.probe(ReadOnly([generation]))

    def test_wrong_published_type_refuses_before_any_read(self):
        comm=ReadOnly()
        with patch.object(witness,'snapshot',return_value=dict(types={'Press/Access/LoginBusy':'Int32'})), \
             self.assertRaisesRegex(ValueError,'published Boolean'):
            self.probe(comm)
        self.assertFalse(comm.events)

    def test_bad_reply_and_invalid_native_values_are_preserved_as_failure(self):
        for index,body in enumerate([(True,2),('true',1),(True,True),(reply(True,'Refused'),1)]):
            output=self.output.with_name(f'bad_{index}.json')
            with self.subTest(body=body),self.assertRaises(ValueError):
                self.probe(ReadOnly(bodies=[(False,0),body])).capture(output)
            self.assertFalse(json.loads(output.read_bytes())['passed'])

    def test_existing_output_is_refused_before_more_reads(self):
        comm=ReadOnly();probe=self.probe(comm)
        self.output.write_text('keep')
        before=len(comm.events)
        with self.assertRaisesRegex(ValueError,'existing'):
            probe.capture(self.output)
        self.assertEqual(len(comm.events),before)
        self.assertEqual(self.output.read_text(),'keep')

    def make_run(self,fail_full=False):
        comm=ReadOnly();events=[];app=self.app;seed=self.seed
        class Parent:
            def __init__(self):
                self.comm,self.app,self.provider_capture=comm,app,seed
                self.evidence={}
            def access_pair(self,phase):
                events.append(phase)
                if fail_full:raise ValueError('full comparison failed')
                return dict(pair=dict(canonical=dict(values={'Press/Access/LoginBusy':False})))
        cls=witness.with_busy_witness(Parent,self.output.with_name('fixture.json'))
        return cls(),events

    def test_short_witness_precedes_full_capture_which_may_have_completed(self):
        run,events=self.make_run()
        result=run.access_pair('login_busy')
        self.assertTrue(result['pair']['canonical']['values']['Press/Access/LoginBusy'])
        self.assertEqual(events,['after_login_busy_witness'])
        self.assertTrue(run.evidence['loginBusyWitness']['sameScanVerified'])
        self.assertFalse(run.evidence['loginBusyWitness']['fullComparison'])

    def test_full_comparison_failure_still_propagates_after_successful_witness(self):
        run,events=self.make_run(fail_full=True)
        with self.assertRaisesRegex(ValueError,'full comparison failed'):
            run.access_pair('login_busy')
        self.assertEqual(events,['after_login_busy_witness'])

    def test_other_access_phases_are_forwarded_without_a_witness(self):
        run,events=self.make_run()
        run.access_pair('logged_out')
        self.assertEqual(events,['logged_out'])
        self.assertNotIn('loginBusyWitness',run.evidence)

    def test_original_access_case_requires_short_proof_and_retains_later_full_pair(self):
        import fraktal_ab_s3e_fixture_execute as fixture
        comm=ReadOnly();app=self.app;seed=self.seed;events=[]
        class Parent:
            def __init__(self):
                self.comm,self.app,self.provider_capture=comm,app,seed
                self.evidence={}
            def command(self,kind,**arguments):
                events.append(('command',kind))
                return dict(accepted=True)
            def check(self,condition,message):
                if not condition:raise ValueError(message)
        with patch.object(fixture.previous,'paired_run',return_value=Parent):
            inherited=fixture.paired_run(self.output.with_name('fixture.json'))
        run=witness.with_busy_witness(inherited,self.output.with_name('fixture.json'))()
        full=dict(pair=dict(canonical=dict(values={'Press/Access/LoginBusy':False})))
        def capture(*args,**kwargs):
            events.append(('full',kwargs['metadata']['phase']))
            return full
        with patch.object(fixture.capture,'capture_pair',side_effect=capture):
            run.command(fixture.mailbox.LOGIN,User='non-secret-test-user',Secret='never-record')
        self.assertEqual(events,[('command',fixture.mailbox.LOGIN),('full','after_login_busy_witness')])
        self.assertFalse(full['pair']['canonical']['values']['Press/Access/LoginBusy'])
        raw=(self.output.with_name('fixture_login_busy_witness.json')).read_text()
        self.assertNotIn('never-record',raw)
        self.assertNotIn('non-secret-test-user',raw)


if __name__=='__main__':unittest.main()

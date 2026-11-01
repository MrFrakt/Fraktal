"""No controller I/O: current authorization, ownership and P5 failure isolation."""
from pathlib import Path
import copy,json,os,subprocess,sys,tempfile,unittest,uuid
from unittest import mock
from s5_session import authorize,FLAGS
from session_ownership import owns_session
from readonly_stages import execute_readonly_stages
D=Path(__file__).parent

class Workflow(unittest.TestCase):
    def valid(self):
        value=json.loads((D/'authorization.template.json').read_bytes())
        value.update(CurrentOwnerApproved=True,OwnerInstruction='test-only valid authorization object; not saved or used')
        value.update({key:True for key in FLAGS})
        return value
    def test_valid_object_validation_only(self):authorize(self.valid())
    def test_every_sdk_static_input_exists_before_any_controller_call(self):
        from artifact_readiness import validate
        result=validate(D)
        self.assertTrue(result['passed'])
        self.assertIn('canonical_prepared_compare.json',result['staticSdkInputs'])
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);(directory/'session').mkdir()
            (directory/'session/Program.cs').write_bytes((D/'session/Program.cs').read_bytes())
            with self.assertRaisesRegex(ValueError,'canonical_prepared_compare'):
                validate(directory)
    def test_capacity_confirmation_is_derived_from_current_image(self):
        from capacity_readiness import validate,FIELDS
        measurement=json.loads((D/'capacity_review.json').read_bytes())
        template=json.loads((D/'authorization.template.json').read_bytes())
        canonical=(D/'canonical.sha256').read_text().strip()
        self.assertTrue(validate(template,measurement,canonical))
        for field in FIELDS:
            bad=copy.deepcopy(template);bad['OwnerCapacityConfirmed'][field]+=1
            with self.assertRaises(ValueError):validate(bad,measurement,canonical)
    def test_every_required_scope_refuses_when_missing(self):
        for flag in FLAGS:
            with self.subTest(flag=flag):
                value=self.valid();value[flag]=False
                with self.assertRaises(ValueError):authorize(value)
    def test_identity_image_source_and_owner_are_bound(self):
        for key,value in [('Serial','00000000'),('CanonicalSha256','0'*64),('SourceSha256','0'*64),
                          ('CurrentOwnerApproved',False),('OwnerInstruction','')]:
            with self.subTest(key=key):
                bad=self.valid();bad[key]=value
                with self.assertRaises(ValueError):authorize(bad)
    def test_excluded_changes_never_authorize(self):
        for key in ['FaultClearAuthorized','ClockSetAuthorized','PowerOperationsAuthorized','VendorStateEditsAuthorized']:
            value=self.valid();value[key]=True
            with self.assertRaises(ValueError):authorize(value)
    def test_cleanup_needs_exact_owned_login(self):
        status={'Access/LoginBusy':False,'Access/CurrentLevel':4,'Access/CurrentUser':'fixture','Access/LoginResultSequence':19}
        proof=dict(correlatedByRepository=True,level=4,user='fixture',loginResultSequence=19)
        self.assertTrue(owns_session(status,[proof]))
        self.assertFalse(owns_session(status,[]))
        for key,value in [('correlatedByRepository',False),('level',3),('user','other'),('loginResultSequence',18)]:
            bad={**proof,key:value};self.assertFalse(owns_session(status,[bad]))
        self.assertFalse(owns_session({**status,'Access/LoginBusy':True},[proof]))
    def test_p5_runs_all_independent_reads_after_each_failure(self):
        for failed in ['configuration_comparison','idle_equivalence','generic_acquire','candidate_timing']:
            seen=[]
            def run(label,*args):
                seen.append(label)
                if label==failed:raise RuntimeError('fixed offline failure')
            errors=execute_readonly_stages(run,python='python',directory=D,tools=D,timing=D/'timing.py')
            self.assertEqual(seen,['configuration_comparison','idle_equivalence','generic_acquire','candidate_timing'])
            self.assertEqual([e['stage'] for e in errors],[failed])
    def test_existing_s4b_evidence_cannot_pass_s5_gateway_gate(self):
        from check_native_read_gates import evaluate
        value=evaluate(Path('C:/work/fraktal-ab-s4b-owner-20261029/session_03'))
        self.assertFalse(value['passed'])
        self.assertFalse(value['gates']['C1_C11_C13']['passed'])
        self.assertTrue(value['gates']['native_scan']['passed'])
    def test_writer_failure_still_collects_reads_and_completes_rollback(self):
        import s5_session as session
        class Sampler:
            def wait(self,timeout=None):return 0
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);seen=[]
            (directory/'authorization.json').write_text(json.dumps(self.valid()))
            (directory/'canonical.sha256').write_text(session.PIN)
            (directory/'source_bindings.json').write_text(json.dumps(dict(gatesPassed=True,sha256={})))
            def fake_run(arguments,**kwargs):
                label=arguments[2];seen.append(label)
                if label=='deploy':
                    (directory/'deploy_attempt.json').write_text('{}')
                    (directory/'candidate_run_requested.json').write_text('{}')
                if label=='gateway_qualification':raise subprocess.CalledProcessError(1,arguments)
            print('Orchestration injection uses mocks only; no controller or process is opened.')
            with mock.patch.object(session,'D',directory),mock.patch.object(session,'dumps',return_value=[]),\
                 mock.patch('artifact_readiness.validate',return_value=dict(passed=True)),\
                 mock.patch.object(session,'digest',side_effect=lambda p:session.SOURCE if str(p).endswith('.L5X') else session.PIN),\
                 mock.patch.object(session,'wait_for_ready'),mock.patch.object(session.subprocess,'run',side_effect=fake_run),\
                 mock.patch.object(session.subprocess,'Popen',return_value=Sampler()),mock.patch.dict(os.environ,{},clear=False):
                self.assertEqual(session.main(),1)
            result=json.loads((directory/'session_result.json').read_bytes())
            self.assertTrue(result['genealogyRestored'])
            self.assertIsNone(result['rollbackError'])
            self.assertFalse(result['passed'])
            self.assertIn('gateway_qualification',result['candidateError'])
            for label in ['configuration_comparison','idle_equivalence','generic_acquire','candidate_timing',
                          'cleanup_owned_session','restore_genealogy','baseline_regressions','preflight_final']:
                self.assertIn(label,seen)
    def test_compiled_sdk_false_approval_stops_before_any_controller_call(self):
        assert json.loads((D/'authorization.json').read_bytes())['CurrentOwnerApproved'] is False
        sdk=D/'session/bin/Debug/net8.0/win-x86/S5Session.exe'
        result=subprocess.run([str(sdk),'backup'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        with (D/f'sdk_refused_false_approval_{uuid.uuid4().hex}.log').open('x',encoding='utf-8') as stream:stream.write(result.stdout)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Current target/artifact owner authorization missing',result.stdout)
        self.assertNotIn('Open Project From Controller',result.stdout)
        self.assertNotIn('Downloaded=',result.stdout)
        self.assertFalse((D/'echo_before_s5.ACD').exists())
        self.assertFalse((D/'deploy_attempt.json').exists())

if __name__=='__main__':unittest.main()

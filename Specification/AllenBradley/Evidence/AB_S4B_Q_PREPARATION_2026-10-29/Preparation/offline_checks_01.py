"""Failure injection and sealed-byte replay for the new session helpers; no PLC calls."""
from pathlib import Path
import copy,datetime,gzip,json,subprocess,sys,tempfile,unittest
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0,str(D))
import qualification_session_v2 as session
from readonly_stages import execute_readonly_stages
from configuration_comparison import compare
from check_native_read_gates import evaluate
SEALED=R/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime'
def load(path):return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
class Checks(unittest.TestCase):
    def test_scope_denials(self):
        valid=load(D/'authorization.template.json');valid.update(CurrentOwnerApproved=True,OwnerInstruction='Standing Echo O3')
        valid.update({k:True for k in session.FLAGS});session.authorize(valid)
        changes=[('CurrentOwnerApproved',False),('Serial','FFFFFFFF'),('CanonicalSha256','wrong'),('SourceSha256','wrong'),('OwnerInstruction','')]
        changes += [(k,False) for k in session.FLAGS]
        changes += [(k,True) for k in ['FaultClearAuthorized','ClockSetAuthorized','PowerOperationsAuthorized','VendorStateEditsAuthorized']]
        for key,value in changes:
            with self.subTest(key=key):
                bad=dict(valid);bad[key]=value
                with self.assertRaises(ValueError):session.authorize(bad)
    def test_missing_approval_entrypoints(self):
        self.assertFalse((D/'authorization.json').exists())
        commands=[[sys.executable,str(D/name)] for name in ['qualification_session_v2.py','desktop_profile.py','task_monitor.py']]
        commands += [[str(session.SDK),'backup']]
        for index,command in enumerate(commands):
            result=subprocess.run(command,capture_output=True,text=True,timeout=25)
            with (D/f'missing_approval_{index:02}.log').open('x',encoding='utf-8') as stream:stream.write(result.stdout+result.stderr)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('authorization.json',result.stdout+result.stderr)
        self.assertFalse((D/'session_started.json').exists());self.assertFalse((D/'deploy_attempt.json').exists())
    def test_readonly_failure_isolation_and_order(self):
        wanted=['configuration_comparison','idle_equivalence','generic_acquire','desktop_profile','candidate_timing']
        for failure in wanted+[None]:
            seen=[]
            def run(label,*args):
                seen.append(label)
                if label==failure:raise RuntimeError('injected refusal')
            errors=execute_readonly_stages(run,python=sys.executable,directory=D,tools=session.T,timing=D/'measure_timing.py')
            self.assertEqual(seen,wanted);self.assertEqual([e['stage'] for e in errors],[] if failure is None else [failure])
    def test_independent_configuration_join_and_refusals(self):
        dart=load(SEALED/'dart_qualification.json.gz');oracle=load(SEALED/'idle_equivalence.json.gz')
        self.assertEqual(compare(dart,oracle)['scalarComparisons'],1100)
        field=next(k for k,v in dart['configurationPages'][0]['page'].items() if type(v) is int)
        for replacement in [False,987654321]:
            bad=copy.deepcopy(dart);bad['configurationPages'][0]['page'][field]=replacement
            with self.assertRaises(AssertionError):compare(bad,oracle)
        bad=copy.deepcopy(dart);bad['configurationPages'].pop()
        with self.assertRaises(AssertionError):compare(bad,oracle)
    def test_read_gate_failure_collection_and_cumulative_timing(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            def write(name,value):
                p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);raw=json.dumps(value).encode()
                p.write_bytes(gzip.compress(raw) if p.suffix=='.gz' else raw)
            moment=datetime.datetime.now(datetime.timezone.utc)
            write('candidate_run_requested.json',dict(Serial='601FC87B',Utc=moment.isoformat(),ReadOnlyMarker=True))
            def vals(i,maximum=9999,overlap=0):return {'FRK_Press_HealthProbe.'+k:v for k,v in dict(Samples=i,TaskMaxScanUs=maximum,TaskOverlapCount=overlap).items()}
            trace=dict(passed=True,readOnly=True,writes=0,counterOrFaultClears=0,rows=[dict(available=True,utc=(moment+datetime.timedelta(seconds=i)).isoformat(),values=vals(i)) for i in range(20)])
            timing=dict(readOnly=True,candidate=True,serial='601FC87B',unit='microseconds',capturedUtc=(moment+datetime.timedelta(seconds=30)).isoformat(),samples=[dict(values=vals(i+20)) for i in range(20)])
            write('task_monitor.json.gz',trace);write('candidate_timing.json',timing)
            result=evaluate(folder)
            self.assertTrue(result['gates']['E8']['passed']);self.assertEqual(len(result['gates']),7)
            self.assertFalse(result['passed']);self.assertTrue(all(not row['passed'] for key,row in result['gates'].items() if key!='E8'))
            for maximum,overlap in [(10000,0),(9000,1)]:
                timing['samples'][-1]['values']=vals(39,maximum,overlap);write('candidate_timing.json',timing)
                self.assertFalse(evaluate(folder)['gates']['E8']['passed'])
if __name__=='__main__':unittest.main(verbosity=2)

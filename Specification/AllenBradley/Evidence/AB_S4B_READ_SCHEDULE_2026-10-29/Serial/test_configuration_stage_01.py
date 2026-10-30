from pathlib import Path
import contextlib,gzip,importlib.util,io,json,sys,tempfile,types,unittest
from unittest.mock import patch
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
spec=importlib.util.spec_from_file_location('independent_config',W/'configuration_comparison.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
fixture=R/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime'
def load(name):return json.loads(gzip.decompress((fixture/name).read_bytes()))
class Isolation(unittest.TestCase):
    def test_each_producer_failure_retains_both_outcomes(self):
        for dart_code,oracle_code in [(0,0),(1,0),(0,1),(1,1)]:
            with self.subTest(dart=dart_code,oracle=oracle_code),tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary);(directory/'authorization.json').write_text('{}')
                calls=[];approved=[]
                def run(argv,**unused):
                    dart=argv[0].endswith('dart.exe');calls.append('dart' if dart else 'oracle')
                    name='configuration_dart.json.gz' if dart else 'configuration_oracle.json.gz'
                    value=load('dart_qualification.json.gz' if dart else 'idle_equivalence.json.gz')
                    if dart:value.update(passed=dart_code==0,readOnly=True,writes=0)
                    (directory/name).write_bytes(gzip.compress(json.dumps(value).encode()))
                    return types.SimpleNamespace(returncode=dart_code if dart else oracle_code)
                fake_authorization=types.SimpleNamespace(authorize=lambda value:approved.append(value))
                with patch.object(stage,'D',directory),patch.object(stage.subprocess,'run',run),\
                     patch.dict(sys.modules,{'qualification_session_v2':fake_authorization}),contextlib.redirect_stdout(io.StringIO()):
                    code=stage.main()
                result=json.loads((directory/'configuration_page_comparison_01.json').read_bytes())
                self.assertEqual(calls,['dart','oracle']);self.assertEqual(approved,[{}])
                self.assertEqual(result['passed'],dart_code==oracle_code==0)
                self.assertEqual(code,0 if result['passed'] else 1)
                self.assertFalse((directory/'dart_qualification.json.gz').exists())
                if result['passed']:self.assertEqual(result['scalarComparisons'],1100)
if __name__=='__main__':unittest.main(verbosity=2)

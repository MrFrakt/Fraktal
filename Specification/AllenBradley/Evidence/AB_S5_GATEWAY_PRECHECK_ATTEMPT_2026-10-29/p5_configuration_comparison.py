"""Independent read-only collection after the writer, including a failed writer."""
from pathlib import Path
import gzip,json,subprocess,sys
from configuration_comparison import compare
from s5_session import authorize
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
authorize(json.loads((D/'authorization.json').read_bytes()))
dart=Path('C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe')
producer=subprocess.run([str(dart),'--packages='+str(D/'dart_package_config.json'),
    str(R/'FraktalCore/HMI/tool/qualify_cip_configuration.dart'),
    'cip://127.0.0.1?slot=0&serial=601FC87B',str(D/'configuration_dart.json.gz')])
oracle=subprocess.run([sys.executable,str(D/'candidate_equivalence.py'),'--expect-serial','601FC87B',
    '--output',str(D/'configuration_oracle.json.gz')])
result=dict(passed=False,readOnly=True,producerExit=producer.returncode,oracleExit=oracle.returncode)
try:
    assert producer.returncode==oracle.returncode==0
    load=lambda name:json.loads(gzip.decompress((D/name).read_bytes()))
    pages=load('configuration_dart.json.gz')
    assert pages['passed'] and pages['readOnly'] and pages['writes']==0
    result=compare(pages,load('configuration_oracle.json.gz'))
except Exception as error:result['error']=f'{type(error).__name__}: {error}'
with (D/'configuration_page_comparison_01.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)

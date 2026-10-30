from pathlib import Path
W=Path(__file__).parent;OLD=Path('C:/work/fraktal-ab-s4b-q-20261029/session_01')
raw=(OLD/'configuration_comparison.py').read_text(encoding='utf-8')
start=raw.index('def main():')
raw=raw[:start]+'''def main():
    from qualification_session_v2 import authorize
    authorize(json.loads((D/'authorization.json').read_bytes()))
    root=Path('C:/Users/SoftIndVM/Fraktal')
    dart=Path('C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe')
    producer=subprocess.run([str(dart),'--packages='+str(D/'dart_package_config.json'),
        str(root/'FraktalCore/HMI/tool/qualify_cip_configuration.dart'),
        'cip://127.0.0.1?slot=0&serial=601FC87B',str(D/'configuration_dart.json.gz')])
    # Both independent reads record, including after a producer failure.
    oracle=subprocess.run([sys.executable,str(D/'candidate_equivalence.py'),'--expect-serial','601FC87B',
        '--output',str(D/'configuration_oracle.json.gz')])
    result=dict(passed=False,readOnly=True,producerExit=producer.returncode,oracleExit=oracle.returncode)
    try:
        assert producer.returncode==oracle.returncode==0,'independent producer/oracle failed'
        load=lambda p:json.loads(gzip.decompress(p.read_bytes()))
        pages=load(D/'configuration_dart.json.gz')
        assert pages['passed'] and pages['readOnly'] and pages['writes']==0
        result=compare(pages,load(D/'configuration_oracle.json.gz'))
    except Exception as error:
        result['error']=f'{type(error).__name__}: {error}'
    with (D/'configuration_page_comparison_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
'''
with (W/'configuration_comparison.py').open('x',encoding='utf-8') as f:f.write(raw)
print('Independent E4 Dart pages and Python oracle; no dependence on E3 output')

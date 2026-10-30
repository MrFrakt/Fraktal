"""Independent frozen/live oracle page join; never derives expectations from Dart."""
from pathlib import Path
import gzip,json,subprocess,sys
D=Path(__file__).parent
def compare(dart,oracle):
    assert oracle['passed']
    pair=oracle['pair'];values=pair['projection']['values'];rows=[]
    for service in pair['capture']['manifest']['readServices']:
        assert (service['Kind'],service['Version'])==(1,1)
        root=service['CanonicalRoot'];prefix=root+'/'
        fields={k[len(prefix):]:v for k,v in values.items() if k.startswith(prefix)}
        def row(group,index):
            start=f'{group}[{index}]/'
            return {k[len(start):]:v for k,v in fields.items() if k.startswith(start)}
        definitions={i:row('Definitions',i) for i in range(fields['DefinitionCount'])}
        for i,v in definitions.items():assert v['DefinitionIndex']==i
        entries=[row('Values',i) for i in range(fields['ValueCount'])]
        assert all(v['Revision']==fields['Revision'] for v in entries)
        ordinals=sorted({v['ModelOrdinal'] for v in entries})
        actual=[p for p in dart['configurationPages'] if p['root']==service['RootSymbol']]
        assert sorted(p['modelOrdinal'] for p in actual)==ordinals
        for ordinal in ordinals:
            selected=sorted((v for v in entries if v['ModelOrdinal']==ordinal),key=lambda v:v['DefinitionIndex'])
            expected=dict(PageCount=1,EntryCount=len(selected))
            for i,v in enumerate(selected,1):
                joined=dict(definitions[v['DefinitionIndex']],ValueText=v['ValueText'],Readable=v['Readable'])
                expected.update({f'Entries[{i}]/{k}':x for k,x in joined.items()})
            page=next(p['page'] for p in actual if p['modelOrdinal']==ordinal)
            assert page.keys()==expected.keys(),('paths',ordinal)
            differences=[k for k in expected if type(page[k]) is not type(expected[k]) or page[k]!=expected[k]]
            assert not differences,('values/types',ordinal,differences)
            rows.append(dict(root=service['RootSymbol'],modelOrdinal=ordinal,entries=len(selected),scalars=len(expected),valuesAndTypesEqual=True))
    assert len(dart['configurationPages'])==len(rows)==4
    count=sum(r['scalars'] for r in rows);assert count==1100
    return dict(passed=True,readOnly=True,pages=len(rows),scalarComparisons=count,rows=rows,
        source='Independent post-fixture legacy/Core projection joined by PLC ReadServices; no Dart expectation values')

def main():
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

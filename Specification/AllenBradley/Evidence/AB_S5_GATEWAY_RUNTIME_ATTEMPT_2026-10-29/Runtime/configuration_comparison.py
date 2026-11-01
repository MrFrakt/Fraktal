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


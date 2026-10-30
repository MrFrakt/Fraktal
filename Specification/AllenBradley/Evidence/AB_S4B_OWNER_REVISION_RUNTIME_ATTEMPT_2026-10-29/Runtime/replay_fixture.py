"""Independent replay of the complete fixed fixture, without controller access."""
from pathlib import Path
import gzip,json,sys
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_canonical_reader import snapshot
from fraktal_ab_canonical_equivalence import compare_live
def main():
    evidence=json.loads((D/'candidate_regressions.json').read_bytes())
    expected={'rows':31,'s4bAccessRows':2,'s4bConfigRows':8}
    counts={key:len(evidence.get(key,[])) for key in expected}
    assert all(row['passed'] for key in expected for row in evidence.get(key,[]))
    assert evidence['restored'] and evidence['policyRestored']
    rows=[]
    for kind,pairs in evidence.items():
        if not kind.endswith('Pairs'):continue
        for entry in pairs:
            p=Path(entry['output']);assert p.parent==D and entry['passed']
            report=json.loads(gzip.decompress(p.read_bytes()));assert report['passed']
            pair=report['pair'];decoded=snapshot(pair['capture'])
            assert decoded['values']==pair['canonical']['values'] and decoded['types']==pair['canonical']['types']
            checked=compare_live(lambda:dict(pair,canonical=decoded))
            assert checked['equal'] and checked['typeAcceptance']
            rows.append(dict(kind=kind,output=p.name,paths=len(decoded['values']),passed=True))
    passed=counts==expected and evidence.get('error') is None and evidence.get('s3fSetMediumEmpty') is True and len(rows)==87
    result=dict(passed=passed,readOnly=True,controllerAccess=False,caseCounts=counts,pairs=len(rows),rows=rows)
    with (D/'paired_replay_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    assert passed,'full 41-case/87-replay gate failed'
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()

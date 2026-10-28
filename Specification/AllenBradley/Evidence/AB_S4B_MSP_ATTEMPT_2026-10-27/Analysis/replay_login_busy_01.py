"""Independent replay of the short Access proof, separate from all full pairs."""
from pathlib import Path
import json

S=Path(__file__).parent.parent/'session_01'
path=S/'candidate_regressions_login_busy_witness.json'
load=lambda p:json.loads(Path(p).read_bytes())
result=dict(controllerAccess=False,fullComparison=False,fullPairsAdded=0,passed=False,recorded=path.is_file())
if path.is_file():
    data=load(path)
    result['capturePassed']=data['passed']
    if data['passed']:
        pair=data['pair'];proof=pair['stateEvidence'];rows=pair['rawReads']
        assert pair['sameStateVerified'] and proof['kind']=='PLC entire-scan generation'
        assert type(proof['generation']) is int and 1<=proof['generation']<=2147483646 and proof['generation']%2==0
        assert proof['freshStart'] and proof['readOnly']
        assert 1<=len(proof['attempts'])<=100
        assert proof['attempts'][-1]['before']==proof['generation']==proof['attempts'][-1]['after']
        assert [row['tag'] for row in rows]==['Press.Access.LoginBusy','FRK_Press_AccessState.LoginBusy']
        assert all(row['status']=='Success' for row in rows)
        canonical,legacy=(row['value'] for row in rows)
        assert type(canonical) in (bool,int) and canonical==1 and type(legacy) is int and legacy==1
        values={'Press/Access/LoginBusy':True};types={'Press/Access/LoginBusy':'Boolean'}
        assert pair['canonical']==pair['projection']==dict(values=values,types=types)
        assert data['valueEquivalent'] and data['busyObserved'] and not data['fullComparison']
        fixture=load(S/'candidate_regressions.json')
        assert fixture['loginBusyWitness']['passed'] and fixture['loginBusyWitness']['paths']==1
        assert not fixture['loginBusyWitness']['fullComparison']
        result.update(passed=True,paths=1,generation=proof['generation'],attempts=len(proof['attempts']),
            valueEquivalent=True,busyObserved=True,manifestHash=data['manifestHash'])
    else:result['error']=data['error']
with (S/'login_busy_replay_01.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result))

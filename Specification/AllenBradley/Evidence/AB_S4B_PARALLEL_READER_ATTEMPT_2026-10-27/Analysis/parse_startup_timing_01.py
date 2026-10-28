"""Reconcile the repository's actual refusal components, never estimate missing data."""
from pathlib import Path
import json
import math
import re
W=Path(__file__).parent
S=W.parent/'session_01'
path=S/'desktop_live/refresh.log'
observations=[]
if path.is_file():
    for line in path.read_text(encoding='utf-8').splitlines():
        if 'stage=complete-sample-rejected' not in line:continue
        fields=dict(re.findall(r'(\w+)=([^\s]+)',line))
        row={key:int(fields[key]) for key in ('sourceAgeUs','rpcUs','transitUs',
            'receivedAgeUs','localProcessingUs','effectiveAgeUs','fastGoodUs')}
        row['responseProcessingMs']=None if fields['responseProcessingMs']=='null' else float(fields['responseProcessingMs'])
        assert row['receivedAgeUs']==row['sourceAgeUs']+row['transitUs']
        assert row['effectiveAgeUs']==row['receivedAgeUs']+row['localProcessingUs']
        assert row['effectiveAgeUs']>=row['fastGoodUs']
        expected=row['rpcUs'] if row['responseProcessingMs'] is None else row['rpcUs']+1000-math.ceil(row['responseProcessingMs']*1000)
        assert row['transitUs']==expected and expected>=0
        row['excessUs']=row['effectiveAgeUs']-row['fastGoodUs']
        row['sourceAlreadyLate']=row['sourceAgeUs']>=row['fastGoodUs']
        row['lateAtReceipt']=row['receivedAgeUs']>=row['fastGoodUs']
        row['localProcessingCrossedBoundary']=not row['lateAtReceipt']
        observations.append(row)
result=dict(passed=True,readOnly=True,controllerAccess=False,observations=observations,
    refusalReproduced=bool(observations),
    interpretation='Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred.')
with (S/'desktop_freshness_analysis_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))

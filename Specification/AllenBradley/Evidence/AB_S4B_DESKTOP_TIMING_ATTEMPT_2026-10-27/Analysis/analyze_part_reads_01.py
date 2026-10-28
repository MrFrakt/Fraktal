"""Interpret recorded schema/revision headers, not absent data or PLC payloads."""
from pathlib import Path
import json,statistics
W=Path(__file__).parent;S=W.parent/'session_01';path=S/'part_read_diagnostics.jsonl'
calls=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.is_file() else []
attempts=[];failed=[]
for call in calls:
    rows=call['reads'];assert call['readCount']==len(rows)
    assert len(rows)<=call['attemptBudget']*3
    groups=[]
    for start in range(0,len(rows),3):
        group=rows[start:start+3]
        assert [r['phase'] for r in group]==['before','body','after'][:len(group)]
        available=len(group)==3 and all(r.get('success') and r.get('tagMatched') and 'schemaVersion' in r and 'dataRevision' in r for r in group)
        schema=[r.get('schemaVersion') for r in group];revisions=[r.get('dataRevision') for r in group]
        equal=available and len(set(schema))==1 and len(set(revisions))==1
        even=bool(equal and revisions[0]%2==0)
        row=dict(call=call['call'],attempt=start//3+1,complete=len(group)==3,
          schemaVersions=schema,dataRevisions=revisions,headersAvailable=available,
          equalHeaders=bool(equal),equalEvenHeaders=even,
          windowUs=group[-1]['startUs']+group[-1]['elapsedUs']-group[0]['startUs'],
          requestElapsedUs=[r['elapsedUs'] for r in group])
        attempts.append(row);groups.append(row)
    if not call['passed']:failed.append(dict(call=call['call'],errorType=call['errorType'],elapsedUs=call['elapsedUs'],attemptBudget=call['attemptBudget'],attempts=groups))
durations=[r['windowUs'] for r in attempts]
result=dict(passed=True,readOnly=True,controllerAccess=False,tracePresent=path.is_file(),calls=len(calls),
 successfulCalls=sum(c['passed'] for c in calls),failedCalls=len(failed),attempts=len(attempts),
 equalEvenHeaderAttempts=sum(r['equalEvenHeaders'] for r in attempts),failedCallRecords=failed,
 maxAttemptWindowUs=max(durations,default=None),medianAttemptWindowUs=statistics.median(durations) if durations else None,
 rows=attempts,traceIncludesOverhead=True,includesLiveAndHeldOracleReads=True,causeIsolated=False,
 interpretation='Only recorded schema/revision equality/parity and timing are classified. No missing headers, payload integrity or host/publisher cause is inferred.')
with (S/'part_read_analysis_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))

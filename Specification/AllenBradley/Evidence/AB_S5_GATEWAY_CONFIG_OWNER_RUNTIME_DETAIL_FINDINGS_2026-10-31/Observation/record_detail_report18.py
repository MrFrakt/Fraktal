import sys
sys.path.pop(0)
from pathlib import Path
import datetime,json
D=Path('C:/work/fraktal-ab-s5-20261029/session_18')
rows=[json.loads(line) for line in (D/'browser_detail_quality_observation.jsonl').read_text(encoding='utf-8').splitlines()]
summary={}
for group in ('timing','history'):
    samples=[r[group] for r in rows if group in r]
    summary[group]=dict(samples=len(samples),minimumGoodLeaves=min(int(r['statuses'].get('0',0)) for r in samples),maximumGoodLeaves=max(int(r['statuses'].get('0',0)) for r in samples),maximumAgeMs=max(r['maximumAgeMs'] for r in samples),samplesWithNonGoodLeaves=sum(any(k!='0' and n>0 for k,n in r['statuses'].items()) for r in samples))
record=dict(ownerWords='performed now, all passed, but we have an old error i didnt mention earlier, command timming - part slide card is too tall and after a few secconds dissapears, and also event history continously populeates then cleasr and repopulates douring about 10 to 15 seconds',
    laterOwnerConnectionChecklistWords='Performed now; all passed without flicker',
    screenshot=dict(source='User attachment in this conversation; no local attachment path available',width=1209,height=1218,twoChromeTabs=True,operatorLoggedIn=True,mode='MANUAL',timingCard='Very tall blank body, columns extend beyond card',eventHistory='Audit rows visible'),
    readOnlyObservation=summary,readOnly=True,credentialValuesRecorded=False,
    scope='Connection/command success reported. Timing layout and detail freshness remain open. No stage exit or logout acceptance implied.',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D/'owner_detail_issue_report.json').open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
print(json.dumps(summary))

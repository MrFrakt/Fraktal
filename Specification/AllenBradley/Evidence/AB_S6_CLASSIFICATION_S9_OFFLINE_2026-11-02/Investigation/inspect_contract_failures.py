from pathlib import Path
import json
W=Path(__file__).parent;tests={};errors=[];failed=[]
for line in (W/'s9_legacy_machine_01.log').read_text(encoding='utf-8',errors='replace').splitlines():
    try:event=json.loads(line)
    except ValueError:continue
    if not isinstance(event,dict):continue
    if event.get('type')=='testStart':tests[event['test']['id']]=event['test']['name']
    if event.get('type')=='error':errors.append(dict(test=tests.get(event.get('testID')),message=str(event.get('error'))[:1100]))
    if event.get('type')=='testDone' and event.get('result')!='success':failed.append(dict(name=tests.get(event.get('testID')),result=event.get('result')))
print(json.dumps(dict(failed=failed,errors=errors),indent=2))

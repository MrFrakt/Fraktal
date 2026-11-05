import sys, subprocess, json, datetime
from pathlib import Path
root=Path(__file__).parent
label=sys.argv[1]
if not label.replace('_','').isalnum(): raise SystemExit('Invalid log label')
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (root/(label+'.log')).open('x',encoding='utf-8') as log:
    result=subprocess.run(sys.argv[2:],stdout=log,stderr=subprocess.STDOUT,text=True)
with (root/(label+'_exit.json')).open('x',encoding='utf-8') as out:
    json.dump(dict(startUtc=start,endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv[2:],exitCode=result.returncode),out,indent=2)
print(json.dumps(dict(label=label,exitCode=result.returncode)))
raise SystemExit(result.returncode)

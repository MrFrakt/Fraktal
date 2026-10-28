"""Append-only command outputs for S4b offline work."""
from pathlib import Path
import datetime,json,subprocess,sys
W=Path(__file__).parent
label=sys.argv[1]
if not label.replace('_','').isalnum():raise SystemExit('invalid label')
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (W/(label+'.log')).open('x',encoding='utf-8') as stream:
    result=subprocess.run(sys.argv[2:],stdout=stream,stderr=subprocess.STDOUT,text=True)
with (W/(label+'_exit.json')).open('x',encoding='utf-8') as stream:
    json.dump(dict(startUtc=started,endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv[2:],exitCode=result.returncode),stream,indent=2)
print(json.dumps(dict(label=label,exitCode=result.returncode)))
raise SystemExit(result.returncode)

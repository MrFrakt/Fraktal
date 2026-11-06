"""Append-only C4 continuation runner: label, working directory, command..."""
from pathlib import Path
import datetime,json,subprocess,sys
W=Path(__file__).parent;label,cwd=sys.argv[1:3]
assert label.replace('_','').isalnum()
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (W/(label+'.log')).open('x',encoding='utf-8') as out:
    result=subprocess.run(sys.argv[3:],cwd=cwd,stdout=out,stderr=subprocess.STDOUT,text=True)
with (W/(label+'_exit.json')).open('x',encoding='utf-8') as out:
    json.dump(dict(startUtc=start,endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   cwd=cwd,command=sys.argv[3:],exitCode=result.returncode),out,indent=2)
print(json.dumps(dict(label=label,exitCode=result.returncode)))
raise SystemExit(result.returncode)

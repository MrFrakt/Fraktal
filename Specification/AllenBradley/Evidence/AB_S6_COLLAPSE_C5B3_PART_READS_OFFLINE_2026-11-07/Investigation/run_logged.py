"""Append-only C5 logger. Records process-start failures as well as exit codes."""
from pathlib import Path
import datetime,json,subprocess,sys,traceback
W=Path(__file__).parent;label,cwd=sys.argv[1:3]
assert label.replace('_','').isalnum()
start=datetime.datetime.now(datetime.timezone.utc).isoformat();error=None
with (W/(label+'.log')).open('x',encoding='utf-8') as out:
 try:code=subprocess.run(sys.argv[3:],cwd=cwd,stdout=out,stderr=subprocess.STDOUT,text=True).returncode
 except Exception as e:
  traceback.print_exc(file=out);code=1;error=type(e).__name__+': '+str(e)
with (W/(label+'_exit.json')).open('x',encoding='utf-8') as out:
 json.dump(dict(startUtc=start,endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cwd=cwd,command=sys.argv[3:],exitCode=code,error=error),out,indent=2)
print(json.dumps(dict(label=label,exitCode=code)))
raise SystemExit(code)

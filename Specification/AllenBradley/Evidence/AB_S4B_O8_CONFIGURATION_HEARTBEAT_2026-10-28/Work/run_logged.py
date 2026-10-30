from pathlib import Path
import datetime,json,subprocess,sys
W=Path(__file__).parent
label=sys.argv[1];assert label.replace('_','').isalnum()
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (W/(label+'.log')).open('x',encoding='utf-8') as f:
    result=subprocess.run(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT,text=True)
with (W/(label+'_exit.json')).open('x',encoding='utf-8') as f:
    json.dump(dict(startUtc=start,endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        command=sys.argv[2:],exitCode=result.returncode),f,indent=2)
print(json.dumps(dict(label=label,exitCode=result.returncode)))
raise SystemExit(result.returncode)

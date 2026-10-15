import json,subprocess,time
from pathlib import Path
work=Path(__file__).resolve().parent
plc=Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens')
source=work/'runtime13/types03.jsonl';deadline=time.monotonic()+900
while time.monotonic()<deadline:
 if source.exists():
  lines=source.read_text('ascii').splitlines()
  if lines:
   try:last=json.loads(lines[-1])
   except json.JSONDecodeError:last={}
   if last.get('event')=='summary':
    assert last['completed'] and last['failures']==0,'typed acceptance failed'
    break
 time.sleep(.5)
else:raise TimeoutError('typed acceptance completion')
steps=[('sets_regression03','Tests/ConfigSets/probe_web.py',work/'runtime13/sets_regression03.jsonl',1500),
 ('pre_hmi_idle03','Tests/ConfigTypes/verify_idle.py',work/'pre_hmi_idle03.jsonl',180),
 ('hmi01','Tests/ConfigTypes/run_hmi.py',work/'hmi01',750),
 ('final_idle01','Tests/ConfigTypes/verify_idle.py',work/'final_idle01.jsonl',180)]
ledger=[]
for name,script,out,timeout in steps:
 started=time.time()
 with (work/(name+'.log')).open('xb') as log:
  command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(plc/'Tests/Access/with_credentials.ps1'),'-Action','probe','-Output',str(out),'-ScriptFile',str(plc/script)]
  result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
 ledger.append(dict(step=name,exit_code=result.returncode,elapsed_seconds=round(time.time()-started,2)))
 (work/'remaining_results.json').write_bytes((json.dumps(ledger,indent=2)+'\n').encode('ascii'))
 assert result.returncode==0,'native gate failed: '+name
print(json.dumps(ledger))

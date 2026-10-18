from pathlib import Path
import subprocess,sys,json,time
w=Path(__file__).parent;repo=Path('C:/Projects/Fraktal');wrapper=repo/'FraktalCore/PLC/Siemens/Tests/Access/with_credentials.ps1'
def run(args,path):
    with path.open('xb') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:raise RuntimeError(str(path)+' exit '+str(r.returncode))
power=['powershell.exe','-NoProfile','-File',str(w/'bench_power.ps1')]
run(['powershell.exe','-NoProfile','-File',str(wrapper),'-Action','probe','-Output',str(w/'bench_before_link_loss.json'),'-ScriptFile',str(w/'inspect_bench.py')],w/'bench_before_link_loss.log')
off=False
try:
    run(power+['-Action','Off'],w/'link_loss_off01.jsonl');off=True
    time.sleep(1)
    run(['powershell.exe','-NoProfile','-File',str(w/'physical_credentials.ps1'),'-Output',str(w/'physical_during_link_loss01.jsonl')],w/'physical_during_link_loss01.log')
    rows=[json.loads(s) for s in (w/'physical_during_link_loss01.jsonl').read_text().splitlines()]
    values={r['member']:r['value'] for r in rows if r.get('event')=='physical-read'}
    assert values==dict(LinkHealthy=False,OutputsEnabled=False),values
    print(dict(physical_during_loss=values),flush=True)
finally:
    if off:run(power+['-Action','On'],w/'link_loss_on01.jsonl')
print('Saved bench restored; original Fraktal remained RUN.',flush=True)

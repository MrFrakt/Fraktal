"""Run the final-source suite after the earlier run, without overlapping suites."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time

W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
T=R/'FraktalCore/PLC/Allen-Bradley/tools'
deadline=time.monotonic()+1800
while not (W/'full_ab_rows_01_exit.json').exists():
    if time.monotonic()>=deadline:raise TimeoutError('prior suite did not complete')
    time.sleep(1)
assert json.loads((W/'full_ab_rows_01_exit.json').read_bytes())['exitCode']==0
def source_hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(T.glob('*.py'))}
before=source_hashes()
with (W/'full_ab_rows_source_bindings_before_02.json').open('x',encoding='utf-8') as f:
    json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=before),f,indent=2)
subprocess.run([sys.executable,str(W/'run_logged.py'),'full_ab_rows_02',sys.executable,'-m','unittest',
               'discover','-s',str(T),'-t',str(T),'-q'],cwd=R,check=True)
assert before==source_hashes(),'source changed during final suite'
with (W/'full_ab_rows_source_bindings_result_02.json').open('x',encoding='utf-8') as f:
    json.dump(dict(passed=True,sourcesUnchangedDuringSuite=True,pythonModules=len(before),
                   utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f,indent=2)
print(json.dumps(dict(passed=True,sourcesUnchangedDuringSuite=True,pythonModules=len(before))))

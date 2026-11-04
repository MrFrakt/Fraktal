from pathlib import Path
W=Path(__file__).parent
source=(W/'replay_s9_contract_pair.py').read_text(encoding='utf-8').replace('_01','_02')
old="        except ValueError:continue\n        if event.get('type')=='suite':"
new="        except ValueError:continue\n        if not isinstance(event,dict):continue\n        if event.get('type')=='suite':"
assert source.count(old)==1
source=source.replace(old,new)
old="    suites={};tests={};results={}"
new="    with (W/('s9_'+label+'_process_02_exit.json')).open('x',encoding='utf-8') as f:json.dump(dict(exitCode=run.returncode,command=command),f,indent=2)\n    suites={};tests={};results={}"
assert source.count(old)==1
source=source.replace(old,new)
with (W/'replay_s9_contract_pair_02.py').open('x',encoding='utf-8') as f:f.write(source)
print('New replay outputs; original parser failure and log preserved')

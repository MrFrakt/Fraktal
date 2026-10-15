import os,sys,json,re
from pathlib import Path
import xml.etree.ElementTree as ET
w=Path(__file__).resolve().parent;r=Path('C:/Projects/Fraktal')
suites={'Ordinary load banks':('02_native_probe.junit.xml',125),'Load-only banks':('05_only_probe.junit.xml',118),'Station/model config':('07_config.junit.xml',120),'Access/session':('08_access.junit.xml',122),'State and alarm':('10_state_alarm.junit.xml',100),'Manual alarm recovery':('11_recovery.junit.xml',341)}
counts={}
for name,(file,n) in suites.items():
 root=ET.parse(w/file).getroot();assert int(root.get('tests'))==n and int(root.get('failures',0))==0 and not list(root.iter('failure')),(name,root.attrib);counts[name]=n
compiles=[]
for file in ('01_native.jsonl','03_only_compile.jsonl','04_only_native.jsonl'):
 rows=[json.loads(s) for s in (w/file).read_text('utf-8-sig').splitlines()]
 c=[s for s in rows if s.get('event')=='compile'];assert c and all(s['errors']==s['warnings']==0 for s in c);compiles.extend(c)
for name in ('GDB_LoadBankA','GDB_LoadBankB'):
 root=ET.parse(w/'export_only_02/xml'/(name+'.xml')).getroot();assert root.findtext('.//IsOnlyStoredInLoadMemory')=='true' and root.findtext('.//MemoryLayout')=='Optimized'
 native=(w/'export_only_02/scl'/(name+'.db')).read_bytes();assert b'UNLINKED' in native and b'NON_RETAIN' in native
baseline=json.loads((w/'15_baseline_native_comparison.json').read_bytes());assert len(baseline['unchanged'])==321 and baseline['changed']==['F_ConfigBenchObserve.scl']
def log(file):
 b=(w/file).read_bytes();return b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8-sig')
assert re.search(r'Ran 170 tests.*?\bOK\b',log('14_tools.log'),re.S)
assert re.search(r'Ran 35 tests.*?\bOK\b',log('17_consistency_tests.log'),re.S)
assert '0 error(s), 0 warning(s)' in log('16_consistency.log')
sys.path.insert(0,str(r/'FraktalCore/PLC/Siemens/tools'))
from tia_target_guard import guard
owner=guard();assert owner['state']=='Run'
summary=dict(generator='0.14 unchanged',native=counts,native_assertions=sum(counts.values()),compiles=compiles,baseline_unchanged=321,baseline_changed=baseline['changed'],tools=170,consistency=35,owner=owner)
with (w/'19_gate_summary.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))

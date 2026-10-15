from pathlib import Path
import json,re,xml.etree.ElementTree as ET
import sys
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_target_guard import guard
WORK=Path(__file__).resolve().parent
suites={
 'Event delivery':('35_delivery_probe.junit.xml',208),
 'Lost receipt reply':('36_lost_reply.xml',10),
 'Closed history':('41_history.junit.xml',174),
 'Manual alarm recovery':('42_recovery.junit.xml',341),
 'Users and policy':('43_access_persistence.xml',419),
 'Named config sets':('44_sets.xml',198),
 'Station/model config':('46_config.junit.xml',120),
 'Access/session':('47_access.junit.xml',122),
 'State and alarm':('49_state_alarm.junit.xml',100),
 'Decisions':('50_decision.xml',36)}
counts={}
for name,(file,expected) in suites.items():
 root=ET.parse(WORK/file).getroot();assert int(root.get('tests'))==expected,(name,root.attrib)
 assert int(root.get('failures',0))==0 and int(root.get('errors',0))==0 and not list(root.iter('failure')) and not list(root.iter('error')),(name,root.attrib)
 counts[name]=expected
stress=[json.loads(s) for s in (WORK/'33_recovery_checkpoint_retest.jsonl').read_text(encoding='utf-8').splitlines()]
stress=[r for r in stress if r.get('event')=='recovery-checkpoint'];assert len(stress)==12 and all(r['count']==16 and r['check']==0 for r in stress)
compile_results={}
for file in ('32_native_download.jsonl','51_press_final_compile.jsonl'):
 rows=[json.loads(s) for s in (WORK/file).read_text(encoding='utf-8').splitlines()]
 compiles=[r for r in rows if r.get('event')=='compile'];assert compiles and all(r['errors']==0 and r['warnings']==0 for r in compiles)
 compile_results[file]=compiles
parity=json.loads((WORK/'56_final_parity.json').read_bytes());assert parity['replayed_sources']==120 and parity['wired']
def log(file):
 raw=(WORK/file).read_bytes();return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
assert re.search(r'Ran 170 tests.*?\bOK\b',log('52_tools_final.log'),re.S)
assert re.search(r'Ran 35 tests.*?\bOK\b',log('54_consistency_tests.log'),re.S)
assert '+574 ~8: All tests passed!' in log('14_hmi_tests.log')
owner=guard();assert owner['state']=='Run'
value=dict(generator='0.14',native=counts,native_assertions=sum(counts.values()),checkpoint_cycles=len(stress),alarms_per_checkpoint_cycle=16,tools=170,consistency=35,hmi=574,hmi_skips=8,compile=compile_results,press=parity,owner=owner,keeper_pid=12728,receipt_protocol='dedicated_metadata_mailbox',active_image_schema=2)
path=WORK/'60_gate_summary.json';assert not path.exists();path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(value,indent=2))

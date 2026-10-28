from pathlib import Path
import json
W=Path(__file__).parent;S=W.parent/'session_01'
path=S/'authorization.template.json';value=json.loads(path.read_bytes())
assert not value['CurrentOwnerApproved'] and not (S/'authorization.json').exists()
old='Fitting rows use a bounded read-only CIP Multiple Service Packet for the existing before counter, count dependencies, native body and after counter.'
new='Fitting rows combine only count/body reads in a bounded read-only CIP Multiple Service Packet between separately completed counter reads; packet execution order is irrelevant.'
assert value['Scope'].count(old)==1
with (W/'authorization_template_before_order_review.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
value['Scope']=value['Scope'].replace(old,new)
path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='')
script=W/'prepare_session_01.py';text=script.read_text(encoding='utf-8')
assert text.count(old)==1
script.write_text(text.replace(old,new),encoding='utf-8',newline='')
print('Unapproved scope corrected to separate pre/post counters; no controller access.')

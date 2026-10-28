from pathlib import Path
import hashlib,json,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T))
from fraktal_ab_sdk_log_gate import audit_log
source=(Path('C:/work/fraktal-ab-s4-20261025/offline_01/audit_access.py').read_text()
    .replace('fraktal_ab_genealogy_s4_demo','fraktal_ab_genealogy_s4b_demo').replace('fieldbus.products(app)','pub.products(app)'))
with (W/'audit_access.py').open('x') as stream:stream.write(source)
for label,project in [('source','canonical_read_view_01.L5X'),('echo','EchoController_view_readback_01.L5X'),
    ('physical','PhysicalController_view_readback_01.L5X'),('prepared','prepared_readback_01.L5X')]:
    subprocess.run([sys.executable,str(W/'run_logged.py'),'access_'+label+'_01',sys.executable,str(W/'audit_access.py'),str(W/project),str(W/('access_'+label+'_01.json'))],check=True,cwd=R)
audits={}
for label in ('view_build_EchoController_01','view_build_PhysicalController_01','prepare_acd_01'):
    audits[label]=audit_log((W/(label+'.log')).read_text(),required_operations=('Build','Save As') if label.startswith('view') else ('Save As',))
    assert audits[label]['Clean'],audits[label]
with (W/'sdk_audits_01.json').open('x') as stream:json.dump(audits,stream,indent=2)
assert hashlib.sha256((W/'canonical_read_view_01.ACD').read_bytes()).hexdigest().upper()=='7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
print(json.dumps(dict(passed=True,accessAudits=4,sdkAudits=len(audits))))

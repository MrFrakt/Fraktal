import hashlib
import json
import sys
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_readback as readback
import fraktal_ab_sdk_log_gate as gate
source=OUT/'resources_01.L5X'
compared=readback.compare(source,OUT/'prepared_readback.L5X')
with (OUT/'prepared_compare.json').open('x',encoding='utf-8') as stream:
    json.dump(compared,stream,indent=2)
audits={}
for name in ('echo_build.log','physical_build.log','prepare.log'):
    audits[name]=gate.audit_log((OUT/name).read_text(encoding='utf-8',errors='replace'),
                               ('Build','Save As'),require_clean_import=True)
    if not audits[name]['Clean']:
        raise RuntimeError((name,audits[name]))
with (OUT/'compiler_audit.json').open('x',encoding='utf-8') as stream:
    json.dump(audits,stream,indent=2)
if not compared['Equivalent']:
    raise RuntimeError('prepared ACD differs from source')
baseline=hashlib.sha256((OUT/'tower_baseline.L5X').read_bytes()).hexdigest().upper()
if baseline!='03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED':
    raise RuntimeError('opt-out baseline changed')
print(json.dumps(dict(preparedEquivalent=True,baselineUnchanged=True,
                      executableBodies=compared['ExecutableBodies'],initialValues=compared['AuthoredInitialValues'])))

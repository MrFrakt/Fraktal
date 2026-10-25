from pathlib import Path
import hashlib
import json
import sys
W=Path(__file__).parent
ROOT=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_sdk_log_gate import audit_log
from fraktal_ab_readback import compare
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
pin=(W/'canonical.sha256').read_text().strip()
assert sha(W/'s3i_canonical.ACD')==sha(W/'capacity_review.ACD')==pin
results={}
for name in ('native_bench_echo_05','native_physical_05','prepare_acd_01'):
    audit=audit_log((W/(name+'.log')).read_text(),('Open project','Build','Save As'),require_clean_import=True)
    results[name]=audit
    assert audit['Clean'],(name,audit)
for name in ('native_bench_echo_05.L5X','native_physical_05.L5X','prepared_readback.L5X'):
    report=compare(W/'s3i_bench_05.L5X',W/name);assert report['Equivalent'],name
report=compare(W/'s3i_bench_05.L5X',W/'prepared_readback.L5X')
with (W/'canonical_prepared_compare.json').open('x') as f:json.dump(report,f,indent=2)
for name in ('echo_access_05','physical_access_05','prepared_access_01'):
    assert json.loads((W/(name+'.json')).read_text())['passed']
with (W/'sdk_audits_01.json').open('x') as f:json.dump(dict(passed=True,canonicalSha256=pin,audits=results),f,indent=2)
print(json.dumps(dict(passed=True,canonicalSha256=pin,readbackValues=report['AuthoredInitialValues'],bodies=report['ExecutableBodies'])))

"""Prepared ACD must read back equal to the source; every SDK log must be clean."""
import json, sys
from pathlib import Path
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
OUT = Path('C:/work/fraktal-ab-echo-20261019')
sys.path.insert(0, str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_readback as readback
import fraktal_ab_sdk_log_gate as gate
compared = readback.compare(OUT/'genealogy_current.L5X', OUT/'prepared_readback.L5X')
with (OUT/'prepared_compare.json').open('x', encoding='utf-8') as stream:
    json.dump(compared, stream, indent=2)
audits = {}
for name, ops in (('echo_build.log', ('Build',)), ('physical_build.log', ('Build',)),
                  ('prepare.log', ('Build', 'Save As'))):
    audits[name] = gate.audit_log((OUT/name).read_text(encoding='utf-8', errors='replace'),
                                  ops, require_clean_import=True)
with (OUT/'compiler_audit.json').open('x', encoding='utf-8') as stream:
    json.dump(audits, stream, indent=2)
bad = [n for n, a in audits.items() if not a['Clean']]
if bad or not compared['Equivalent']:
    raise SystemExit(json.dumps(dict(equivalent=compared['Equivalent'], unclean=bad)))
print(json.dumps(dict(preparedEquivalent=True, logsClean=list(audits),
                      executableBodies=compared['ExecutableBodies'],
                      initialValues=compared['AuthoredInitialValues'])))

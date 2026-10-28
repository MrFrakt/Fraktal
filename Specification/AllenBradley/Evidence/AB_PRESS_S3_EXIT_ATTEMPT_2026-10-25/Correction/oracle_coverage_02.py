"""Offline: which press S3k contract paths can the legacy oracle not produce?

Replays the oracle's value construction (shared.oracle) with the press candidate
over the accepted genealogy idle capture's recorded inputs; the press declares no
Part, host-event or tower owner, so those inputs are absent. No controller access.
"""
import gzip, json, os, sys
from pathlib import Path
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_press_canonical_echo38'
ROOT = Path('C:/Users/SoftIndVM/Fraktal'); sys.path.insert(0, str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_press_canonical_echo38 as candidate
import fraktal_ab_projection as projection
import fraktal_ab_manifest as manifest
import fraktal_ab_s3k_equivalence as s3k

capture = ROOT/'Specification/AllenBradley/Evidence/AB_S3K_CANONICAL_RUNTIME_2026-10-25/Runtime/idle_equivalence.json.gz'
held = json.loads(gzip.decompress(capture.read_bytes()))['pair']['legacyInputs']
app = candidate.application(); assert projection.APP == app
additional = dict(held['additional'], part=None, host=None, tower=None)
# Numeric localization keys differ between catalogues; translate genealogy key numbers
# to press numbers through their portable names, only in fields that hold a key.
import fraktal_ab_genealogy_s3k_demo as genealogy
g_rows = manifest.content(genealogy.application())['Localization']; p_rows = manifest.content(app)['Localization']
to_portable = {r['NumericKey']: r['PortableKey'] for r in g_rows}; to_press = {r['PortableKey']: r['NumericKey'] for r in p_rows}
remapped = []
def remap(value, name=''):
    if isinstance(value, dict): return {k: remap(v, k) for k, v in value.items()}
    if isinstance(value, list): return [remap(v, name) for v in value]
    if name.endswith('Key') and type(value) is int and value in to_portable and to_portable[value] in to_press:
        if to_press[to_portable[value]] != value: remapped.append(name)
        return to_press[to_portable[value]]
    return value
additional = remap(additional)
shift = additional['line_shift']['Count'] if app.line else 0
expected = s3k.subset_paths(app, held['codes'], canonical=False, count=0, shift_count=shift)
rows = manifest.content(app)
catalogue = {row['NumericKey']: row['PortableKey'] for row in rows['Localization']}
values = {}
for module in projection.modules(rows, app=app):
    base = module['base']
    values.update({base+'/Status/Name': module['identity'], base+'/Status/ModuleType': module['type'],
                   base+'/Status/DisplayNameKey': module['displayNameKey']})
    if module['typeKey']: values[base+'/Status/TypeKey'] = module['typeKey']
    name = module['identity'].split('.')[-1]
    detail = (projection.unit_status(held['unit'], None, app=app) if module['type'] == 1 else
              projection.module_status(held['contexts'][name], app, name, catalogue))
    values.update({base+'/'+p: v for p, v in detail.items()})
values.update({app.name+'/'+p: v for p, v in projection.model_status(app, held['unit'], held['codes']).items()})
error = None
try:
    values.update(s3k.extra_values(app, held['unit'], additional, page=0, model=0, provider_state={}))
except Exception as caught:
    error = f'{type(caught).__name__}: {caught}'
missing = sorted(expected - values.keys())
print(json.dumps(dict(expected=len(expected), produced=len(values), missingCount=len(missing), missing=missing[:40], extraError=error, remappedFields=sorted(set(remapped))), indent=1))

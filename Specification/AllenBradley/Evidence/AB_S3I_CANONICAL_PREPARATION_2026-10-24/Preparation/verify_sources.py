from pathlib import Path
import gzip
import hashlib
import json
import subprocess

ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;EV=ROOT/'Specification/AllenBradley/Evidence'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=json.loads((EV/'AB_S3H_CANONICAL_OBSERVATION_FRAME_PREPARATION_2026-10-24/Preparation/source_bindings_01.json').read_text())['sha256']
T='FraktalCore/PLC/Allen-Bradley/tools/'
changed={T+n for n in ('fraktal_ab_canonical_equivalence.py','fraktal_ab_canonical_observation.py',
    'fraktal_ab_canonical_publication.py','fraktal_ab_generate.py','fraktal_ab_line.py','test_fraktal_ab_canonical_publication.py')}
added={T+n for n in ('fraktal_ab_canonical_line.py','fraktal_ab_genealogy_s3i_demo.py','fraktal_ab_s3i_equivalence.py',
    'fraktal_ab_s3i_fixture_execute.py','fraktal_ab_s3i_native_checks.py','fraktal_ab_s3i_reference.py',
    'test_fraktal_ab_remaining_correspondences.py','test_fraktal_ab_s3i_line.py')}
assert changed<=prior.keys(),changed-prior.keys()
bindings={}
for name,pin in prior.items():
    now=sha(ROOT/name);assert (now!=pin.lower())==(name in changed),('unexpected inherited change',name)
    bindings[name]=now
for name in added:
    assert name not in bindings;bindings[name]=sha(ROOT/name)
assert len(bindings)==170
with (W/'source_bindings_01.json').open('x') as f:json.dump(dict(passed=True,sha256=bindings,changed=sorted(changed),added=sorted(added)),f,indent=2)

# Preserve the original publication profile's exact source, and replay the
# latest accepted S3h native document through the unchanged generic reader.
import sys
sys.path.insert(0,str(ROOT/T))
import fraktal_ab_canonical_reader as reader
import fraktal_ab_genealogy_s3h_demo as demo
import fraktal_ab_generate as gen
output=W/'accepted_s3h_regenerated_01.L5X';assert not output.exists()
gen.generate(demo.application(),Path('C:/work/echo38_5580_seed.L5X'),output)
assert sha(output)=='bf456bca68745c39d0903d0de96b9b8ad4ec9dc502e809f38da82599d2efb1f2'
directory=EV/'AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24'
paths=[]
for path in directory.rglob('*.json.gz'):
    data=json.loads(gzip.decompress(path.read_bytes()))
    if data.get('passed') and isinstance(data.get('pair'),dict) and 'canonical' in data['pair']:
        pair=data['pair'];assert reader.snapshot(pair['capture'])==pair['canonical']
        paths.append(dict(path=str(path.relative_to(directory)),sha256=sha(path),nodes=pair['canonical']['nodeCount']))
assert len(paths)==88,len(paths)
report=dict(passed=True,sourceBindings=len(bindings),acceptedS3hSourceUnchanged=True,acceptedS3hPairsReplayed=len(paths),pairs=paths)
with (W/'accepted_replay_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='pairs'}))

"""Bind the follow-up to the accepted PLC image and 170 inherited sources."""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
W=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence'
T='FraktalCore/PLC/Allen-Bradley/tools/'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=json.loads((E/'AB_S3I_CANONICAL_RUNTIME_2026-10-24/Runtime/initial_source_verification_02.json').read_text())['sha256']
assert len(prior)==170
for name,pin in prior.items():assert sha(ROOT/name)==pin,name
add=[T+'fraktal_ab_s3i_lifetime_execute.py',T+'test_fraktal_ab_s3i_lifetime.py']
assert not any(name in prior for name in add)
bindings=dict(prior,**{name:sha(ROOT/name) for name in add})
with (W/'source_bindings_01.json').open('x') as f:json.dump(dict(passed=True,sha256=bindings,unchangedInherited=170,added=add,changed=[]),f,indent=2)
output=W/'s3i_regenerated_01.L5X'
subprocess.run([sys.executable,str(ROOT/T/'fraktal_ab_s3i_native_checks.py'),'--seed','C:/work/echo38_5580_seed.L5X','--output',str(output)],check=True,stdout=subprocess.DEVNULL)
assert sha(output)==sha(W/'s3i_bench_05.L5X')=='0f3a5f6dd762bed3819404025daf6d5703511807b440c4988eacf5e494ec72c3'
for name in ('s3i_canonical.ACD','capacity_review.ACD','retention_control.ACD'):
    assert sha(W/name).upper()=='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
sys.path.insert(0,str(ROOT/T))
import fraktal_ab_canonical_reader as reader
reference=E/'AB_S3I_CANONICAL_RUNTIME_2026-10-24/Runtime'
count=0
for path in sorted(reference.glob('*.json.gz')):
    data=json.loads(gzip.decompress(path.read_bytes()))
    if isinstance(data.get('pair'),dict):
        assert data['passed'] and reader.snapshot(data['pair']['capture'])==data['pair']['canonical'];count+=1
assert count==88,count
report=dict(passed=True,sourceBindings=172,unchangedInherited=170,plcSourceUnchanged=True,acdUnchanged=True,
    acceptedPairsReplayed=88,sourceSha256=sha(output),capacityUsedBlocks=2763512,capacityAvailableBlocks=382216,
    compileReadbackEvidence='AB_S3I_CANONICAL_PREPARATION_2026-10-24',runtimeEvidence='AB_S3I_CANONICAL_RUNTIME_2026-10-24')
with (W/'unchanged_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))

"""Bind the retry to the sealed lifetime closure: four oracle/fixture files change, the PLC does not."""
from pathlib import Path
import hashlib, json, subprocess, sys

W = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
E = ROOT/'Specification/AllenBradley/Evidence'
T = 'FraktalCore/PLC/Allen-Bradley/tools/'
ACD = 'A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
SOURCE = '0f3a5f6dd762bed3819404025daf6d5703511807b440c4988eacf5e494ec72c3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


prior = json.loads((E/'AB_S3I_CANONICAL_LIFETIME_PREPARATION_2026-10-24/Preparation/source_bindings_01.json').read_text())['sha256']
assert len(prior) == 172
changed = {T + n for n in ('fraktal_ab_paired_observation.py', 'fraktal_ab_s3i_lifetime_execute.py',
                           'test_fraktal_ab_canonical_observation.py', 'test_fraktal_ab_s3i_lifetime.py')}
bindings = {}
for name, pin in prior.items():
    now = sha(ROOT/name)
    assert (now != pin) == (name in changed), ('unexpected source state', name)
    bindings[name] = now
with (W/'source_bindings_01.json').open('x') as out:
    json.dump(dict(passed=True, sha256=bindings, unchangedInherited=168, changed=sorted(changed), added=[]), out, indent=2)
output = W/'s3i_regenerated_01.L5X'
subprocess.run([sys.executable, str(ROOT/T/'fraktal_ab_s3i_native_checks.py'), '--seed', 'C:/work/echo38_5580_seed.L5X',
                '--output', str(output)], check=True, stdout=subprocess.DEVNULL)
assert sha(output) == sha(W/'s3i_bench_05.L5X') == SOURCE
for name in ('s3i_canonical.ACD', 'capacity_review.ACD', 'retention_control.ACD'):
    assert sha(W/name).upper() == ACD, name
report = dict(passed=True, sourceBindings=len(bindings), changed=sorted(changed), plcSourceUnchanged=True,
              acdUnchanged=True, sourceSha256=SOURCE, canonicalSha256=ACD,
              compileReadbackEvidence='AB_S3I_CANONICAL_PREPARATION_2026-10-24',
              capacityUsedBlocks=2763512, capacityAvailableBlocks=382216)
with (W/'unchanged_verification_01.json').open('x') as out:
    json.dump(report, out, indent=2)
print(json.dumps(report))

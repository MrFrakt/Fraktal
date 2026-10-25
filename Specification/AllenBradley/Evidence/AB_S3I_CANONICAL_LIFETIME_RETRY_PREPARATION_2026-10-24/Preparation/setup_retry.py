"""Prepare the S3i lifetime retry offline from the sealed preparation; no controller operations."""
from pathlib import Path
import gzip, hashlib, json, shutil

W = Path(__file__).parent
OLD = 'C:/work/fraktal-ab-s3i-lifetime-20261024/prepare_9af0ac9f71534d89b5be9645bdc6575f'
P = Path(OLD)
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
EV = ROOT/'Specification/AllenBradley/Evidence'
SEALED = EV/'AB_S3I_CANONICAL_LIFETIME_PREPARATION_2026-10-24'
S = SEALED/'Preparation'
ACD = 'A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
SOURCE = '0f3a5f6dd762bed3819404025daf6d5703511807b440c4988eacf5e494ec72c3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


manifest = json.loads((SEALED/'manifest.json').read_text())
for row in manifest['artifacts']:
    assert sha(SEALED/row['path']) == row['sha256'], row['path']

# Text files: the sealed copies, with only the workspace path rebound.
bound = {}
for name in ('scripts/guard_echo.py', 'scripts/preflight.py', 'scripts/retention_preflight.py',
             'scripts/retention_readiness.py', 'ensure_manual.py', 'final_checks.py', 'measure_timing.py',
             'audit_access.py', 'audit_baseline_access.py', 'retention_preflight_source.py',
             'retention_readiness_source.py', 'run_logged.py', 'test_authorization.py',
             'session/Program.cs', 'session/S3iLifetimeSession.csproj', 'session/NuGet.Config',
             'runtime_template/start_session.py', 'runtime_template/candidate_then_restore.py',
             'baseline_capacity.json', 'baseline_reference.json', 'canonical_prepared_compare.json',
             'capacity_review.json', 'authorization.template.json'):
    text = (S/name).read_text(encoding='utf-8')
    count = text.count(OLD)
    target = W/name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8', newline='') as out:
        out.write(text.replace(OLD, W.as_posix()))
    assert W.as_posix() in target.read_text(encoding='utf-8') or count == 0
    bound[name] = count
assert (S/'canonical.sha256').read_text().strip() == ACD
(W/'canonical.sha256').write_text(ACD, encoding='utf-8')
expanded = gzip.decompress((S/'s3i_bench_05.L5X.gz').read_bytes())
assert hashlib.sha256(expanded).hexdigest() == SOURCE
(W/'s3i_bench_05.L5X').write_bytes(expanded)

# Three fresh copies of the still-pristine Capacity review copy.
assert sha(P/'capacity_review.ACD').upper() == ACD
for name in ('s3i_canonical.ACD', 'capacity_review.ACD', 'retention_control.ACD'):
    assert not (W/name).exists()
    shutil.copyfile(P/'capacity_review.ACD', W/name)
    assert sha(W/name).upper() == ACD

prepared = json.loads((S/'authorization.json').read_text())
assert prepared['CurrentOwnerApproved'] is False
prepared.update(RuntimeDirectory=None, Scope='Prepared retry only; current owner approval required',
                RetryOf='Evidence/AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24.md')
with (W/'authorization.json').open('x') as out:
    json.dump(prepared, out, indent=2)
for name in ('preflight.json', 'deploy_attempt.json', 'backup.sha256', 'echo_before_s3i.ACD',
             'canonical_downloaded.L5X', 'genealogy_restored.L5X', 'retained_cycle.json'):
    assert not (W/name).exists(), name
with (W/'setup_retry_01.json').open('x') as out:
    json.dump(dict(passed=True, canonicalSha256=ACD, sourceSha256=SOURCE, pathOccurrencesRebound=bound,
                   sealedPreparationArtifactsVerified=len(manifest['artifacts']), controllerOperations=0,
                   authorization=False), out, indent=2)
print(json.dumps(dict(passed=True, rebound=sum(bound.values()), files=len(bound), controllerOperations=0)))

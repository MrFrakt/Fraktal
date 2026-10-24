"""Fresh one-shot workspace for the same pinned image; no native authority."""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).parent;OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pin=(OLD/'canonical.sha256').read_text().strip()
assert sha(OLD/'capacity_review.ACD').upper()==pin=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
assert not (OLD/'authorization.template.json').samefile(OLD/'authorization.json')
for source,target in (('capacity_review.ACD','s3h_canonical.ACD'),('capacity_review.ACD','capacity_review.ACD'),
    ('s3h_candidate_03.L5X','s3h_candidate_03.L5X'),('canonical.sha256','canonical.sha256'),
    ('canonical_prepared_readback.L5X','canonical_prepared_readback.L5X'),('canonical_prepared_compare.json','canonical_prepared_compare.json'),
    ('capacity_review.json','capacity_review.json'),('baseline_capacity.json','baseline_capacity.json'),
    ('baseline_reference.json','baseline_reference.json'),('native_summary_final.json','native_summary_final.json'),
    ('run_logged.py','run_logged.py')):
    assert not (P/target).exists();shutil.copyfile(OLD/source,P/target)
(P/'session').mkdir();(P/'scripts').mkdir()
for source,target in (('session/Program.cs','session/Program.cs'),('session/S3hSession.csproj','session/S3hSession.csproj'),
    ('session/NuGet.Config','session/NuGet.Config'),('scripts/guard_echo.py','scripts/guard_echo.py'),
    ('scripts/preflight.py','scripts/preflight.py'),('ensure_manual.py','ensure_manual.py'),
    ('final_checks.py','final_checks.py'),('measure_timing.py','measure_timing.py'),
    ('audit_access.py','audit_access.py'),('audit_baseline_access.py','audit_baseline_access.py')):
    text=(OLD/source).read_text().replace(OLD.as_posix(),P.as_posix())
    with (P/target).open('x') as f:f.write(text)
template=json.loads((OLD/'authorization.template.json').read_text());assert not template['CurrentOwnerApproved']
template.update(Scope=template['Scope']+'; unchanged-even polls paced at one millisecond inside the original budget',
    RetryOf='Evidence/AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md',CurrentOwnerApproved=False)
with (P/'authorization.template.json').open('x') as f:json.dump(template,f,indent=2)
reference=dict(passed=True,controllerChangesAuthorized=False,preparedAcdSha256=pin,
    imageSource=(OLD/'capacity_review.ACD').as_posix(),imageSourceSha256=pin,
    generatedSourceSha256=sha(P/'s3h_candidate_03.L5X'),
    unchangedNativeImage=True,capacityReusedByExactImageHash=True,
    capacityEvidence='Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23/Preparation/capacity_review.json',
    capacityEvidenceSha256=sha(OLD/'capacity_review.json'),
    nativeBuildEvidence='Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23/Preparation/native_summary_final.json',
    nativeBuildEvidenceSha256=sha(OLD/'native_summary_final.json'))
with (P/'prepared_image_reference.json').open('x') as f:json.dump(reference,f,indent=2)
print(json.dumps(reference))

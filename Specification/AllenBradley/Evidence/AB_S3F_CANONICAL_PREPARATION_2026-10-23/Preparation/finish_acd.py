import hashlib,json,shutil
from pathlib import Path
W=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
pin=(W/'canonical.sha256').read_text().strip()
assert sha(W/'s3f_canonical.ACD')==pin
assert not (W/'capacity_review.ACD').exists()
shutil.copyfile(W/'s3f_canonical.ACD',W/'capacity_review.ACD')
assert sha(W/'capacity_review.ACD')==pin
template=dict(CurrentOwnerApproved=False,Serial='601FC87B',CanonicalSha256=pin,
    FaultClearAuthorized=False,ManualNormalizationAuthorized=False,AccessVectorsAuthorized=False,
    ConfigurationVectorsAuthorized=False,Scope=[
    'guarded MANUAL normalization when needed; fresh preflight and backup',
    'Program/download/Run exact S3f candidate',
    'five-document restore, 31 inherited regressions and two inherited Access checks',
    'configuration queries for two pages, empty page and model bank; one station edit/restoration; class hiding/logout/login/restoration',
    'isolated store SAVE/LIST/EXPORT/IMPORT/LOAD/DELETE; absent-set refusal; four malformed provider response refusals',
    'paired equivalence, native record sizes and scan measurement',
    'hash-checked genealogy rollback, five-document restore and 31 baseline regressions',
    'MANUAL cleanup and final checks'])
with (W/'authorization.template.json').open('x') as f:json.dump(template,f,indent=2)
print(json.dumps(dict(passed=True,canonicalSha256=pin,controllerChangesAuthorized=False)))

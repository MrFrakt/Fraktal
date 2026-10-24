"""Pin the prepared ACD and issue an explicitly unapproved session template."""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
pin=(P/'canonical.sha256').read_text().strip();assert sha(P/'s3g_canonical.ACD')==pin
assert not (P/'capacity_review.ACD').exists();shutil.copyfile(P/'s3g_canonical.ACD',P/'capacity_review.ACD')
template=dict(CurrentOwnerApproved=False,Serial='601FC87B',CanonicalSha256=pin,
    ManualNormalizationAuthorized=False,AccessVectorsAuthorized=False,ConfigurationVectorsAuthorized=False,
    NativeMetricsVectorsAuthorized=False,FaultClearAuthorized=False,ClockSetAuthorized=False,
    Scope=['fresh identity/MANUAL preflight/backup; Program/download/Run of the exact S3g ACD',
    'first-scan native bench: nine fixed OEE arithmetic vectors; two high-bit profiler rows; six DINT owner cells saved/restored in the same scan',
    'five-document restore; 31 inherited regressions, two Access and eight configuration cases; read-only 3672/3622/3272-path paired captures',
    'read-only native vector verification, record sizes and scan; genealogy rollback; five-document restore and 31 baseline regressions',
    'MANUAL normalization/cleanup; Run/not faulted/scanning/idle/logout/not-restoring; saved documents and policy equal'])
with (P/'authorization.template.json').open('x') as f:json.dump(template,f,indent=2)
print(json.dumps(dict(passed=True,preparedAcdSha256=pin,currentOwnerApproved=False)))

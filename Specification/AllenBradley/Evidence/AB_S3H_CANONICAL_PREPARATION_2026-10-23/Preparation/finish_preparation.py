from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).parent
pin=(P/'canonical.sha256').read_text().strip()
assert hashlib.sha256((P/'s3h_canonical.ACD').read_bytes()).hexdigest().upper()==pin
assert not (P/'capacity_review.ACD').exists()
shutil.copyfile(P/'s3h_canonical.ACD',P/'capacity_review.ACD')
scope=dict(Serial='601FC87B',CanonicalSha256=pin,CurrentOwnerApproved=False,
    ManualNormalizationAuthorized=False,AccessVectorsAuthorized=False,ConfigurationVectorsAuthorized=False,
    FaultClearAuthorized=False,ClockSetAuthorized=False,
    CandidateRows=41,BaselineRows=31,
    Scope='Guarded MANUAL normalization when needed; fresh preflight/backup; Program/download/Run; five-document restore and inherited 41 candidate checks with read-only traceability/decision/held/fault/sequence/reset/access/config captures; read-only all-path equivalence/sizes/native TASK scan; hash-checked genealogy rollback, five-document restore and 31 baseline regressions; MANUAL cleanup and final checks',
    NoAddedDirectTraceabilityWrites=True)
with (P/'authorization.template.json').open('x') as f:json.dump(scope,f,indent=2)
print(json.dumps(dict(passed=True,preparedAcdSha256=pin,controllerChangesAuthorized=False)))

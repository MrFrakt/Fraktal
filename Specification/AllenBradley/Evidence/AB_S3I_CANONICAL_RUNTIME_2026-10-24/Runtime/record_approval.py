"""Bind the current owner reply to the unchanged, sealed S3i preparation."""
from pathlib import Path
import datetime,gzip,hashlib,json,shutil
R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3i-20261024/prepare_d6df75f72d02435aab2ef3fbd7ea986d')
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence'
NAME='AB_S3I_CANONICAL_PREPARATION_2026-10-24'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
d=json.loads((E/NAME/'manifest.json').read_text(encoding='utf-8'))
assert sha(E/d['report'])==d['reportSha256']
for row in d['artifacts']:
    p=E/NAME/row['path'];raw=p.read_bytes();assert sha(p)==row['sha256'] and len(raw)==row['bytes'],row['path']
    if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256']
bindings=json.loads((E/NAME/'Preparation/source_bindings_01.json').read_text())['sha256']
assert len(bindings)==170 and all(sha(ROOT/name)==pin for name,pin in bindings.items())
pin='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
assert d['preparedAcdSha256']==pin==sha(W/'s3i_canonical.ACD').upper()==sha(W/'capacity_review.ACD').upper()
assert sha(W/'s3i_bench_05.L5X')==d['sourceSha256']
for name in ('preflight.json','deploy_attempt.json','backup.sha256','echo_before_s3i.ACD','canonical_downloaded.L5X','genealogy_restored.L5X'):
    assert not (W/name).exists(),name
# The executable and every session script must still equal the sealed source.
for name in ('session/Program.cs','scripts/guard_echo.py','scripts/preflight.py','ensure_manual.py','final_checks.py','measure_timing.py'):
    assert sha(W/name)==sha(E/NAME/'Preparation'/name),name
sdk=W/'session/bin/Debug/net8.0/win-x86/S3iSession.exe'
approval=dict(CurrentOwnerApproved=True,Serial='601FC87B',CanonicalSha256=pin,SourceSha256=d['sourceSha256'],
    ManualNormalizationAuthorized=True,AccessVectorsAuthorized=True,ConfigurationVectorsAuthorized=True,
    NativeLineVectorsAuthorized=True,FaultClearAuthorized=False,ClockSetAuthorized=False,
    CandidateRows=41,BaselineRows=31,FirstScanPublicationVectors=8,
    CalendarProducerLifetimeAcceptanceIncluded=False,ObservationFrameAcquisition=True,
    ApprovalQuestion='call_857f749a9e6d4fd6a69515d2b6e226ab:0',ApprovalAnswer='Approve this guarded S3i session',
    Scope='Guarded MANUAL normalization if needed; fresh backup; Program/download/Run; eight fixed first-scan Line/shift publication vectors with exact owner restoration; five-document restore and 41 candidate cases with read-only equivalence/sizes/scan; genealogy rollback, five-document restore and 31 baseline cases; cleanup/final checks',
    Excluded=['fault clear','clock change','firmware/network change','power-state operation','hard kill','vendor-state edit'],
    ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),RuntimeDirectory=R.as_posix(),
    PreparationManifestSha256=sha(E/NAME/'manifest.json'),PreparationReportSha256=d['reportSha256'],
    SessionExecutableSha256=sha(sdk),SessionAssemblySha256=sha(sdk.with_suffix('.dll')),SessionSourceSha256=sha(W/'session/Program.cs'))
old=json.loads((W/'authorization.json').read_text());assert old['CurrentOwnerApproved'] is False and old['NativeLineVectorsAuthorized'] is False
assert sha(W/'authorization.json')==sha(E/NAME/'Preparation/authorization.json')
# Preserve the complete former working file before creating the live control
# file. Every evidence destination is new, and the sealed payload is untouched.
destination=R/'preapproval_working_authorization.json';assert not destination.exists()
(W/'authorization.json').rename(destination)
for path in (W/'authorization.json',R/'owner_session_approval.json'):
    with path.open('x',encoding='utf-8') as f:json.dump(approval,f,indent=2)
with (R/'initial_source_verification.json').open('x') as f:
    json.dump(dict(passed=True,sourceBindings=170,sha256=bindings,preparedAcdSha256=pin,
        sourceSha256=d['sourceSha256'],sessionExecutableSha256=sha(sdk),sessionAssemblySha256=sha(sdk.with_suffix('.dll'))),f,indent=2)
print(json.dumps(dict(passed=True,sourceBindings=170,preparedAcdSha256=pin,controllerOperations=0)))

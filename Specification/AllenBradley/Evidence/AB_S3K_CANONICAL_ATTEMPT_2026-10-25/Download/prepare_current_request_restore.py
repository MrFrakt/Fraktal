"""Record the owner's current request/restore approval without editing old evidence."""
from pathlib import Path
import datetime,hashlib,json
D=Path(__file__).parent
S3J=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
GENEALOGY='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
pin=(D/'canonical.sha256').read_text().strip()
assert pin=='5B62CAC28C8EB5A819850D49FC854123C0B0B00449E2E8663FAC08B96C3000F6'
instruction='please continue, run request cases **then restore genealogy**'
common=dict(CurrentOwnerApproved=True,OwnerInstruction=instruction,
    RecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),Serial='601FC87B',
    CanonicalSha256=pin,GenealogySha256=GENEALOGY,MailboxOrTagWritesAuthorized=True,
    RestoreGenealogyAuthorized=True,BaselineRegressionWritesAuthorized=True,ManualNormalizationAuthorized=True,
    DownloadAuthorized=False,BackupUploadAuthorized=False,FaultClearAuthorized=False,ClockSetAuthorized=False,
    PowerOperationsAuthorized=False,VendorStateEditsAuthorized=False,
    Scope='Run the prepared S3k request session on the already-loaded pinned image: inherited 41 cases, typed vectors and collision observation, read-only equivalence/acquisition/timing. Then Program/download/Run of a hash-checked copy of pinned genealogy, five-document restore, 31 baseline cases, guarded MANUAL cleanup, final checks and preflight. Stop candidate work at first failure; restore still follows if the exact-target/fault/logout guards pass. No S3k redownload, fault clear, clock set or power operation.')
for name in ('request_authorization.json','restore_authorization.json'):
    with (D/name).open('x',encoding='utf-8') as out:json.dump(common,out,indent=2)
# A restore-only executable, preserving every identity/hash/SDK guard. The
# original download-only authorization and executable remain historical.
out=D/'restore_session';out.mkdir(exist_ok=False)
source=(D/'session/Program.cs').read_text()
old='var modes=new[]{"backup","deploy-canonical","restore-genealogy"};'
assert source.count(old)==1
source=source.replace(old,'var modes=new[]{"restore-genealogy"};')
source=source.replace('Path.Combine(root,"authorization.json")','Path.Combine(root,"restore_authorization.json")')
assert source.count('restore_authorization.json')==2
with (out/'Program.cs').open('x',encoding='utf-8') as f:f.write(source)
with (out/'S3kRestore.csproj').open('xb') as f:f.write((D/'session/S3kSession.csproj').read_bytes())
# Reuse the accepted baseline MANUAL helper with this current approval, not
# the old S3j approval file. Its exact genealogy and idle/logout guards stay.
manual=(S3J/'ensure_manual.py').read_text()
manual=manual.replace("(W/'authorization.json')","(W/'restore_authorization.json')")
manual=manual.replace("str(W/'scripts/guard_echo.py')",repr(str(S3J/'scripts/guard_echo.py')))
with (D/'ensure_manual_baseline.py').open('x',encoding='utf-8') as f:f.write(manual)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with (D/'current_authorization_preparation_01.json').open('x') as f:
    json.dump(dict(passed=True,authorizationInstruction=instruction,canonicalSha256=pin,genealogySha256=GENEALOGY,
        helperSources={p.name:sha(p) for p in (out/'Program.cs',out/'S3kRestore.csproj',D/'ensure_manual_baseline.py')},
        originalAuthorizationSha256=sha(D/'authorization.json'),controllerOperations=0),f,indent=2)
print(json.dumps(dict(passed=True,authorizationRecorded=True,restoreOnlyHelperPrepared=True,controllerOperations=0)))

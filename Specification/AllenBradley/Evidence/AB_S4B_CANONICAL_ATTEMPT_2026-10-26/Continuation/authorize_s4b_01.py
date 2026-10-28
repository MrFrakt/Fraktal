"""Record the owner's current exact-image grant after immutable checks."""
from pathlib import Path
import datetime,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence/AB_S4B_FROZEN_PACKAGE_PREPARATION_2026-10-26'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_bytes())
assert sha(E.parent/m['report'])==m['reportSha256']
for row in m['artifacts']:
    p=E/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],row['path']
b=json.loads((D/'source_bindings_02.json').read_bytes())
assert sha(D/'source_bindings_02.json')==m['sourceBindingsSha256']
for path,pin in b['sha256'].items():assert sha(Path(path)).upper()==pin,path
assert not any((D/n).exists() for n in ('authorization.json','session_started.json','deploy_attempt.json','echo_before_s4b.ACD'))
value=json.loads((D/'authorization.template.json').read_bytes())
value.update(CurrentOwnerApproved=True,OwnerInstruction='Approve guarded S4b qualification',
    ApprovalQuestion='call_298845fc9dc04b9c89398259d6673bfa:0',
    ApprovalRecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    ApprovedPreparationManifestSha256=sha(E/'manifest.json'))
for key in ('BackupUploadAuthorized','DownloadAuthorized','MailboxOrTagWritesAuthorized','ManualNormalizationAuthorized',
    'RestoreGenealogyAuthorized','BaselineRegressionWritesAuthorized','DartReadQualificationAuthorized'):value[key]=True
for key in ('FaultClearAuthorized','ClockSetAuthorized','PowerOperationsAuthorized','VendorStateEditsAuthorized'):assert value[key] is False
with (D/'authorization.json').open('x',encoding='utf-8',newline='') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(approved=True,serial=value['Serial'],acdSha256=value['CanonicalSha256'],sourceBindingsVerified=len(b['sha256']),
    question=value['ApprovalQuestion'],faultClear=False,clockChanges=False,powerOperations=False)))

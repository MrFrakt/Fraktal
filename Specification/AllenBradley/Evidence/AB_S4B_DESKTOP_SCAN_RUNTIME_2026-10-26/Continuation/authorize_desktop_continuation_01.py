from pathlib import Path
import hashlib
import json

W=Path(__file__).parent
previous=W.parent/'desktop_scan_01'
old=json.loads((previous/'authorization.json').read_bytes())
result=json.loads((previous/'session_result.json').read_bytes())
assert old['ApprovalQuestion']=='call_6c35ecad4ba84714a17ec9b7b68f5ad4:0'
assert old['OwnerInstruction']=='Approve guarded S4b desktop/scan session'
assert old['ApprovedPreparationManifestSha256']=='99526bd8dd48f23b462c7ae0730366dbda1ecb34d8790d707416f4c6e4fdf0f3'
assert not (previous/'deploy_attempt.json').exists()
assert json.loads((previous/'manual_initial.json').read_bytes())['controllerWrites']==0
assert result['candidateError'].startswith('JSONDecodeError:') and not result['dumpFiles']
original=W/'authorize_lookup_retry_01.py'
archived=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26/Continuation/authorize_lookup_retry_01.py')
assert original.read_bytes()==archived.read_bytes()
source=original.read_text(encoding='utf-8')
for before,after in {
    "D = Path('C:/work/fraktal-ab-s4b-20261025/retry_lookup_01')":"D = Path('C:/work/fraktal-ab-s4b-20261025/desktop_scan_continue_01')",
    'AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26':'AB_S4B_DESKTOP_SCAN_CONTINUATION_2026-10-26',
    '7da9844267de8f3c0a080bec16b8144960e17c1f4ec2813cdd2d3dc32c332ff5':'93a355a260bf7412f4e02ee13c1fdc5c66ea503832a9cbb90137a1c27bf6d0e7',
    'qualification_lookup_retry':'qualification_desktop_scan_continuation',
    'Approve guarded S4b lookup retry':'Approve guarded S4b desktop/scan session',
    'call_2b13d9faea7945c9803fd0d2782b3c10:0':'call_6c35ecad4ba84714a17ec9b7b68f5ad4:0',
    'spec.loader.exec_module(module)':'import sys\nsys.path.insert(0,str(D))\nspec.loader.exec_module(module)',
    'module.authorize(approval)':"""approval.update(OriginalAuthorizationSha256=hashlib.sha256((D.parent/'desktop_scan_01/authorization.json').read_bytes()).hexdigest(),
    OriginalApprovedPreparationManifestSha256='99526bd8dd48f23b462c7ae0730366dbda1ecb34d8790d707416f4c6e4fdf0f3',
    AuthorizationContext='Same current instruction; previous attempt stopped before download and writes; readiness-only correction',
    TaskCounterClearAuthorized=False)
module.authorize(approval)""",
}.items():
    assert source.count(before)==1,before
    source=source.replace(before,after)
exec(compile(source,str(original),'exec'),{'__file__':__file__})

"""Prepare a new, unapproved S4a qualification session; no controller access."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
W=Path(__file__).parent
D=W.parent/'session_01'
OLD=Path('C:/work/fraktal-ab-s3k-20261025/retry_login_01')
D.mkdir();(D/'scripts').mkdir();(D/'session').mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
PIN=sha(W/'command_a_02.ACD');SOURCE=sha(W/'s3k_command_a_02.L5X')
assert PIN=='07C54E8DCE8D70A1EC487684B65F3596922D615448881AA05470304821CC2FF3'
capacity=json.loads((W/'capacity_auto_02.json').read_bytes())
assert capacity['CanonicalSha256']==PIN and capacity['VerifiedFit']

def save(name,text):
    with (D/name).open('x',encoding='utf-8',newline='') as stream:stream.write(text)
def copy_text(source,target):
    value=(OLD/source).read_text().replace(OLD.as_posix(),D.as_posix())
    value=value.replace('fraktal_ab_genealogy_s3k_demo','fraktal_ab_genealogy_s4_demo')
    value=value.replace('s3k_command_a','s4a_coherence').replace('echo_before_s3k','echo_before_s4a')
    value=value.replace('S3kSession','S4Session').replace('S3k','S4a')
    save(target,value)

for name in ('run_logged.py','scripts/guard_echo.py','scripts/preflight.py',
             'ensure_manual_baseline.py','ensure_manual_candidate.py','pre_restore_guard.py',
             'restore_original_medium.py'):
    copy_text(name,name)
copy_text('session/Program.cs','session/Program.cs')
copy_text('session/S3kSession.csproj','session/S4Session.csproj')
save('audit_access.py',(W/'audit_access.py').read_text())
shutil.copyfile(W/'command_a_02.ACD',D/'s4a_coherence.ACD')
shutil.copyfile(W/'s3k_command_a_02.L5X',D/'s4a_coherence.L5X')
save('canonical.sha256',PIN+'\n')
save('genealogy.sha256','D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084\n')
save('capacity_review.json',json.dumps(capacity,indent=2)+'\n')
comparison=json.JSONDecoder().raw_decode((W/'prepared_compare_02.log').read_text().lstrip())[0]
assert comparison['Equivalent']
save('canonical_prepared_compare.json',json.dumps(comparison,indent=2)+'\n')
approval=json.loads((OLD/'authorization.template.json').read_bytes())
approval.update(CanonicalSha256=PIN,SourceSha256=SOURCE,ReadGroupProbeAuthorized=False,
    PowerOperationsAuthorized=False,VendorStateEditsAuthorized=False,
    Scope='Fresh guards/backup; guarded MANUAL normalization; Program/download/Run of exact V6.7 image; '
          'five-document restore and 31 candidate cases; read-only paired equivalence, generic acquisition, '
          '100 bounded small-group acquisitions per planned row with published counter progress, native scan; '
          'pinned genealogy rollback and exact original host-document restoration, five-document restore and '
          '31 baseline cases; MANUAL cleanup/final checks/preflight. No fault clear, clock, power or vendor-state operation.')
approval['OwnerCapacityConfirmed']={k:capacity[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent')}
save('authorization.template.json',json.dumps(approval,indent=2)+'\n')
session=(OLD/'retry_session.py').read_text().replace(OLD.as_posix(),D.as_posix())
session=session.replace('AA4239C636647527CC37F3B3F18206821FBEE108D3315C5087DC0DCD1653BBDF',PIN)
session=session.replace('B543336202821F95BC41A5A51441E86021F1BA9EFF28D42FABCD1AA83D7C782A',SOURCE)
session=session.replace('fraktal_ab_genealogy_s3k_demo','fraktal_ab_genealogy_s4_demo')
session=session.replace('s3k_command_a','s4a_coherence').replace('echo_before_s3k','echo_before_s4a').replace('S3kSession','S4Session')
session=session.replace("'BaselineRegressionWritesAuthorized')","'BaselineRegressionWritesAuthorized', 'ReadGroupProbeAuthorized')")
session=session.replace("('FaultClearAuthorized', 'ClockSetAuthorized')","('FaultClearAuthorized', 'ClockSetAuthorized', 'PowerOperationsAuthorized', 'VendorStateEditsAuthorized')")
start=session.index("        run('request_cases'");end=session.index("        run('generic_acquire'",start)
session=session[:start]+'''        run('candidate_regressions', PY, D / 'candidate_regressions.py', '--execute-fixture',
            '--expect-serial', '601FC87B', '--credential-file', CREDENTIAL,
            '--output', D / 'candidate_regressions.json')
        run('idle_equivalence', PY, D / 'candidate_equivalence.py', '--expect-serial', '601FC87B',
            '--output', D / 'idle_equivalence.json.gz')
'''+session[end:]
position=session.index("        run('candidate_timing'")
session=session[:position]+'''        run('read_group_qualification', PY, T / 'fraktal_ab_read_group_probe.py', '--expect-serial', '601FC87B',
            '--iterations', '100', '--output', D / 'read_group_qualification.json.gz')
'''+session[position:]
save('qualification_session.py',session.replace('S3k','S4a').replace('complete request/rollback','complete qualification/rollback'))
save('candidate_regressions.py','''"""Only the existing 31 genealogy vectors on the exact authorized V6.7 image."""
from pathlib import Path
import json,os,sys
D=Path(__file__).parent
sys.path.insert(0,str(D))
from qualification_session import authorize
authorize(json.loads((D/'authorization.json').read_bytes()))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from fraktal_ab_genealogy_execute import main
if __name__=='__main__':raise SystemExit(main(expected_declaration='fraktal_ab_genealogy_s4_demo'))
''')
save('candidate_equivalence.py','''"""Migration-only value equivalence, independent of shipping small-group proof."""
import sys
from functools import partial
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_genealogy_s4_demo as candidate
import fraktal_ab_s3k_equivalence as oracle
import fraktal_ab_s2_equivalence as shared
if __name__=='__main__':raise SystemExit(shared.main(partial(oracle.run,candidate_factory=candidate.application),description=__doc__))
''')
print(json.dumps(dict(prepared=True,session=str(D),acdSha256=PIN,sourceSha256=SOURCE,
                     capacity=capacity['DisplayedUsagePercent'],controllerAccess=False,currentOwnerApproved=False)))

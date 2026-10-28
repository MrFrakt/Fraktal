"""Sealable guarded S4b fixture preparation only; no controller operations."""
from pathlib import Path
import hashlib,json,shutil
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01'
OLD=Path('C:/work/fraktal-ab-s4-20261025/session_01')
PIN='7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
SOURCE='C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F'
D.mkdir();(D/'scripts').mkdir();(D/'session').mkdir()
def save(path,text):
    with (D/path).open('x',encoding='utf-8',newline='') as stream:stream.write(text)
def transform(text):
    return (text.replace(OLD.as_posix(),D.as_posix()).replace('s4a_coherence','s4b_read_view').replace('echo_before_s4a','echo_before_s4b')
        .replace('fraktal_ab_genealogy_s4_demo','fraktal_ab_genealogy_s4b_demo').replace('S4a','S4b').replace('S4Session','S4bSession')
        .replace('07C54E8DCE8D70A1EC487684B65F3596922D615448881AA05470304821CC2FF3',PIN)
        .replace('20F27F80CF9D0AEFEFA72EB64848927AE6076CF05CB544073575A55728825996',SOURCE))
for path in ('run_logged.py','scripts/guard_echo.py','scripts/preflight.py','ensure_manual_baseline.py','ensure_manual_candidate.py',
    'pre_restore_guard.py','restore_original_medium.py','session/Program.cs'):
    save(path,transform((OLD/path).read_text()))
save('session/S4bSession.csproj',(OLD/'session/S4Session.csproj').read_text())
save('audit_access.py',(W/'audit_access.py').read_text())
shutil.copyfile(W/'canonical_read_view_01.ACD',D/'s4b_read_view.ACD')
shutil.copyfile(W/'canonical_read_view_01.L5X',D/'s4b_read_view.L5X')
save('canonical.sha256',PIN+'\n');save('genealogy.sha256',(OLD/'genealogy.sha256').read_text())
capacity=json.loads((W/'capacity_auto_01.json').read_bytes());assert capacity['VerifiedFit'] and capacity['CanonicalSha256']==PIN
save('capacity_review.json',json.dumps(capacity,indent=2)+'\n')
comparison=json.JSONDecoder().raw_decode((W/'prepared_compare_01.log').read_text().lstrip())[0];assert comparison['Equivalent']
save('canonical_prepared_compare.json',json.dumps(comparison,indent=2)+'\n')
approval=json.loads((OLD/'authorization.template.json').read_bytes())
approval.update(CanonicalSha256=PIN,SourceSha256=SOURCE,ReadGroupProbeAuthorized=False,DartReadQualificationAuthorized=False,
    OwnerCapacityConfirmed={k:capacity[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent')},
    Scope='Fresh exact guards and backup; guarded MANUAL normalization; Program/download/Run of V6.8; '
    'five-document restore and the inherited 41 candidate cases (31 main, two Access, eight configuration/set-store), with original values restored; '
    'concurrent read-only Dart worker/tier/row/liveness observer, then read-only all-bank configuration and chart detail queries; '
    'all-path legacy-oracle equivalence, generic acquisition and native scan; pinned genealogy rollback, exact original host documents, '
    'five-document restore and 31 baseline cases; MANUAL cleanup/final checks/preflight. No typed command vectors, fault clear, clock, power or vendor-state edits.')
save('authorization.template.json',json.dumps(approval,indent=2)+'\n')
session=transform((OLD/'qualification_session.py').read_text()).replace("'ReadGroupProbeAuthorized')","'DartReadQualificationAuthorized')")
start=session.index("        run('read_group_qualification'");end=session.index("        run('candidate_timing'",start)
session=session[:start]+session[end:]
save('qualification_session.py',session)
save('candidate_equivalence.py','''import sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_s4b_equivalence as gate
import fraktal_ab_s2_equivalence as shared
if __name__=='__main__':raise SystemExit(shared.main(gate.run,description=gate.__doc__))
''')
save('candidate_regressions.py','''"""The inherited 41 fixed writes; concurrent observer is strictly read-only."""
from pathlib import Path
import json,os,subprocess,sys,time
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0,str(D))
from qualification_session import authorize
authorize(json.loads((D/'authorization.json').read_bytes()))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_demo'
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_genealogy_s4b_demo as candidate
import fraktal_ab_s4b_equivalence as equivalence
import fraktal_ab_s3f_fixture_execute as fixture
def paired(destination):
    return fixture.paired_run(destination,candidate_factory=candidate.application,equivalence_gate=equivalence.run,prefix='s4b')
def main():
    ready=D/'dart_ready.json';stop=D/'dart_stop.json';output=D/'dart_qualification.json.gz'
    assert not any(p.exists() for p in (ready,stop,output,D/'dart_qualification.log'))
    command=['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe',
      '--packages='+str(R/'FraktalCore/HMI/.dart_tool/package_config.json'),str(R/'FraktalCore/HMI/tool/qualify_cip_canonical.dart'),
      '--endpoint','cip://127.0.0.1?slot=0&serial=601FC87B','--output',str(output),'--samples','10000','--ready-file',str(ready),'--stop-file',str(stop)]
    result=1;failure=None
    with (D/'dart_qualification.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=R/'FraktalCore/HMI',stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline=time.monotonic()+90
            while not ready.exists():
                if process.poll() is not None:raise RuntimeError('read-only Dart qualification failed before candidate writes')
                if time.monotonic()>deadline:raise RuntimeError('read-only Dart readiness deadline exceeded')
                time.sleep(.05)
            if json.loads(ready.read_bytes())!={'ready':True,'readOnly':True,'sample':0}:raise ValueError('invalid observer readiness')
            result=genealogy.main(run_type_factory=paired,schema='fraktal.ab.s4b-genealogy-fixture',expected_declaration='fraktal_ab_genealogy_s4b_demo')
        except BaseException as error:
            failure=error
        finally:
            with stop.open('x') as stream:json.dump(dict(stop=True),stream)
            try:observer=process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                # This terminates only this read-only Dart helper, never Echo.
                process.kill();process.wait(timeout=10);observer=1
            with (D/'dart_observer_exit.json').open('x') as stream:json.dump(dict(exitCode=observer,command=command),stream,indent=2)
    if failure is not None:raise failure
    return result if result else observer
if __name__=='__main__':raise SystemExit(main())
''')
print(json.dumps(dict(prepared=True,authorized=False,session=str(D),acdSha256=PIN,sourceSha256=SOURCE,capacityPercent=capacity['DisplayedUsagePercent'])))

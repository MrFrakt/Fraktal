"""The inherited 41 fixed writes; concurrent observer is strictly read-only."""
from pathlib import Path
import json,os,subprocess,sys,time
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0,str(D))
from qualification_session_v2 import authorize
from session_ready import wait_for_ready
authorize(json.loads((D/'authorization.json').read_bytes()))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_demo'
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_genealogy_s4b_demo as candidate
import fraktal_ab_s4b_equivalence as equivalence
import fraktal_ab_s3f_fixture_execute as fixture
def paired(destination):
    from login_busy_witness import with_busy_witness
    parent=fixture.paired_run(destination,candidate_factory=candidate.application,equivalence_gate=equivalence.run,prefix='s4b')
    return with_busy_witness(parent,destination)
def main():
    ready=D/'dart_ready.json';stop=D/'dart_stop.json';output=D/'dart_qualification.json.gz'
    assert not any(p.exists() for p in (ready,stop,output,D/'dart_qualification.log'))
    command=['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe','-Dfraktal.cip.trace=true',
      '--packages='+str(D/'dart_package_config.json'),str(R/'FraktalCore/HMI/tool/qualify_cip_canonical.dart'),
      '--endpoint','cip://127.0.0.1?slot=0&serial=601FC87B','--output',str(output),'--samples','10000','--ready-file',str(ready),'--stop-file',str(stop)]
    result=1;failure=None
    with (D/'dart_qualification.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=R/'FraktalCore/HMI',stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            wait_for_ready(ready,dict(ready=True,readOnly=True,sample=0),process,timeout=90)
            from part_read_diagnostics import trace_part_reads
            with trace_part_reads(D/'part_read_diagnostics.jsonl'):
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

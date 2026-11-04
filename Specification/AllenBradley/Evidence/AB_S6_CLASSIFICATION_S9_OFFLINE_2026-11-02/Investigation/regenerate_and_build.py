"""Regenerate the accepted S5 source, then run both offline v38 targets only."""
from pathlib import Path
import hashlib,json,subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
T=R/'FraktalCore/PLC/Allen-Bradley/tools'
source=W/'s5_regenerated_01.L5X'
def run(label,*args):
    subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,args)],cwd=R,check=True)
assert not source.exists()
run('regenerate_s5_01',sys.executable,T/'fraktal_ab_generate.py','C:/work/echo38_5580_seed.L5X',source,
    '--declaration','fraktal_ab_genealogy_s4b_owner_demo')
digest=hashlib.sha256(source.read_bytes()).hexdigest().upper()
assert digest=='979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162',digest
sdk=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
for target in ('EchoController','PhysicalController'):
    output=W/(target+'_s5_readback_01.L5X')
    assert not output.exists()
    run('build_'+target+'_01',sdk,'--build-readback',source,output,target)
    run('readback_'+target+'_01',sys.executable,T/'fraktal_ab_readback.py',source,output)
    run('audit_'+target+'_01',sys.executable,T/'fraktal_ab_sdk_log_gate.py',W/('build_'+target+'_01.log'),
        '--require','Open project','--require','Build','--require','Save As')
value=dict(passed=True,generatedSourceByteIdenticalToS5=True,sourceSha256=digest,
    v38Targets=['EchoController','PhysicalController'],buildReadbackAndSdkAuditPassed=True,
    controllerAccess=False,downloads=0,originalGenealogyAcdOpened=False)
with (W/'regeneration_and_build_result_01.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
print(json.dumps(value))

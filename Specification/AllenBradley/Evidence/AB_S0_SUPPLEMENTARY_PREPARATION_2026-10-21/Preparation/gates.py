from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).resolve().parent
TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(TOOLS))

def save(name,document):
    with (WORK/name).open('x',encoding='utf-8') as out:
        json.dump(document,out,indent=2);out.write('\n')

def run(name,command):
    tick=time.monotonic()
    with (WORK/name).open('x',encoding='utf-8') as out:
        result=subprocess.run([str(v) for v in command],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
    row=dict(log=name,command=[str(v) for v in command],exitCode=result.returncode,seconds=round(time.monotonic()-tick,3))
    print(json.dumps(row),flush=True)
    return row

if sys.argv[1]=='offline':
    rows=[run(name,command) for name,command in [
        ('ab_suite_final.log',[sys.executable,'-m','unittest','discover','-s',TOOLS,'-t',TOOLS]),
        ('root_tests_final.log',[sys.executable,'-m','unittest','tools.test_check_ab_spec','tools.test_check_ab_contracts','tools.test_check_consistency']),
        ('spec_final.log',[sys.executable,'tools/check_ab_spec.py']),
        ('contracts_final.log',[sys.executable,'tools/check_ab_contracts.py']),
        ('consistency_final.log',[sys.executable,'tools/check_consistency.py','--strict']),
        ('diff_check_final.log',['git','diff','--check'])]]
    save('offline_summary.json',dict(rows=rows,passed=all(r['exitCode']==0 for r in rows)))
elif sys.argv[1]=='native':
    from fraktal_ab_readback import compare
    from fraktal_ab_sdk_log_gate import audit_log
    report=json.loads((WORK/'generated_final/generation.json').read_text())
    binary=TOOLS/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
    rows=[]
    reused={'literal':('literal_Echo_08.log','literal_Echo_08.L5X','generated_08/s0s_literal.L5X'),
            'combined':('combined_Echo_08.log','combined_Echo_08.L5X','generated_08/s0s_combined.L5X'),
            'limit':('limit_Echo_04.log','limit_Echo_04.L5X','generated_04/s0s_limit.L5X'),
            'over_limit':('over_limit_Echo_08.log',None,'generated_08/s0s_over_limit.L5X')}
    for target in ('EchoController','PhysicalController'):
        for case in report['cases']:
            key=case['case'];source=Path(case['output'])
            if target=='EchoController' and key in reused:
                log_name,export,old_source=reused[key]
                assert (WORK/old_source).read_bytes()==source.read_bytes()
                log=(WORK/log_name).read_text(encoding='utf-8')
                row=dict(case=key,target=target,log=log_name,reusedIdenticalSource=True,
                         sourceSha256=case['sha256'],exitCode=0 if export else 3762504530)
                output=WORK/export if export else None
            else:
                output=WORK/f'final_{key}_{target}.L5X'
                row=run(f'final_{key}_{target}.log',[binary,'--build-readback',source,output,target])
                row.update(case=key,target=target,sourceSha256=case['sha256'])
                log=(WORK/row['log']).read_text(encoding='utf-8')
            row['sourceUnchanged']=hashlib.sha256(source.read_bytes()).hexdigest().upper()==case['sha256'].upper()
            if case['expectedBuild']=='reject-size':
                row['expectedRejectionObserved']=row['exitCode']!=0 and 'XMLSrv_E_IMPORT_ABORTED_NO_CHANGES' in log
                row['passed']=row['sourceUnchanged'] and row['expectedRejectionObserved']
                row['inference']='Only an Extra DINT above 2 MiB differs from the exact-limit case; under-limit Extra and exact-limit controls must also pass.'
            else:
                row['sdkAudit']=audit_log(log,('Open project','Build','Save As'),True)
                row['readback']=compare(source,output) if output and output.exists() else None
                row['passed']=row['exitCode']==0 and row['sourceUnchanged'] and row['sdkAudit']['Clean'] and row['readback'] and row['readback']['Equivalent']
            rows.append(row)
            print(json.dumps(dict(case=key,target=target,passed=bool(row['passed']))),flush=True)
    save('native_summary.json',dict(rows=rows,passed=all(bool(r['passed']) for r in rows)))
else:
    raise SystemExit('unknown mode')

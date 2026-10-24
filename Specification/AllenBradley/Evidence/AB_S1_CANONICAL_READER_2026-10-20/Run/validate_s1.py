from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path(__file__).resolve().parent
TOOLS = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0, str(TOOLS))

def save(name, data):
    with (WORK/name).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')

def run(name, command):
    tick=time.monotonic()
    with (WORK/name).open('x', encoding='utf-8') as stream:
        result=subprocess.run([str(v) for v in command], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, text=True)
    row=dict(log=name, command=[str(v) for v in command], exitCode=result.returncode, seconds=round(time.monotonic()-tick,3))
    print(json.dumps(row),flush=True)
    return row

mode=sys.argv[1]
if mode=='offline':
    checks=[('ab_suite.log',[sys.executable,'-m','unittest','discover','-s',TOOLS,'-t',TOOLS]),
            ('root_tests.log',[sys.executable,'-m','unittest','tools.test_check_ab_spec','tools.test_check_ab_contracts','tools.test_check_consistency']),
            ('ab_spec.log',[sys.executable,'tools/check_ab_spec.py']),
            ('ab_contracts.log',[sys.executable,'tools/check_ab_contracts.py']),
            ('consistency_strict.log',[sys.executable,'tools/check_consistency.py','--strict']),
            ('diff_check.log',['git','diff','--check'])]
    rows=[run(name,command) for name,command in checks]
    save('offline_summary.json',dict(rows=rows,passed=all(r['exitCode']==0 for r in rows)))
    raise SystemExit(0 if all(r['exitCode']==0 for r in rows) else 1)
elif mode=='native':
    import fraktal_ab_readback as readback
    from fraktal_ab_sdk_log_gate import audit_log
    source=Path('C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7/corrected_combined/s0_combined.L5X')
    binary=TOOLS/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    rows=[]
    for target in ('EchoController','PhysicalController'):
        output=WORK/f'probe_{target}_readback.L5X'
        row=run(f'probe_{target}_build.log',[binary,'--build-readback',source,output,target])
        row['target']=target
        row['sdkAudit']=audit_log((WORK/row['log']).read_text(encoding='utf-8'),('Open project','Build','Save As'),True)
        row['readback']=readback.compare(source,output)
        rows.append(row)
    passed=all(r['exitCode']==0 and r['sdkAudit']['Clean'] and r['readback']['Equivalent'] for r in rows)
    save('native_summary.json',dict(sourceSha256=before,sourceUnchanged=hashlib.sha256(source.read_bytes()).hexdigest()==before,rows=rows,passed=passed))
    raise SystemExit(0 if passed else 1)
elif mode=='echo':
    from pylogix import PLC
    import fraktal_ab_canonical_reader as reader
    from fraktal_ab_s0_canonical_measure import discover_templates, member_table
    guard=Path('C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7/scripts/guard_echo.py')
    row=run('identity_guard.log',[sys.executable,guard])
    if row['exitCode']:
        raise SystemExit('identity guard failed')
    with PLC('127.0.0.1') as comm:
        comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=0,4000,5
        identity=comm.GetDeviceProperties().Value
        if str(identity.SerialNumber).lower()!='0x601fc87b' or identity.ProductCode!=288 or identity.Revision!='38.11':
            raise SystemExit('exact Echo identity failed')
        reply=comm.GetTagList(allTags=False)
        if reply.Status!='Success': raise SystemExit('Symbol discovery failed')
        objects=discover_templates(comm)
        templates=[dict(handle=h,name=u.Name,byteSize=reader.template_byte_size(comm,h),members=member_table(u)) for h,u in objects.items()]
        symbols=[dict(name=t.TagName,handle=t.DataTypeValue,arrayRank=t.Array,structure=bool(t.Struct)) for t in reply.Value]
    report=dict(schema='fraktal.ab.s1-template-size-observation',capturedUtc=datetime.now(timezone.utc).isoformat(),serial='601FC87B',readOnly=True,canonicalAcceptance=False,reason='Restored legacy V1 genealogy image; no V6 canonical root or manifest',symbols=symbols,templates=templates)
    save('echo_template_catalog.json',report)
    print(json.dumps(dict(templates=len(templates),symbols=len(symbols),readOnly=True)),flush=True)
elif mode=='final':
    script=Path('C:/work/fraktal-ab-s0-20261020/runtime_6cf8bfb1e68e4002b5c3738feb9bf486/final_checks_02.py')
    rows=[run('final_checks.log',[sys.executable,script,WORK/'final_checks.json']),
          run('echo_inspect.log',['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe','inspect'])]
    save('final_summary.json',dict(rows=rows,passed=all(r['exitCode']==0 for r in rows)))
else:
    raise SystemExit('unknown validation mode')

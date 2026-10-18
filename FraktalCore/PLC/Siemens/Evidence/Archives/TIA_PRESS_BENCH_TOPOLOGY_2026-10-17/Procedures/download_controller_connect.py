from pathlib import Path
import subprocess,os,json,hashlib
w=Path(__file__).parent;tia=Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens');stations=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations'
assert not any(json.loads((w/'bench_before_controller_download.json').read_text()).values())
physical=[json.loads(s) for s in (w/'physical_before_controller_download.jsonl').read_text().splitlines()]
assert next(r['value'] for r in physical if r.get('member')=='OutputsEnabled') is False
assert next(r['certificate_sha256'] for r in physical if r.get('event')=='physical-bridge')=='5b7cbc6ccbe886e5c2fb099ca1f231de14d791a0c93b69f56a892d2f32829581'
for label,verified in (('native05_controller_connect','verified_private.json'),('physical06_controller_connect','verified_public.json')):
    assert (w/label/verified).is_file()
    rows=[json.loads(s) for s in (w/label/'build.log').read_text('utf-8-sig').splitlines() if s.startswith('{')]
    compiled=[r for r in rows if r.get('event')=='compile'];assert len(compiled)==2 and all(r['errors']==r['warnings']==0 for r in compiled)
driver=tia/'tools/TiaCli/bin/candidate_structure_examples/Fraktal.Tia.Cli.exe'
assert hashlib.sha256(driver.read_bytes()).hexdigest()=='ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74'
for label,host,project,interface,number,target,address in (
    ('download03_controller_bench','169.254.212.61',stations/'Press_IoBridge_Press1500_20261015/FrkS12/FrkS12.ap20','Siemens PLCSIM Virtual Ethernet Adapter',1,'1 X2','192.168.0.20'),
    ('download04_controller_physical','192.168.0.10',stations/'Press_IoBridge_1214C_20261015/FrkSpikeS2.ap20','Intel(R) 82574L Gigabit Network Connection',2,'1 X1','192.168.0.10')):
    out=w/label;out.mkdir(exist_ok=False)
    guard=subprocess.run(['powershell.exe','-NoProfile','-File',str(tia/'tools/Invoke-TiaPressBench.ps1'),'-Action','status'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True);(out/'guard.jsonl').write_bytes(guard.stdout)
    ident=subprocess.run([sys.executable,'-B',str(tia/'tools/s7_probe.py'),'ident','--host',host],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True) if False else None
    import sys
    ident=subprocess.run([sys.executable,'-B',str(tia/'tools/s7_probe.py'),'ident','--host',host],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True);(out/'ident.log').write_bytes(ident.stdout)
    assert (b'6ES7 516-3AP03-0AB0' if number==1 else b'6ES7 214-1AG40-0XB0') in ident.stdout
    p=out/'download.plan';p.write_text(f'open-project --path "{project}"\ndownload --plc PLC_1 --pc-interface "{interface}" --pc-number {number} --target "{target}" --confirm-target {address} --user-management keep --software-only\nsave\n',encoding='ascii')
    with (out/'download.log').open('xb') as f:r=subprocess.run([str(driver),'plan',str(p)],stdout=f,stderr=subprocess.STDOUT)
    print(dict(download_exit=r.returncode,target=label),flush=True)
    if r.returncode:raise SystemExit(r.returncode)

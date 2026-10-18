"""Read-only acceptance of the authorized local Echo traceability image."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

root = Path('C:/Users/SoftIndVM/Fraktal')
work = Path('C:/work/fraktal-echo-deploy-20261018')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_part_demo'
sys.path.insert(0, str(root / 'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_projection as projection
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_part as part
import fraktal_ab_host_events as host
import fraktal_ab_press_execute as execute

subprocess.run([sys.executable, str(work/'guard_echo.py')], check=True)
app = projection.APP
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot = 0
    comm.SocketTimeout = 5
    comm.ConnectionSize = 4000
    scan_tag = f'FRK_{app.name}_ScanCount'
    before = comm.Read(scan_tag)
    time.sleep(.25)
    after = comm.Read(scan_tag)
    assert before.Status == after.Status == 'Success'
    assert type(before.Value) is int and after.Value > before.Value, 'PLC scan counter is stopped'
    native_part = part.read(comm, app)
    native_host = host.read(comm, app)
    unit = execute.read_layout(comm, f'FRK_{app.name}_Unit', gen.unit_context_members(app))
    assert unit is not None and unit['Error'] == 0 and unit['Running'] == 0
    assert unit['OrderFail'] == 0, 'module/Unit scan ordering violation'
    assert native_part['SchemaVersion'] == 1 and native_part['Present'] == 0
    assert native_host['metadata']['SchemaVersion'] == 2
    assert native_host['metadata']['Failed'] == 0
    assert native_host['metadata']['EpochLow'] or native_host['metadata']['EpochHigh']
    document = projection.read_document(comm)
    assert document['contentHash'] == manifest.content_hash(app)
    assert document['values']['Press/Part/Present'] is False
    assert document['values']['Press/HostEvents/SchemaVersion'] == 2
    report = dict(schema='fraktal.ab.echo-readonly-runtime', schemaVersion=1,
        controller='127.0.0.1', serial='601FC87B', declaration='fraktal_ab_part_demo',
        manifestHash=manifest.content_hash(app), scanBefore=before.Value, scanAfter=after.Value,
        unitError=unit['Error'], orderFail=unit['OrderFail'], part=native_part,
        host=native_host, projectedNodeCount=document['nodeCount'], moduleCount=document['moduleCount'],
        writesPerformed=False, commandsExercised=False)
    (work/'runtime_read.json').write_text(json.dumps(report,indent=2)+'\n')
    # No account values, credentials or raw tag data beyond the Part/host facets.
    projected = {p:v for p,v in document['values'].items() if any(t in p for t in
        ('/Part/','/HostEvents/','/Nameplate/'))}
    (work/'projected_facets.json').write_text(json.dumps(projected,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('part','host')}))

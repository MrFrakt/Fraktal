import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
OUT=Path(__file__).parent
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_resource_demo'
sys.path.insert(0,str(TOOLS))
from pylogix import PLC
import fraktal_ab_generate as gen
import fraktal_ab_host_events as host
import fraktal_ab_live as live
import fraktal_ab_manifest as manifest
import fraktal_ab_part as part
import fraktal_ab_part_execute as fixture
import fraktal_ab_projection as projection
import fraktal_ab_resource_demo as declaration
import fraktal_ab_tower_execute as tower
import fraktal_ab_readback as rb

app=declaration.application()
checks={}
def check(name,value):
    checks[name]=bool(value)
    if not value: raise AssertionError(name)
def write(name,value):
    with (OUT/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
prior=json.loads((OUT/'preflight.json').read_text(encoding='utf-8'))
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0
    native.ConnectionSize=4000
    native.SocketTimeout=5
    comm=fixture.Guarded(native,0x601FC87B,app)
    comm.guard()
    unit=fixture.px.read_unit(comm)
    access=projection.read_access(comm)
    check('manual_idle',unit['Mode']==0 and all(unit[k]==0 for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')))
    check('session_logged_out',access['CurrentLevel']==0)
    check('original_policy_restored',access['Required']==prior['originalPolicy'])
    held=projection.read_document(comm)['liveConfig']
    check('configuration_restore_complete',not held.restoring)
    medium=live.FileMedium(live.live_directory(app,'601FC87B'))
    wanted=live.documents(app,held,0)
    def values(document): return [{k:v for k,v in row.items() if k!='rev'} for row in document[1:]]
    documents={key:medium.read(key) for key in wanted}
    for key,document in documents.items():
        check('saved_live_'+key,document is not None and values(document)==values(wanted[key]))
        check('pre_download_values_'+key,values(document)==values(prior['documents'][key]))
    check('lamp_test_inactive',not tower.snapshot(comm,app)['SignalTower/TestActive'])
    check('part_absent',not part.read(comm,app)['Present'])
    batch=host.read(comm,app,tuple(m.code for m in app.models))
    check('resource_events_retained',any(event['Kind'] in (7,8) for event in batch['events']))
    write('final_batch.json',batch)
    state=dict(mode=unit['Mode'],running=unit['Running'],error=unit['Error'],
               partPresent=False,sessionLevel=access['CurrentLevel'],policy=access['Required'])

command=[sys.executable,str(TOOLS/'fraktal_ab_host_events.py'),'127.0.0.1','--expect-serial','601FC87B',
         '--cursor',str(OUT/'resources.cursor.json'),'--sqlite-output',str(OUT/'resources.sqlite')]
counts=[]
for attempt in range(2):
    run=subprocess.run(command,capture_output=True,timeout=30)
    (OUT/f'sink_{attempt+1}.log').write_bytes(run.stdout+run.stderr)
    check(f'sink_{attempt+1}_accepted',run.returncode==0)
    with closing(sqlite3.connect(OUT/'resources.sqlite')) as connection:
        check(f'sink_{attempt+1}_integrity',connection.execute('PRAGMA integrity_check').fetchone()==('ok',))
        records=[json.loads(row[0]) for row in connection.execute('SELECT Record FROM Events ORDER BY Id')]
        counts.append(len(records))
check('sink_reopen_no_duplicate_rows',counts[0]==counts[1])
check('resource_sink_subject_and_identity',any(record.get('event',{}).get('Kind') in (7,8)
    and record['event']['Subject'].startswith('Fixture.') and record['event']['PartUid']=='' for record in records))

generated=OUT/'resources_reproduced.L5X'
gen.generate(app,Path('C:/work/echo38_5580_seed.L5X'),generated)
check('source_reproduces_compiled_image',sha(generated)==sha(OUT/'resources_01.L5X'))
identity=subprocess.run(['python','C:/work/fraktal-echo-deploy-20261018/guard_echo.py'],capture_output=True,timeout=30)
check('final_exact_target',identity.returncode==0)
(OUT/'final_identity.json').write_bytes(identity.stdout)
echo=subprocess.run(['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe','inspect'],capture_output=True,timeout=60)
check('echo_read',echo.returncode==0)
status=json.loads(echo.stdout)
check('echo_run_not_faulted',status['ControllerMode']==1 and status['IsFaulted'] is False and status['SerialNumber']==0x601FC87B)
(OUT/'final_echo.json').write_bytes(echo.stdout)
write('final_checks.json',dict(schema='fraktal.ab.resource-final-checks',version=1,checks=checks,passed=all(checks.values()),
    manifestHash=manifest.content_hash(app),configRevision=manifest.config_revision(app),state=state,
    sinkRows=counts[-1],sourceSha256=sha(generated),preparedAcdSha256=(OUT/'prepared.sha256').read_text().strip(),
    downloadedAcdSha256=sha(OUT/'resources_01.ACD'),backupAcdSha256=sha(OUT/'echo_before_resources.ACD')))
print(json.dumps(dict(passed=all(checks.values()),checks=len(checks),sinkRows=counts[-1],manifestHash=manifest.content_hash(app))))

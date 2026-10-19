import json, os, sqlite3, subprocess, sys
from contextlib import closing
from pathlib import Path
out=Path(__file__).parent
root=Path('C:/Users/SoftIndVM/Fraktal')
tools=root/'FraktalCore/PLC/Allen-Bradley/tools'
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_resource_demo'
sys.path.insert(0,str(tools))
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_resource_demo as resource
import fraktal_ab_host_events as host
app=resource.application()
stage=sys.argv[1]
assert stage in ('after_download','after_regression')
checks={}
def check(name, value):
    checks[name]=bool(value)
    assert value,name
def read_json(name): return json.loads((out/name).read_text(encoding='utf-8'))
def rows():
    with closing(sqlite3.connect(out/'restart.sqlite')) as db:
        check('database_integrity',db.execute('PRAGMA integrity_check').fetchone()==('ok',))
        return [json.loads(row[0]) for row in db.execute('SELECT Record FROM Events ORDER BY Id')]
def consume(label):
    command=[sys.executable,str(tools/'fraktal_ab_host_events.py'),'127.0.0.1','--expect-serial','601FC87B',
       '--cursor',str(out/'restart.cursor.json'),'--sqlite-output',str(out/'restart.sqlite')]
    run=subprocess.run(command,capture_output=True,timeout=40)
    (out/(stage+'_'+label+'.log')).write_bytes(run.stdout+run.stderr)
    check(label+'_collector_accepted',run.returncode==0)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0
    native.ConnectionSize=4000
    native.SocketTimeout=5
    comm=fixture.Guarded(native,0x601FC87B,app)
    comm.guard()
    batch=host.read(comm,app,tuple(m.code for m in app.models))
prior=read_json('cursor_before_download.json')
epoch=[batch['metadata']['EpochLow'],batch['metadata']['EpochHigh']]
check('publisher_epoch_changed',epoch!=prior['epoch'])
old=read_json('sink_before_download.json')
consume('first')
first=rows()
check('old_records_preserved',first[:len(old)]==old)
notices=[r for r in first if r.get('reason')=='publisherEpochChanged']
check('exactly_one_restart_notice',len(notices)==1)
check('notice_names_prior_cursor_and_new_epoch',notices[0]['previous']==prior and notices[0]['epoch']==epoch)
check('cursor_advanced_to_current_publisher',read_json('restart.cursor.json')['epoch']==epoch)
check('cursor_acknowledges_current_sequence',read_json('restart.cursor.json')['sequence']==batch['metadata']['NewestSequence'])
consume('reopen')
check('reopen_does_not_duplicate',rows()==first)
if stage=='after_download':
    check('new_publisher_initially_empty',batch['metadata']['Count']==batch['metadata']['NewestSequence']==0)
else:
    check('new_resource_records_delivered',any(r.get('kind')=='event' and r['idempotencyKey'][2:4]==epoch and r['event']['Kind'] in (7,8) for r in first))
    old_keys={r['event']['Sequence'] for r in old if r.get('kind')=='event'}
    new_keys={r['event']['Sequence'] for r in first if r.get('kind')=='event' and r['idempotencyKey'][2:4]==epoch}
    check('reused_sequence_numbers_remain_distinct_across_epochs',bool(old_keys & new_keys))
    (out/'restart.cursor.json').write_bytes((out/'cursor_before_download.json').read_bytes())
    consume('stale_cursor_replay')
    check('stale_cursor_replay_does_not_duplicate',rows()==first)
    consume('stale_cursor_reopen')
    check('replayed_cursor_reopen_does_not_duplicate',rows()==first)
    check('replay_recovers_acknowledgement',read_json('restart.cursor.json')['sequence']==batch['metadata']['NewestSequence'])
result=dict(schema='fraktal.ab.publisher-restart-check',version=1,stage=stage,checks=checks,
    passed=all(checks.values()),previousCursor=prior,currentCursor=read_json('restart.cursor.json'),
    batch=batch,records=first,collectorControllerWrites=0,
    clockReplayQualified=False,powerCycleQualified=False,gatewayServiceRestartQualified=False)
with (out/(stage+'.json')).open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2)
print(json.dumps(dict(stage=stage,passed=True,checks=len(checks),rows=len(first),epoch=epoch)))

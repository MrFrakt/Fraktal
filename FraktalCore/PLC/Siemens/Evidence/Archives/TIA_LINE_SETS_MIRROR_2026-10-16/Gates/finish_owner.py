"""Observe durable cleanup, then release only the guarded owner test CPU."""
import os
import sys
import json
import time
import hashlib
from pathlib import Path
sys.path.insert(0,r'C:\Projects\Fraktal\FraktalCore\PLC\Siemens\Tests\Line')
from owner_target import WORK,PROFILE,TIA,guard,original,action
sys.path.insert(0,str(TIA/'tools'))
from tia_webapi import WebApi
from tia_mailbox import Mailbox

out=Path(sys.argv[1]);assert out.parent.resolve()==Path(__file__).resolve().parent
before=original();status=guard()
api=WebApi(PROFILE['address'],Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/LineOwner_20261016.webapi.pin',False)
api.login('fraktal');box=Mailbox(api,guard,lambda r:None)
limit=time.monotonic()+90
while any(box.read(r+'.ConfigPersist.Pending') for r in ('StationA','StationB')):
    assert time.monotonic()<limit
    time.sleep(.1)
assert not any(box.read(r+'.ConfigPersist.Failed') for r in ('StationA','StationB'))
assert box.read('GDB_LineOwnerTest.WorkingTaktMs')==2500
for root in ('StationA','StationB'):
    assert box.read(root+'.Access.CurrentLevel')==0
    assert box.request('LOGIN',root,User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
    deadline=time.monotonic()+30
    while box.read(root+'.Access.LoginBusy'):
        assert time.monotonic()<deadline
        time.sleep(.1)
    assert box.read(root+'.Access.CurrentLevel')==4
    assert box.request('LIST_CONFIG_SETS',root)
    assert box.read(root+'.ConfigSetCount')==0
    assert box.request('LOGOUT',root)
    assert box.read(root+'.Access.CurrentLevel')==0
api.conn.close();released=action('release');after=original();assert before==after
pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations').glob('*.webapi.pin')}
with out.open('x') as stream:
    json.dump(dict(before=before,after=after,owner_released=released,normalized_value=2500,
                   sets=0,pending=False,failed=False,pins=pins),stream,indent=2)
    stream.write('\n')
print(released);print('Original Fraktal unchanged; owner writes durable and test sets absent')

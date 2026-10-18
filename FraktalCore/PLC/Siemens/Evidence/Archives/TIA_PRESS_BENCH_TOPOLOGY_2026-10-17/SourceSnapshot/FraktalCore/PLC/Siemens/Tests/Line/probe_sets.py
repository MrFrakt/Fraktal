"""Whole line sets, JSON exchange, access, shared readiness and durable restart."""
import copy
import json
import os
from pathlib import Path
import sys
import time

from owner_target import WORK, PROFILE, TIA, action, guard, original
sys.path.insert(0, str(TIA/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_webapi import WebApi, leaf_var


def probe(output):
    if output.resolve().parent != WORK.resolve(): raise ValueError('fixed private workspace required')
    before = original()
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/LineOwner_20261016.webapi.pin'
    api = WebApi(PROFILE['address'], pin, False)
    facts = Catalog.read()
    line_kind = facts.enums['E_ConfigKind']['LINE_CFG']
    checks = []
    with output.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row): stream.write(json.dumps(row)+'\n'); stream.flush()

        def check(label, value, expected=True):
            passed = type(value) is type(expected) and value == expected
            checks.append(passed)
            emit(dict(event='check', label=label, value=value, expected=expected, passed=passed))
            if not passed: raise AssertionError(label)

        def wait(predicate, label, seconds=120):
            deadline = time.monotonic()+seconds
            while time.monotonic()<deadline:
                if predicate(): return
                time.sleep(.1)
            raise TimeoutError(label)

        def connect():
            api.login('fraktal')
            return Mailbox(api, guard, emit)

        def ready():
            wait(lambda: not box.read('FRK_PersistStatus.Restoring'), 'restore barrier')
            wait(lambda: all(not box.read(r+'.ConfigPersist.Pending') and not box.read(r+'.ConfigPersist.Failed')
                            for r in ('StationA','StationB')), 'verified document writes')

        def login(root='StationA', user='admin'):
            check('login '+root+' '+user, box.request('LOGIN', root, User=user, Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            wait(lambda: not box.read(root+'.Access.LoginBusy'), 'login completion')
            check('level '+root+' '+user, box.read(root+'.Access.CurrentLevel'), 4 if user=='admin' else 1)

        def edit(value, root='StationA'):
            return box.request('WRITE_CONFIG',root,TargetPath=root,NameValue='line.taktMs',TextValue=str(value),IntValue=1)

        def listing(root='StationA'):
            assert box.request('LIST_CONFIG_SETS',root)
            return [box.read(root+'.ConfigSets[%d].SetName'%i) for i in range(1,box.read(root+'.ConfigSetCount')+1)]

        def export(name, root='StationA', kind=None, model=0, token='0123456789abcdef0123456789abcdef', after_header=None):
            rows=[]
            if kind is None:
                accepted=box.request('EXPORT_CONFIG_SET',root,TextValue=name,IntValue=0)
            else:
                accepted=box.request('EXPORT_CURRENT_CONFIG',root,TextValue=name,IntValue=kind,DurationMs=model,NameValue=token)
            if not accepted:return None
            count=box.read(root+'.ConfigSetDocumentLines')
            rows.append(json.loads(box.read(root+'.ConfigSetDocument')))
            if after_header:after_header()
            for index in range(1,count+1):
                if not box.request('EXPORT_CONFIG_SET',root,TextValue=name,IntValue=index,NameValue=token if kind is not None else ''): return None
                check('export cursor '+name+' '+str(index),box.read(root+'.ConfigSetDocumentLine'),index)
                rows.append(json.loads(box.read(root+'.ConfigSetDocument')))
            emit(dict(event='document',name=name,root=root,rows=rows))
            return rows

        def importing(rows):
            for index, row in enumerate(rows):
                text=json.dumps(row,separators=(',',':'),ensure_ascii=True)
                pieces=[text[i:i+255] for i in range(0,len(text),255)]
                for piece_index,piece in enumerate(pieces):
                    last=piece_index==len(pieces)-1
                    if not box.request('IMPORT_CONFIG_SET',TextValue=piece,IntValue=0 if last else 1,
                                       BoolValue=last and index==len(rows)-1):return False
            return True

        try:
            box=connect();ready();emit(dict(event='connection',status=guard(),fingerprint=api.fingerprint))
            for root in ('StationA','StationB'):
                login(root)
                for name in listing(root):
                    if not name.startswith('line-e2e-'):raise RuntimeError('preserve unexpected saved test set')
                    assert box.request('DELETE_CONFIG_SET',root,TextValue=name)
            check('normalize initial line value',edit(2500))
            snapshot=export('line-e2e-current',kind=line_kind,after_header=lambda:check('peer edit during immutable export',edit(2600,'StationB')))
            check('current line export complete',len(snapshot),9)
            check('current line export identity',snapshot[0]['root'],'StationA')
            check('current line export kind',snapshot[0]['kind'],line_kind)
            check('current export stays immutable',int(next(r['value'] for r in snapshot[1:] if r['key']=='line.taktMs')),2500)
            check('peer edit changed live owner',box.read('GDB_LineOwnerTest.WorkingTaktMs'),2600)
            check('line keys and scopes',all(r['scope']=='StationA' and r['key'].startswith('line.') and r['kind']==line_kind for r in snapshot[1:]))
            check('line model selector refused',box.request('EXPORT_CURRENT_CONFIG',TextValue='line-e2e-invalid',IntValue=line_kind,DurationMs=1,NameValue='1'*32),False)
            for index in range(4):check('save line set '+str(index),box.request('SAVE_CONFIG_SET',TextValue='line-e2e-'+str(index),IntValue=line_kind))
            check('line set catalog full',len(listing()),4)
            check('full catalog refuses another set',box.request('SAVE_CONFIG_SET',TextValue='line-e2e-overflow',IntValue=line_kind),False)
            check('full catalog still exports current line',export('line-e2e-full-current',kind=line_kind) is not None)
            stored=export('line-e2e-0')
            check('saved line set count',stored[0]['records'],8)
            check('save current line value',int(next(r['value'] for r in stored[1:] if r['key']=='line.taktMs')),2600)
            check('change before whole load',edit(3000))
            revision=box.read('StationA.Line.Revision')
            check('load whole line set',box.request('LOAD_CONFIG_SET',TextValue='line-e2e-0'))
            check('whole set advances revision once',box.read('StationA.Line.Revision'),revision+1)
            check('whole set restores value',box.read('GDB_LineOwnerTest.WorkingTaktMs'),2600)
            wait(lambda:box.read('StationB.Line.Revision')==revision+1,'peer line revision')
            for change in ('partial','last-bound','revision','enum','wrong-root'):
                broken=copy.deepcopy(stored)
                if change=='partial':broken.pop();broken[0]['records']-=1
                elif change=='last-bound':broken[-1]['value']='999'
                elif change=='revision':broken[-1]['rev']+=1
                elif change=='enum':next(r for r in broken[1:] if r['key']=='line.grade')['value']='99'
                else:broken[0]['root']='StationB'
                current=box.read('StationA.Line.Revision')
                check('reject imported '+change,importing(broken),False)
                check('bad import keeps working revision '+change,box.read('StationA.Line.Revision'),current)
                check('bad import preserves saved catalog '+change,len(listing()),4)
            check('saved set survives refused replacement',box.request('LOAD_CONFIG_SET',TextValue='line-e2e-0'))
            check('root catalog identity is retained',box.request('LOAD_CONFIG_SET','StationB',TextValue='line-e2e-0'),False)
            check('peer root saves own named snapshot',box.request('SAVE_CONFIG_SET','StationB',TextValue='line-e2e-peer',IntValue=line_kind))
            modes=facts.enums['E_Mode']
            check('peer AUTO',box.request('SET_MODE','StationB',IntValue=modes['AUTO']))
            wait(lambda:box.read('StationB.ModeActivePublished')==modes['AUTO'],'AUTO mode')
            check('peer starts',box.request('START','StationB'))
            wait(lambda:box.read('StationB.RunningPublished'),'peer running')
            revision=box.read('StationA.Line.Revision')
            check('shared readiness refuses whole load',box.request('LOAD_CONFIG_SET',TextValue='line-e2e-0'),False)
            check('refused whole load keeps revision',box.read('StationA.Line.Revision'),revision)
            check('peer reset',box.request('OPERATOR_RESET','StationB'))
            wait(lambda:box.read('StationB.Status.State')==0 and not box.read('StationB.RunningPublished'),'peer ready')
            check('peer MANUAL',box.request('SET_MODE','StationB',IntValue=modes['MANUAL']))
            wait(lambda:box.read('StationB.ModeActivePublished')==modes['MANUAL'],'MANUAL mode')
            gate=facts.enums['E_GatedAction']['CONFIG_SET']
            check('lower set gate for independent value-access check',box.request('SET_ACCESS_LEVEL',IntValue=gate,TextValue='1'))
            login(user='operator')
            check('per-value write level refuses line set load',box.request('LOAD_CONFIG_SET',TextValue='line-e2e-0'),False)
            check('readable set can export at lower level',export('line-e2e-0') is not None)
            login()
            check('restore set gate',box.request('SET_ACCESS_LEVEL',IntValue=gate,TextValue='4'))
            ready();saved_revision=box.read('StationA.Line.Revision')
            emit(dict(event='poison-guard',status=guard()))
            api.call('PlcProgram.Write',{'var':leaf_var(['GDB_LineOwnerTest','PoisonPulse']),'value':True})
            wait(lambda:box.read('GDB_LineOwnerTest.WorkingTaktMs')==99999,'poison working cache')
            api.conn.close();emit(dict(event='power-cycle',status=action('restart')))
            api=WebApi(PROFILE['address'],pin,False);box=connect();ready()
            check('line image restored after set load',box.read('GDB_LineOwnerTest.WorkingTaktMs'),2600)
            check('line revision restored',box.read('StationA.Line.Revision'),saved_revision)
            check('boot saw typed default before restore',box.read('GDB_LineOwnerTest.BootDefaultValue'),1000)
            for root in ('StationA','StationB'):login(root)
            check('four owner line sets durable',len(listing()),4)
            check('peer root line set durable',listing('StationB'),['line-e2e-peer'])
            check('durable line set still loads',box.request('LOAD_CONFIG_SET',TextValue='line-e2e-0'))
            for index,kind in enumerate((facts.enums['E_ConfigKind']['STATION_CFG'],facts.enums['E_ConfigKind']['PAR_CFG'])):
                assert box.request('DELETE_CONFIG_SET',TextValue='line-e2e-'+str(index+2))
                name='line-e2e-ordinary-'+str(index)
                check('save ordinary kind '+str(kind),box.request('SAVE_CONFIG_SET',TextValue=name,IntValue=kind))
                ordinary=export(name)
                check('ordinary set excludes line '+str(kind),all(not r['key'].startswith('line.') and r['kind']==kind for r in ordinary[1:]))
            for root in ('StationA','StationB'):
                for name in listing(root):
                    if not name.startswith('line-e2e-'):raise RuntimeError('unexpected set in cleanup')
                    check('delete test set '+root+' '+name,box.request('DELETE_CONFIG_SET',root,TextValue=name))
            check('normalize final working value',edit(2500));ready()
            for root in ('StationA','StationB'):assert box.request('LOGOUT',root)
            after=original();check('original Fraktal unchanged',after,before)
            emit(dict(event='complete',checks=len(checks),failures=sum(not c for c in checks)))
        finally:
            if api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))

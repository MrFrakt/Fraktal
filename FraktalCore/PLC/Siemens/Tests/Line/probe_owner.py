"""Live mailbox/manifest/shared LOAD_DB owner checks on the fixed .53 bench."""
import json
import os
from pathlib import Path
import sys
import time

from owner_target import WORK, PROFILE, TIA, action, guard, original
sys.path.insert(0,str(TIA/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_webapi import WebApi, leaf_var


def probe(out):
    if out.resolve().parent != WORK.resolve(): raise ValueError('fixed private evidence directory required')
    before = original()
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/LineOwner_20261016.webapi.pin'
    checks = []
    pages = {}
    guard()
    # This trust applies only to the newly registered, guarded virtual test CPU.
    api = WebApi(PROFILE['address'], pin, not pin.exists())
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row): stream.write(json.dumps(row)+'\n');stream.flush()

        def check(label, value, expected=True):
            passed = type(value) is type(expected) and value == expected
            checks.append(passed)
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed))
            if not passed: raise AssertionError(label)

        def wait(predicate,label,seconds=120):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                if predicate():return
                time.sleep(.1)
            raise TimeoutError(label)

        def connect():
            api.login('fraktal')
            return Mailbox(api,guard,emit)

        def ready():
            wait(lambda: not box.read('FRK_PersistStatus.Restoring'),'restore barrier')
            wait(lambda: all(not box.read(r+'.ConfigPersist.Pending') and not box.read(r+'.ConfigPersist.Failed')
                             for r in ('StationA','StationB')),'verified document writes')

        def login(root,user='admin'):
            check('login accepted '+root+' '+user,box.request('LOGIN',root,User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            wait(lambda:not box.read(root+'.Access.LoginBusy'),'application authentication')
            check('authenticated level '+root,box.read(root+'.Access.CurrentLevel'),4 if user=='admin' else 1)

        def edit(key,text,root='StationA',revision=1,model=0):
            return box.request('WRITE_CONFIG',root,TargetPath=root,NameValue='line.'+key,TextValue=text,IntValue=revision,DurationMs=model)

        def line_entries(root,model=0):
            found=[]; total=1; page=0
            cached=pages.get(root) if model==0 else None
            visits=iter(cached) if cached else None
            visited=[]
            while True:
                if visits:
                    try:page=next(visits)
                    except StopIteration:break
                elif page>=total:break
                assert box.request('QUERY_CONFIG',root,IntValue=page,DurationMs=model)
                base=root+'.HmiResponse.ConfigPage'
                total=box.read(base+'.PageCount');count=box.read(base+'.EntryCount')
                names=('Scope','Item','WriteKey','ValueText','Writable','Readable','ConfigKind','WriteRevision','ModelScoped')
                requests=[('PlcProgram.Read',{'var':leaf_var((base+'.Entries[%d].%s'%(slot,name)).split('.'))})
                          for slot in range(1,count+1) for name in names]
                values=api.bulk(requests)
                if any(error for value,error in values):raise RuntimeError('manifest read failed')
                rows=[dict(zip(names,[v[0] for v in values[i:i+len(names)]])) for i in range(0,len(values),len(names))]
                lines=[r for r in rows if r['ConfigKind']==2]
                if lines:visited.append(page);found.extend(lines)
                if not visits:page+=1
            if model==0 and not cached:pages[root]=visited
            return found

        try:
            box=connect();emit(dict(event='connection',status=guard(),fingerprint=api.fingerprint))
            ready()
            for root in ('StationA','StationB'):
                check('line identity '+root,box.read(root+'.Line.LineId'),'PRESS-LINE-1')
                check('line owner '+root,box.read(root+'.Line.Owner'),'BenchLineOwner')
                check('line role '+root,box.read(root+'.Line.Role'),Catalog.read().enums['E_LineRole']['OWNER'])
                login(root)
            check('one shared revision',box.read('StationA.Line.Revision'),box.read('StationB.Line.Revision'))
            rows=line_entries('StationA')
            check('eight line capabilities',len(rows),8)
            check('root scoped line manifest',all(r['Scope']=='StationA' and r['Item'].startswith('Line/') and r['Writable'] and not r['ModelScoped'] for r in rows))
            check('inactive model excludes line config',len(line_entries('StationA',1)),0)
            old=box.read('StationA.Line.Revision')
            config_revs={r:box.read(r+'.ConfigRev') for r in ('StationA','StationB')}
            check('peer root edits owner',edit('taktMs','2500','StationB'))
            wait(lambda:box.read('StationA.Line.Revision')==old+1 and box.read('StationB.Line.Revision')==old+1,'revision propagation')
            check('both referencing manifests invalidate',all(box.read(r+'.ConfigRev')!=config_revs[r] for r in config_revs))
            for root in ('StationA','StationB'):
                values={r['WriteKey']:r for r in line_entries(root)}
                check('shared value '+root,int(values['line.taktMs']['ValueText']),2500)
            check('typed LREAL edit',edit('gain','2.5'))
            check('peer sees typed LREAL',float(next(r['ValueText'] for r in line_entries('StationB') if r['WriteKey']=='line.gain')),2.5)
            revision=box.read('StationA.Line.Revision')
            for key,text,rev,model,label in (
                ('taktMs','0',1,0,'declared lower bound'),('small','256',1,0,'native upper bound'),
                ('grade','99',1,0,'enum domain'),('gain','bad',1,0,'invalid numeric text'),
                ('hostName','x'*41,1,0,'string width'),('taktMs','3000',2,0,'capability revision'),
                ('taktMs','3000',1,1,'model selector')):
                check('refuse '+label,edit(key,text,revision=rev,model=model),False)
                check('rejected edit keeps revision '+label,box.read('StationA.Line.Revision'),revision)
            check('logout root',box.request('LOGOUT'))
            check('anonymous line edit refused',edit('taktMs','3000'),False)
            login('StationA','operator')
            check('field minimum refuses operator',edit('taktMs','3000'),False)
            login('StationA')
            modes=Catalog.read().enums['E_Mode']
            check('peer AUTO selected',box.request('SET_MODE','StationB',IntValue=modes['AUTO']))
            wait(lambda:box.read('StationB.ModeActivePublished')==modes['AUTO'],'peer AUTO')
            check('peer starts',box.request('START','StationB'))
            wait(lambda:box.read('StationB.RunningPublished'),'peer BUSY')
            check('shared readiness refuses write from idle peer',edit('taktMs','3000'),False)
            check('peer reset accepted',box.request('OPERATOR_RESET','StationB'))
            wait(lambda:box.read('StationB.Status.State')==0 and not box.read('StationB.RunningPublished'),'peer reset')
            check('peer MANUAL selected',box.request('SET_MODE','StationB',IntValue=modes['MANUAL']))
            wait(lambda:box.read('StationB.ModeActivePublished')==modes['MANUAL'],'peer MANUAL')
            ready()
            expected=box.read('StationA.Line.Revision')
            emit(dict(event='poison-guard',status=guard()))
            api.call('PlcProgram.Write',{'var':leaf_var(['GDB_LineOwnerTest','PoisonPulse']),'value':True})
            wait(lambda:box.read('GDB_LineOwnerTest.WorkingTaktMs')==99999,'test cache poisoning')
            check('working cache deliberately differs',box.read('GDB_LineOwnerTest.WorkingTaktMs'),99999)
            api.conn.close()
            emit(dict(event='power-cycle',status=action('restart')))
            api=WebApi(PROFILE['address'],pin,False);box=connect();ready()
            check('boot observed defaults before restore',box.read('GDB_LineOwnerTest.BootDefaultSeen'))
            check('boot default value',box.read('GDB_LineOwnerTest.BootDefaultValue'),1000)
            check('LOAD_DB restored working value',box.read('GDB_LineOwnerTest.WorkingTaktMs'),2500)
            check('LOAD_DB restored revision',box.read('StationA.Line.Revision'),expected)
            check('peer restored same revision',box.read('StationB.Line.Revision'),expected)
            check('restart clears application grant',box.read('StationA.Access.CurrentLevel'),0)
            after=original();check('original Fraktal unchanged',after,before)
            emit(dict(event='complete',checks=len(checks),failures=sum(not v for v in checks)))
        finally:
            if api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))

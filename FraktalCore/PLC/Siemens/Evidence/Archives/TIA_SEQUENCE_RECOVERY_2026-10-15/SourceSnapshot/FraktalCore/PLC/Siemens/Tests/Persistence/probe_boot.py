"""Read-only storage readiness and durability witness for the selected fixture."""
import os,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard

def probe(out):
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    paths=['FRK_PersistStatus.Restoring','FRK_PersistStatus.Failed','FRK_PersistStatus.NativeStatus','FRK_PersistStatus.DocumentCount']
    paths += [r+'.'+f for r in ('StationA','StationB') for f in ('Status.Name','RunningPublished','Access.CurrentLevel','ConfigPersist.Pending','ConfigPersist.Failed','ConfigPersist.WindowMs','ConfigPersist.RestoreLost')]
    try:
        api.login('fraktal')
        with out.open('x',encoding='ascii',newline='\n') as log:
            end=time.monotonic()+60
            while time.monotonic()<end:
                rows=api.bulk([('PlcProgram.Read',dict(var=leaf_var(p.split('.')))) for p in paths])
                errors={p:error for p,(value,error) in zip(paths,rows) if error}
                if errors:log.write(json.dumps(dict(event='read-errors',errors=errors))+'\n');log.flush()
                assert not errors,errors
                state={p:value for p,(value,error) in zip(paths,rows)}
                log.write(json.dumps(dict(event='snapshot',status=guard(),values=state))+'\n');log.flush()
                if guard()['state']=='Run' and not state['FRK_PersistStatus.Restoring'] and not state['FRK_PersistStatus.Failed'] and all(state[r+'.Status.Name']==r and not state[r+'.ConfigPersist.Pending'] and not state[r+'.ConfigPersist.Failed'] for r in ('StationA','StationB')):
                    print(json.dumps(state));return
                time.sleep(.5)
            raise AssertionError('bounded storage readiness/durability')
    finally:api.conn.close()

if __name__=='__main__':probe(Path(sys.argv[1]))

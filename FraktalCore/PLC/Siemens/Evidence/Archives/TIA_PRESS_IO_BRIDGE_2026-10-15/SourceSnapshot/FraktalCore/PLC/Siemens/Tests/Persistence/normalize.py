"""Restore the qualification bench's policy and inactive control state."""
import json, os, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi,leaf_var
from tia_mailbox import Mailbox
from tia_target_guard import guard
from fraktal_tia_binding import Catalog


def normalize(out):
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        try:
            api.login('fraktal');box=Mailbox(api,guard,emit)
            def until(predicate,label):
                end=time.monotonic()+60
                while time.monotonic()<end:
                    if predicate():return
                    time.sleep(.1)
                raise AssertionError(label)
            emit(dict(event='fixture-guard',status=guard()))
            api.call('PlcProgram.Write',dict(var=leaf_var(['GDB_StateAlarmTest','CauseLive']),value=False))
            for root in ('StationA','StationB'):
                assert box.request('LOGIN',root,User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                until(lambda:not box.read(root+'.Access.LoginBusy'),'login completion')
                assert box.read(root+'.Access.CurrentLevel')==4
                assert box.request('SET_SESSION_TIMEOUT',root,DurationMs=0)
                levels={2:1,4:1,5:1,8:4,11:3}
                for gate in Catalog.read().enums['E_GatedAction'].values():
                    assert box.request('SET_ACCESS_LEVEL',root,IntValue=gate,TextValue=str(levels.get(gate,0)))
                if box.read(root+'.AlarmLog.NActive') or any(box.read(root+'.'+flag) for flag in ('Busy','Error','Aborted')):
                    assert box.request('OPERATOR_RESET',root)
                assert box.request('SET_MODE',root,IntValue=Catalog.read().enums['E_Mode']['MANUAL'])
            until(lambda:all(not box.read(r+'.ConfigPersist.Pending') and not box.read(r+'.ConfigPersist.Failed') for r in ('StationA','StationB')),'verified durability')
            for root in ('StationA','StationB'):
                assert box.request('LOGOUT',root)
                assert not box.read(root+'.RunningPublished') and box.read(root+'.Access.CurrentLevel')==0
            # A fresh scan also clears test-only standalone publisher state left
            # by an interrupted suite. Confirmed documents remain untouched.
            for action in ('halt','run'):
                emit(dict(event='restart-guard',action=action,status=guard()))
                result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                emit(dict(event='restart-result',exit_code=result.returncode,output=result.stdout.decode('utf-8-sig')))
                assert result.returncode==0
            until(lambda:not box.read('FRK_PersistStatus.Restoring'),'restore complete')
            emit(dict(event='summary',completed=True,status=guard()))
        finally:api.conn.close()


if __name__=='__main__':normalize(Path(sys.argv[1]))

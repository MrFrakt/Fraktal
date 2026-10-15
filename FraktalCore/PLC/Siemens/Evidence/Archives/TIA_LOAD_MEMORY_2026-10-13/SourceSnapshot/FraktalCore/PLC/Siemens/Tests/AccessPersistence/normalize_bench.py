"""Explicitly restore the shared bench after tests that edit retained policy."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import time

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]/'tools'), str(HERE.parent/'ConfigSets')]
from tia_webapi import WebApi, leaf_var
from native_mailbox import Mailbox
from fraktal_tia_binding import Catalog
spec = importlib.util.spec_from_file_location('guard', HERE.parent/'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UNIT)

if __name__ == '__main__':
    with Path(sys.argv[1]).open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row)+'\n')
            stream.flush()
        api = WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
        try:
            api.login('fraktal')
            box = Mailbox(api, UNIT.guard, emit)
            for field,value in (('GDB_StateAlarmTest.CauseLive',False),('GDB_StateAlarmTest.Position',0),('GDB_StateAlarmTest.PublishState',False),('GDB_StateAlarmTest.ClearLog',True)):
                emit(dict(event='fixture-guard',target=field,status=UNIT.guard()))
                api.call('PlcProgram.Write',{'var':leaf_var(field.split('.')),'value':value})
            for root in ('StationA','StationB'):
                assert box.request('LOGIN',root,User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                deadline = time.monotonic()+8
                while box.read(root+'.Access.LoginBusy') and time.monotonic()<deadline:
                    time.sleep(.02)
                assert box.read(root+'.Access.CurrentLevel') == 4
                assert box.request('SET_SESSION_TIMEOUT',root,DurationMs=0)
                # Operator reset is optional when there is no blocking cause.
                if not box.request('OPERATOR_RESET',root):
                    assert box.read(root+'.HmiResponse.Report.Reasons[1].Description') == 'std.release.noBlockingAlarm'
                assert box.request('SET_MODE',root,IntValue=Catalog.read().enums['E_Mode']['MANUAL'])
                assert box.request('LOGOUT',root)
            # Reset the previous state/alarm suite's nonretained scratch and pulses.
            startup = box.read('GDB_AccessPersistTest.StartupCount')
            for action in ('halt','run'):
                emit(dict(event='restart-guard',action=action,status=UNIT.guard()))
                result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                emit(dict(event='restart-result',action=action,exit_code=result.returncode,output=result.stdout.decode('utf-8-sig').strip()))
                assert result.returncode == 0
            deadline = time.monotonic()+8
            while box.read('GDB_AccessPersistTest.StartupCount') <= startup and time.monotonic()<deadline:
                time.sleep(.02)
            assert box.read('GDB_AccessPersistTest.StartupCount') > startup
            emit(dict(event='complete',status=UNIT.guard()))
        finally:
            api.conn.close()

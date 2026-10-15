"""Reset only the qualification bench requests and authenticated sessions."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi
from fraktal_tia_binding import Catalog
from native_mailbox import Mailbox
spec=importlib.util.spec_from_file_location('guard',HERE.parent/'Unit/probe_web.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)
if __name__=='__main__':
    with Path(sys.argv[1]).open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
        try:
            api.login('fraktal');box=Mailbox(api,UNIT.guard,emit)
            for root in ('StationA','StationB'):
                assert box.request('LOGIN',root,User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                deadline=time.monotonic()+8
                while box.read(root+'.Access.LoginBusy') and time.monotonic()<deadline:time.sleep(.02)
                assert box.read(root+'.Access.CurrentLevel')==4
                if not box.request('OPERATOR_RESET',root):
                    assert box.read(root+'.HmiResponse.Report.Reasons[1].Description')=='std.release.noBlockingAlarm'
                assert box.request('SET_MODE',root,IntValue=Catalog.read().enums['E_Mode']['MANUAL'])
                assert box.request('LOGOUT',root)
            emit({'event':'complete','status':UNIT.guard()})
        finally:api.conn.close()

"""Run ordinary config acceptance with named sets explicitly deployed."""
import importlib.util
from pathlib import Path
import sys
spec=importlib.util.spec_from_file_location('config_probe',Path(__file__).resolve().parent.parent/'Config/probe_web.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if __name__=='__main__':
    import os
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
    from tia_webapi import WebApi
    from native_mailbox import Mailbox
    spec=importlib.util.spec_from_file_location('guard',Path(__file__).resolve().parent.parent/'Unit/probe_web.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    api.login('fraktal');box=Mailbox(api,guard.guard,lambda row: None)
    try:
        for root in ('StationA','StationB'):assert box.request('LOGOUT',root)
    finally:api.conn.close()
    module.probe(Path(sys.argv[1]),expect_sets=True,station_schema=2)

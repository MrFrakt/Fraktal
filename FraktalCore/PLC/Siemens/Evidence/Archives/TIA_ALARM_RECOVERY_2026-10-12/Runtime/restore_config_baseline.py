"""Restore one retained test value changed by an interrupted regression."""
from pathlib import Path
import importlib.util,json,os,sys,time
repo=Path("C:/Projects/Fraktal/FraktalCore/PLC/Siemens")
sys.path[:0]=[str(repo/"tools"),str(repo/"Tests/ConfigSets")]
from tia_webapi import WebApi
from native_mailbox import Mailbox
spec=importlib.util.spec_from_file_location("guard",repo/"Tests/Unit/probe_web.py")
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
with Path(sys.argv[1]).open("x",encoding="ascii",newline="\n") as stream:
    def emit(row):stream.write(json.dumps(row)+"\n");stream.flush()
    api=WebApi("169.254.212.49",Path(os.environ["LOCALAPPDATA"])/"Fraktal/TiaStations/FrkS12.webapi.pin",False)
    try:
        api.login("fraktal");box=Mailbox(api,g.guard,emit)
        assert box.read("StationA.ModelId.ModelCode")=="MODEL_A"
        emit(dict(event="baseline-before",preset=box.read("StationA.ParCfg.Preset")))
        assert box.request("LOGIN",User="admin",Secret=os.environ["FRAKTAL_TIA_ADMIN_PIN"])
        deadline=time.monotonic()+8
        while box.read("StationA.Access.LoginBusy") and time.monotonic()<deadline:time.sleep(.02)
        assert box.read("StationA.Access.CurrentLevel")==4
        assert box.request("WRITE_CONFIG",TargetPath="StationA",NameValue="preset",TextValue="10",IntValue=2)
        assert box.read("StationA.ParCfg.Preset")==10
        assert box.request("LOGOUT")
        assert box.read("StationA.Access.CurrentLevel")==0
        emit(dict(event="complete",preset=10,status=g.guard()))
    finally:api.conn.close()

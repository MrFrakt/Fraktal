"""Extend the measured Unit fixture with two nested Units and manual releases."""
import argparse
import copy
import importlib.util
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
spec=importlib.util.spec_from_file_location('unit_fixture',HERE.parent/'Unit/make_fixture.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)


def declaration():
    value=UNIT.declaration();value['registry_capacity']=32
    root=value['types'][0]
    inner=copy.deepcopy(root);inner['name']='FB_InnerUnit';inner['type_key']='Fraktal.Test.Inner'
    satellite=copy.deepcopy(root);satellite['name']='FB_SatelliteUnit';satellite['type_key']='Fraktal.Test.Satellite'
    for t in (inner,satellite):t['unit']['modes']=['AUTO','MANUAL','HOME']
    satellite['children'].append({'name':'Inner','type':inner['name']})
    root['children'].append({'name':'Satellite','type':satellite['name']})
    value['types'].extend([satellite,inner])
    value['types'][2]['logic']['ManRelease']='''    "FRK_ManualCondition"(Conditions := #ManConditions, Slot := 1, Value := 2, Ok := #Hal.Permit, Diag := #Hal.Diag, Bypassable := FALSE);
    "FRK_ManualCondition"(Conditions := #ManConditions, Slot := 2, Value := 2, Ok := #Hal.Sample = 0, Diag := #Hal.LaterDiag, Bypassable := FALSE);'''
    return value


def prepare(out,frames):
    UNIT.test_package(out,frames,declaration())
    import fraktal_tia_generate as GEN
    from fraktal_tia_binding import READONLY
    (out/'05_GDB_RoutingTest.db').write_bytes(GEN.db('GDB_RoutingTest',[
        'PermitOne : Bool;', 'PermitTwo : Bool;', 'NestedFinish : Bool;', 'InnerFinish : Bool;', 'NestedAccessLock : Bool;',
        'RootManualPermit : Bool;', 'ManualAccessLock : Bool;', 'LocalPulse : Bool;', 'LocalKind : DInt;', 'LocalValue : DInt;',
        'LocalAccepted'+READONLY+' : Bool;', 'LocalFirstKind'+READONLY+' : DInt;',
        'LocalRequest'+GEN.PRIVATE+' : "ST_HmiRequest";',
        'ManExecute'+READONLY+' : Bool;', 'ManStarts'+READONLY+' : DInt;'
    ]).encode('ascii'))
    p=out/'40_Main.scl';text=p.read_text(encoding='ascii')
    anchor='    IF #Initial_Call THEN\n';assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'''        "GDB_RoutingTest".PermitOne := TRUE;
        "GDB_RoutingTest".PermitTwo := TRUE;
        "GDB_RoutingTest".RootManualPermit := TRUE;
        "GDB_RoutingTest".NestedFinish := FALSE;
        "GDB_RoutingTest".InnerFinish := FALSE;
        "GDB_RoutingTest".NestedAccessLock := FALSE;
''')
    anchor='    "GDB_FraktalMain"(Startup := #Initial_Call);';assert text.count(anchor)==1
    wiring='''    "StationA".Cell.Gate.ParCfg.Timeout := T#8s;
    IF "GDB_RoutingTest".ManualAccessLock THEN "StationA".Access.Policy.Required[2] := 3; ELSE "StationA".Access.Policy.Required[2] := 0; END_IF;
    "GDB_FraktalHal".Data.StationA.Cell.Gate.Permit := "GDB_RoutingTest".PermitOne;
    IF "GDB_RoutingTest".PermitTwo THEN "GDB_FraktalHal".Data.StationA.Cell.Gate.Sample := 0; ELSE "GDB_FraktalHal".Data.StationA.Cell.Gate.Sample := 1; END_IF;
    "GDB_FraktalHal".Data.StationA.Cell.Gate.Diag.ReasonCode := 2002;
    "GDB_FraktalHal".Data.StationA.Cell.Gate.Diag.Description := WSTRING#'test.manual.first';
    "GDB_FraktalHal".Data.StationA.Cell.Gate.LaterDiag.ReasonCode := 2003;
    "GDB_FraktalHal".Data.StationA.Cell.Gate.LaterDiag.Description := WSTRING#'test.manual.second';
    "GDB_FraktalHal".Data.StationA.Satellite.Cell.Clamp.Permit := "GDB_RoutingTest".RootManualPermit;
    "GDB_FraktalHal".Data.StationA.Satellite.Cell.Clamp.Diag.SourcePath := WSTRING#'StationA.Satellite.Cell.Clamp';
    "GDB_FraktalHal".Data.StationA.Satellite.Cell.Clamp.Diag.Description := WSTRING#'test.nested.permit';
    "GDB_FraktalHal".Data.StationA.Satellite.Cell.Clamp.Diag.ReasonCode := 2002;
    "GDB_FraktalHal".Data.StationA.Satellite.Inner.Cell.Clamp.Permit := TRUE;
    "GDB_FraktalHal".Data.StationA.Satellite.Cell.Clamp.Finish := "GDB_RoutingTest".NestedFinish;
    "GDB_FraktalHal".Data.StationA.Satellite.Inner.Cell.Clamp.Finish := "GDB_RoutingTest".InnerFinish;
    IF "GDB_RoutingTest".NestedAccessLock THEN
        "StationA".Satellite.Access.Policy.Required[5] := 4;
    ELSE
        "StationA".Satellite.Access.Policy.Required[5] := 0;
    END_IF;
    IF "GDB_RoutingTest".LocalPulse THEN
        "GDB_RoutingTest".LocalRequest.Kind := "GDB_RoutingTest".LocalKind;
        "GDB_RoutingTest".LocalRequest.IntValue := "GDB_RoutingTest".LocalValue;
        "FRK_UnitOperation"(Core := "StationA".Satellite.Core, Unit := "StationA".Satellite.Unit, Status := "StationA".Satellite.Status, Policy := "StationA".Satellite.ModePolicy, Access := "StationA".Satellite.Access, Supported := "StationA".Satellite.SupportedModesPublished, Request := "GDB_RoutingTest".LocalRequest, Response := "FRK_UnitScratch".Response, Trusted := FALSE);
        "GDB_RoutingTest".LocalAccepted := "FRK_UnitScratch".Response.Accepted;
        "GDB_RoutingTest".LocalFirstKind := -1;
        IF "FRK_UnitScratch".Response.Report.Count > 0 THEN "GDB_RoutingTest".LocalFirstKind := "FRK_UnitScratch".Response.Report.Reasons[1].Kind; END_IF;
        "GDB_RoutingTest".LocalPulse := FALSE;
    END_IF;
'''
    text=text.replace(anchor,wiring+anchor+'''
    "GDB_RoutingTest".ManExecute := "StationA".Cell.Gate.Execute;
    "GDB_RoutingTest".ManStarts := "StationA".Cell.Gate.Device.StartCount;''')
    p.write_bytes(text.encode('ascii'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)

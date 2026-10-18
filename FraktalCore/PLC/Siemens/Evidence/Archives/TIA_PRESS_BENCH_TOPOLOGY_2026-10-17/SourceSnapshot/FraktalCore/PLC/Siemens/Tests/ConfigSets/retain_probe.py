"""Named-set and ordinary config retention through an owner-preserving power cycle."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi
from native_mailbox import Mailbox
spec=importlib.util.spec_from_file_location('guard',HERE.parent/'Unit/probe_web.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)
def probe(out):
    checks=[];complete=False;pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    api=WebApi('169.254.212.49',pin,False)
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(name,actual,expected):
            ok=type(actual) is type(expected) and actual==expected;checks.append((name,ok));emit(dict(event='check',label=name,actual=actual,expected=expected,passed=ok));assert ok,name
        def login():
            check('admin login',box.request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN']),True)
            deadline=time.monotonic()+8
            while box.read('StationA.Access.LoginBusy') and time.monotonic()<deadline:time.sleep(.02)
            check('admin authenticated',box.read('StationA.Access.CurrentLevel'),4)
        try:
            api.login('fraktal');box=Mailbox(api,UNIT.guard,emit);login()
            check('write config before save',box.request('WRITE_CONFIG',TargetPath='StationA',NameValue='siteLabel',TextValue='power-saved',IntValue=1),True)
            check('save named set before power off',box.request('SAVE_CONFIG_SET',TextValue='power-retain',IntValue=1),True)
            check('edit live after snapshot',box.request('WRITE_CONFIG',TargetPath='StationA',NameValue='siteLabel',TextValue='live-retained',IntValue=1),True)
            before=box.read('StationA.ConfigRev');api.conn.close()
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parent/'Config/cycle_simulator.ps1')],capture_output=True)
            emit(dict(event='power-cycle',output=result.stdout.decode('utf-8-sig'),exit_code=result.returncode));assert result.returncode==0
            api=WebApi('169.254.212.49',pin,False);api.login('fraktal');box=Mailbox(api,UNIT.guard,emit);login()
            check('ordinary live value survives power',box.read('StationA.StationCfg.SiteLabel'),'live-retained')
            check('activation revision changes',box.read('StationA.ConfigRev')!=before,True)
            check('list after power',box.request('LIST_CONFIG_SETS'),True)
            check('named set survives power',box.read('StationA.ConfigSets[1].SetName'),'power-retain')
            check('load retained set',box.request('LOAD_CONFIG_SET',TextValue='power-retain'),True)
            check('saved snapshot survives independently',box.read('StationA.StationCfg.SiteLabel'),'power-saved')
            check('delete retained set',box.request('DELETE_CONFIG_SET',TextValue='power-retain'),True)
            check('restore bench default',box.request('WRITE_CONFIG',TargetPath='StationA',NameValue='siteLabel',TextValue='bench',IntValue=1),True)
            assert box.request('LOGOUT');complete=True;emit(dict(event='complete',checks=len(checks),status=UNIT.guard()))
        finally:
            api.conn.close();suite=ET.Element('testsuite',name='Fraktal.TIA.ConfigSetPower',tests=str(len(checks)),failures=str(sum(not ok for _,ok in checks)),errors='0' if complete else '1')
            for name,ok in checks:
                case=ET.SubElement(suite,'testcase',name=name)
                if not ok:ET.SubElement(case,'failure',message=name)
            if not complete:ET.SubElement(ET.SubElement(suite,'testcase',name='completed'),'error',message='Probe stopped before completion')
            ET.ElementTree(suite).write(out.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)
if __name__=='__main__':probe(Path(sys.argv[1]))

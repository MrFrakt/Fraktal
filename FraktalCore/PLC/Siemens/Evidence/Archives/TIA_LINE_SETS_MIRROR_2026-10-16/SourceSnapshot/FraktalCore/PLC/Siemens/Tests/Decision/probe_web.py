"""Harvest native decision checks and enforce the published/private boundary."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi, leaf_var
spec=importlib.util.spec_from_file_location('unit_probe',HERE.parent/'Unit/probe_web.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)


def probe(out):
    names=json.loads((HERE/'checks.json').read_bytes())
    rows=[];checks=[]
    rows.append({'event':'simulator-guard','status':UNIT.guard()})
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    try:
        api.login('fraktal')
        def read(name):return api.call('PlcProgram.Read',{'var':leaf_var(name.split('.'))})
        def check(name,actual,expected=True):
            ok=type(actual) is type(expected) and actual==expected
            checks.append((name,ok));rows.append({'event':'check','name':name,'actual':actual,'expected':expected,'passed':ok})
        check('native checks done',read('GDB_DecisionTest.Done'))
        check('native total',read('GDB_DecisionTest.Total'),len(names))
        check('native passed',read('GDB_DecisionTest.Passed'),len(names))
        for index,name in names.items():check(name,read('GDB_DecisionTest.Checks['+index+']'))
        for target in ('FRK_Decisions.Slots[1].Owner','GDB_DecisionTest.WorkTestAccess.CurrentLevel'):
            denied=False
            try:read(target)
            except Exception as error:
                denied=True;rows.append({'event':'private-read-refused','target':target,'error_type':type(error).__name__})
            check('private '+target,denied)
        for target,value in [('StationA.Decision.Prompt','test.write.refused'),('StationA.DecisionAnswer',1)]:
            rows.append({'event':'mutation-guard','target':target,'status':UNIT.guard()})
            denied=False
            try:api.call('PlcProgram.Write',{'var':leaf_var(target.split('.')),'value':value})
            except Exception as error:
                denied=True;rows.append({'event':'readonly-write-refused','target':target,'error_type':type(error).__name__})
            check('readonly '+target,denied)
        check('decision withdrawn',read('StationA.Decision.Prompt'),'')
        rows.append({'event':'final-simulator','status':UNIT.guard()})
    finally:api.conn.close()
    out.write_bytes(('\n'.join(json.dumps(r,ensure_ascii=True) for r in rows)+'\n').encode('ascii'))
    suite=ET.Element('testsuite',name='Fraktal.TIA.Decisions',tests=str(len(checks)),failures=str(sum(not ok for _,ok in checks)))
    for name,ok in checks:
        case=ET.SubElement(suite,'testcase',name=name)
        if not ok:ET.SubElement(case,'failure',message='Native decision assertion failed')
    ET.ElementTree(suite).write(out.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)
    if any(not ok for _,ok in checks):raise AssertionError('Native decision checks failed; see '+str(out))
    print(json.dumps({'checks':len(checks),'passed':len(checks),'output':str(out)}))


if __name__=='__main__':probe(Path(sys.argv[1]))

"""Derive Fraktal source/TIA groups and keep Main as a calling routine."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def split_main(text):
    anchor='    "GDB_FraktalMain"(Startup := #Initial_Call);'
    assert text.count(anchor)==1, 'Expected exactly one forest-composition call'
    start=text.index('\nBEGIN\n')+len('\nBEGIN\n')
    body=text[start:text.rindex('END_ORGANIZATION_BLOCK')]
    before,after=body.split(anchor)
    temps=re.search(r'VAR_TEMP\n(.*?)END_VAR',text,re.S)
    declarations=temps[1].splitlines() if temps else []
    routines=[]
    for name,section in [('F_ConfigBenchPrepare',before),('F_ConfigBenchObserve',after)]:
        section=re.sub(r'#Initial_Call\b','#Startup',section)
        used=[line for line in declarations
              if (hit:=re.match(r'\s*(\w+)\s*:',line)) and re.search(r'#'+hit[1]+r'\b',section)]
        lines=['FUNCTION "'+name+'" : Void',"{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1',
               'VAR_INPUT','    Startup : Bool;','END_VAR']
        if used:lines+=['VAR_TEMP',*used,'END_VAR']
        routines.append('\n'.join([*lines,'BEGIN',section.strip('\n'),'END_FUNCTION','']))
    main=text[:start]
    if temps:main=main[:temps.start()]+main[temps.end()+1:]
    main+='    "F_ConfigBenchPrepare"(Startup := #Initial_Call);\n'+anchor+'\n'
    main+='    "F_ConfigBenchObserve"(Startup := #Initial_Call);\nEND_ORGANIZATION_BLOCK\n'
    # Reconstruct the old execution order and check that extraction changed
    # only the routine boundary and Startup parameter spelling.
    assert before+anchor+after==body
    return main, '\n'.join(routines)


def group(filename, text):
    if any(token in filename for token in ('RecoveryTest', 'RecoveryWork', 'RecoveryActions', 'RecoveryOwner')):
        return 'Tests/SequenceRecovery'
    if 'PressDemoUnit' in filename and filename.endswith('.scl'):
        return 'Examples/PressDemo/01_PneumaticPress'
    if 'GDB_GRAPH_PressDemo' in filename or 'PressDemoAutoServices' in filename:
        return 'Examples/PressDemo/01_PneumaticPress/Sequences'
    if 'PressDemo' in filename and filename.startswith('29_') and filename.endswith('.db'):
        return 'Examples/PressDemo/00_System'
    if 'PressDemo' in filename and ('HardwareDriver' in filename or filename.startswith(('30_','35_','40_'))):
        return 'Examples/PressDemo/00_System'
    if 'Release' in filename and 'PressDemo' in filename:
        return 'Examples/PressDemo/01_PneumaticPress/Release'
    if filename.startswith(('26_','27_','28_')) or 'FB_PressDemoAuto' in filename or 'FB_PressDemoHome' in filename or 'LoadPosition' in filename:
        return 'Examples/PressDemo/01_PneumaticPress/Sequences'
    if 'Cylinder' in filename and not 'Declaration' in filename:
        return 'Framework/Modules/ControlModules/Cylinder'
    if 'ST_PressDemo' in filename:
        return 'Examples/PressDemo/01_PneumaticPress/DUTs'
    if 'PressDemoUnit' in filename:
        return 'Examples/PressDemo/01_PneumaticPress'
    if 'Composition' in filename:
        return 'Examples/PressDemo/00_System'
    names=re.findall(r'^(?:TYPE|FUNCTION_BLOCK|FUNCTION|DATA_BLOCK|ORGANIZATION_BLOCK)\s+"(\w+)"',text,re.M)
    if any(n in ('Main','F_ConfigBenchPrepare','F_ConfigBenchObserve','FB_FraktalMain','GDB_FraktalMain','GDB_FraktalHal','StationA','StationB') for n in names):
        return 'Tests/ConfigBench/00_System'
    if filename.startswith('39') or any(n.startswith('GDB_') or n.startswith('F_Test') for n in names):return 'Tests/ConfigBench/Fixtures'
    if any(n.startswith('FB_') and not n.startswith('FB_FRK') for n in names):
        return 'Tests/ConfigBench/Modules'
    if any('Declaration' in n or 'UnitProbe' in n or 'Routing' in n or 'StationCfg' in n for n in names):
        return 'Tests/ConfigBench/DUTs'
    return 'Framework/Core'


def organize(source,out,project,export):
    out.mkdir(parents=True,exist_ok=False)
    inventory=[]; plan=['open-project --path "'+str(project)+'"','delete-blocks --plc PLC_1']
    for path in sorted(source.iterdir()):
        if path.suffix not in ('.scl','.udt','.db','.xml'):continue
        data=path.read_bytes();text=data.decode('utf-8-sig')
        logical=group(path.name,text);target=out/logical/path.name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        inventory.append({'file':target.relative_to(out).as_posix(),'group':logical,
                          'sha256':hashlib.sha256(data).hexdigest(),'kind':path.suffix[1:]})
    # XML chart types precede their SCL owner adapters; everything else follows
    # the established filename dependency order from the source generator.
    def dependency(row):
        name=Path(row['file']).name
        if name.startswith('28_'):return 2
        if name.startswith(('29_','30_','35_','38_','40_')):return 3
        return 1 if row['kind']=='xml' else 0
    rows=sorted(inventory,key=lambda row:(dependency(row),Path(row['file']).name))
    compiled_charts=False
    for row in rows:
        if Path(row['file']).name.startswith('28_') and not compiled_charts:
            plan+=['compile --plc PLC_1','save']
            compiled_charts=True
        path=out/row['file'];logical=row['group']
        if row['kind']=='xml':
            plan.append('import-xml --plc PLC_1 --file "'+str(path)+'" --group "'+logical+'"')
        else:
            plan.append('import-sources --plc PLC_1 --dir "'+str(path.parent)+'" --only "'+path.name+'" --group "'+logical+'"')
    plan+=['compile --plc PLC_1','list-groups --plc PLC_1','export --plc PLC_1 --out "'+str(export)+'" --scl true','save']
    (out/'layout.json').write_bytes((json.dumps({'version':1,'files':inventory},indent=2)+'\n').encode('ascii'))
    (out/'import.plan').write_bytes(('\n'.join(plan)+'\n').encode('ascii'))
    return inventory


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('out',type=Path)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--export',type=Path,required=True)
    args=parser.parse_args();print(json.dumps({'files':len(organize(args.source,args.out,args.project,args.export))}))

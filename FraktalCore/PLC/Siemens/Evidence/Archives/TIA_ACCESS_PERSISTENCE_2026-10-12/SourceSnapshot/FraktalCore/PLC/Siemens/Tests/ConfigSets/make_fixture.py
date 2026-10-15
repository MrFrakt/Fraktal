"""Named sets on the existing two-root config/decision simulator bench."""
import argparse
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('config_fixture',HERE.parent/'Config/make_fixture.py')
CONFIG=importlib.util.module_from_spec(spec);spec.loader.exec_module(CONFIG)
def prepare(out,frames):
    value=CONFIG.declaration();value['config_sets']={'capacity':4}
    value['records']['ST_UnitProbeStationCfg']=value['records']['ST_UnitProbeStationCfg'].replace('SchemaVersion : UINT := 1','SchemaVersion : UINT := 2').replace('END_STRUCT',"LongText : STRING(80) := 'long default'; END_STRUCT")
    for module in value['types']:
        if 'unit' in module:
            module['config'].insert(-1,{'member':'StationCfg.LongText','key':'long.'+'k'*135,'revision':1,
                'label':'test.config.siteLabel','requires_ready':False,'min_write':1})
    CONFIG.prepare(out,frames,value)
    spec=importlib.util.spec_from_file_location('decision_fixture',HERE.parent/'Decision/make_fixture.py')
    decision=importlib.util.module_from_spec(spec);spec.loader.exec_module(decision)
    # Keep the decision acceptance hook; ownership and calls remain in its POU.
    import json
    from fraktal_tia_binding import Catalog
    text=(HERE.parent/'Decision/decision_bench.scl.in').read_text('ascii')
    for enum,members in Catalog.read().enums.items():
        for member,value in members.items():text=text.replace('@'+enum+'.'+member+'@',str(value))
    text=text.replace('@CASE_COUNT@',str(len(json.loads((HERE.parent/'Decision/checks.json').read_bytes()))))
    assert '@' not in text
    (out/'39_DecisionBench.scl').write_bytes(text.encode('ascii'))
    path=out/'40_Main.scl';text=path.read_text('ascii')
    anchor='    "F_ConfigBenchObserve"(Startup := #Initial_Call);'
    assert text.count(anchor)==1
    path.write_bytes(text.replace(anchor,anchor+'\n    "F_DecisionBench"();').encode('ascii'))
    from fraktal_tia_generate import db
    from fraktal_tia_binding import READONLY
    (out/'05_GDB_ConfigSetTest.db').write_bytes(db('GDB_ConfigSetTest',[
        'Corrupt : Bool;', 'SetName : String[80];', 'Field : Int;', 'Text : String[80];',
        'Slot'+READONLY+' : Int;', 'RecordScope'+READONLY+' : String[80];', 'RecordKey'+READONLY+' : String[160];'
    ]).encode('ascii'))
    (out/'39a_ConfigSetBench.scl').write_bytes((HERE/'set_bench.scl.in').read_bytes())
    path=out/'38_ConfigBenchRoutines.scl';text=path.read_text('ascii')
    gate=Catalog.read().enums['E_GatedAction']['CONFIG_SET']
    minimum=Catalog.read().enums['E_AccessLevel']['ENGINEER']
    pos=text.index('\nBEGIN\n')+len('\nBEGIN\n')
    text=text[:pos]+'    IF #Startup THEN\n'+''.join('        "'+root+'".Access.Policy.Required[%d] := %d;\n'%(gate,minimum) for root in ('StationA','StationB'))+'    END_IF;\n'+text[pos:]
    pos=text.rindex('END_FUNCTION')
    text=text[:pos]+'    "F_ConfigSetBench"();\n'+text[pos:]
    path.write_bytes(text.encode('ascii'))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path);parser.add_argument('frames',type=Path)
    args=parser.parse_args();prepare(args.out,args.frames)

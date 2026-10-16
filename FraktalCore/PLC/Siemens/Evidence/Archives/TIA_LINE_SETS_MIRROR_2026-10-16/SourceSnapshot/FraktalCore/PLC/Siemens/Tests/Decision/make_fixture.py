"""Core decisions on the existing two-root, nested-Unit config bench."""
import argparse
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('config_fixture',HERE.parent/'Config/make_fixture.py')
CONFIG=importlib.util.module_from_spec(spec);spec.loader.exec_module(CONFIG)
def prepare(out,frames):
    CONFIG.prepare(out,frames)
    text=(HERE/'decision_bench.scl.in').read_text('ascii')
    from fraktal_tia_binding import Catalog
    catalog=Catalog.read()
    for enum,members in catalog.enums.items():
        for member,value in members.items():text=text.replace('@'+enum+'.'+member+'@',str(value))
    import json
    text=text.replace('@CASE_COUNT@',str(len(json.loads((HERE/'checks.json').read_bytes()))))
    assert '@' not in text
    (out/'39_DecisionBench.scl').write_bytes(text.encode('ascii'))
    path=out/'40_Main.scl';text=path.read_text('ascii')
    anchor='    "F_ConfigBenchObserve"(Startup := #Initial_Call);'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    "F_DecisionBench"();')
    path.write_bytes(text.encode('ascii'))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path);parser.add_argument('frames',type=Path)
    args=parser.parse_args();prepare(args.out,args.frames)

import json,importlib.util,sys,re
from pathlib import Path
w=Path(__file__).resolve().parent
v=json.loads((w/'frames_07/manifest.json').read_bytes())['declaration']
name=next(t['station_config'] for t in v['types'] if t.get('station_config'))
schema=int(re.search(r'SchemaVersion\s*:\s*UINT\s*:=\s*(\d+)',v['records'][name],re.I)[1])
p=Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Tests/Config/probe_web.py')
s=importlib.util.spec_from_file_location('probe',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.probe(Path(sys.argv[1]),expect_sets=bool(v.get('config_sets')),station_schema=schema)

import importlib.util,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
v=json.loads((HERE/'frames_04/manifest.json').read_bytes())['declaration']
spec=importlib.util.spec_from_file_location('probe',Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Tests/Config/probe_web.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
root=v['roots'][0];owner=next(t for t in v['types'] if t['name']==root['type'])
schema=int(re.search(r'SchemaVersion\s*:\s*UINT\s*:=\s*(\d+)',v['records'][owner['station_config']],re.I)[1])
module.probe(Path(sys.argv[1]),expect_sets=bool(v.get("config_sets")),station_schema=schema)

import importlib.util,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
v=json.loads((HERE/'frames_04/manifest.json').read_bytes())['declaration']
spec=importlib.util.spec_from_file_location('probe',Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Tests/AlarmPersistence/probe_web.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.probe(Path(sys.argv[1]),expect_recovery="StationA" in v.get("alarm_recovery",{}).get("scopes",[]))

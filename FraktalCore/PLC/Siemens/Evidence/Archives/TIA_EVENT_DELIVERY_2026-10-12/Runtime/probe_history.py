import json,importlib.util,sys
from pathlib import Path
w=Path(__file__).resolve().parent
v=json.loads((w/'frames_07/manifest.json').read_bytes())['declaration']
p=Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Tests/AlarmPersistence/probe_web.py')
s=importlib.util.spec_from_file_location('probe',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.probe(Path(sys.argv[1]),expect_recovery=bool(v.get('alarm_recovery')))

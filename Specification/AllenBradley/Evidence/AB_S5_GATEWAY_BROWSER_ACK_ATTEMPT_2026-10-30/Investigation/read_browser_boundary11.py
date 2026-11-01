from pathlib import Path
import gzip,json,os
D=Path(__file__).parent/'session_11'
data=json.loads(gzip.decompress((D/'idle_equivalence.json.gz').read_bytes()))
pair=data['pair']
report={}
for name in ['projection','canonical']:
    values=pair[name]['values']
    report[name]={k:v for k,v in values.items() if k.endswith(('/HmiResponse/AckSequence','/HmiRequest/Sequence','/Access/CurrentLevel','/ModeActive'))}
with (D/'browser_failed_boundary_counters.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report,indent=2))
directory=Path(os.environ['LOCALAPPDATA'])/'Google/Chrome/User Data/Default/Local Storage/leveldb'
findings=[]
for path in sorted(directory.glob('*.log')):
    raw=path.read_bytes()
    marker=b'fraktal.hmi.connection.v1';position=0
    while (position:=raw.find(marker,position))>=0:
        origin=raw[max(0,position-100):position]
        if b'127.0.0.1:8080' in origin:
            nearby=raw[position+len(marker):position+len(marker)+8192].decode('utf-8',errors='replace')
            start=nearby.find('{')
            if start>=0:
                try:
                    value,_=json.JSONDecoder().raw_decode(nearby[start:])
                    if isinstance(value,dict) and 'transport' in value and 'endpoint' in value:
                        findings.append(dict(source=path.name,transport=value['transport'],endpoint=value['endpoint'],selectedUnitPaths=value.get('selectedUnitPaths')))
                except (ValueError,TypeError):pass
        position+=len(marker)
with (D/'browser_local_endpoint_findings.json').open('x',encoding='utf-8') as stream:json.dump(dict(readOnly=True,origin='http://127.0.0.1:8080',connectionSettingsOnly=True,findings=findings),stream,indent=2)
print(json.dumps(dict(browserConnectionFindings=findings)))

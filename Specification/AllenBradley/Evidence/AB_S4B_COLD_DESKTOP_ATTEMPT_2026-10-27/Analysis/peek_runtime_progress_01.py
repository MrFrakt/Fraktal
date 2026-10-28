"""Read only completed local captures; never connect to the controller."""
from pathlib import Path
import gzip
import json
W=Path(__file__).parent
S=W.parent/'session_01'
files=sorted(S.glob('candidate_regressions*.json.gz'),key=lambda p:p.stat().st_mtime)
rows=[]
for p in ([files[0],files[-1]] if len(files)>1 else files):
    try:
        data=json.loads(gzip.decompress(p.read_bytes()))
        probe=data.get('pair',{}).get('legacyInputs',{}).get('additional',{}).get('healthProbe')
        rows.append(dict(file=p.name,passed=data.get('passed'),healthProbe=probe))
    except (OSError,EOFError,ValueError):
        rows.append(dict(file=p.name,stillWriting=True))
print(json.dumps(dict(controllerAccess=False,captureFiles=len(files),firstAndLatest=rows)))

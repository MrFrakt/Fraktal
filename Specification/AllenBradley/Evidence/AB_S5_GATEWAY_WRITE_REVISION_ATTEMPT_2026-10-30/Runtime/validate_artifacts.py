from pathlib import Path
import json
from artifact_readiness import validate
D=Path(__file__).parent
value=validate(D)
with (D/'artifact_readiness_02.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))

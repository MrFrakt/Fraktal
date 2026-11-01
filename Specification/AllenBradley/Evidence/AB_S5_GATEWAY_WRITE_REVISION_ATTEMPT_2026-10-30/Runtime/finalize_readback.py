from pathlib import Path
import json
from artifact_readiness import validate
D=Path(__file__).parent
assert json.loads((D/'prepared_readback_01_exit.json').read_bytes())['exitCode']==0
value=json.loads((D/'prepared_readback_01.log').read_text())
assert value['Equivalent'] is True
with (D/'canonical_prepared_compare.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
result=validate(D)
with (D/'artifact_readiness_01.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))

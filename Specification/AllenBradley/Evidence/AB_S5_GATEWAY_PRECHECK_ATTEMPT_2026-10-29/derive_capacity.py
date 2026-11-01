from pathlib import Path
import json,hashlib
from capacity_readiness import validate,FIELDS
D=Path(__file__).parent
measurement=json.loads((D/'capacity_review.json').read_bytes())
canonical=(D/'canonical.sha256').read_text().strip()
for name in ['authorization.template.json','authorization.json']:
    path=D/name;value=json.loads(path.read_bytes())
    assert value['CurrentOwnerApproved'] is False
    value['OwnerCapacityConfirmed']={key:measurement[key] for key in FIELDS}
    assert validate(value,measurement,canonical)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
result=dict(passed=True,controllerAccess=False,capacityUnit='Blocks',
    sourceMeasurementSha256=hashlib.sha256((D/'capacity_review.json').read_bytes()).hexdigest(),
    confirmed={key:measurement[key] for key in FIELDS})
with (D/'capacity_derived_01.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))

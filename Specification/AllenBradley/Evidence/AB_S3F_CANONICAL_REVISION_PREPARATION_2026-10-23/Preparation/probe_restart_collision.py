"""Offline retained-state restart edge; imports no controller transport."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from test_fraktal_ab_canonical_config import ConfigurationTests
import fraktal_ab_canonical_config as config
t=ConfigurationTests();t.setUp();t.scan();before=t.work['Revision']
t.boot=before-1;t.controller.tags['S:FS']=True;t.scan();after=t.work['Revision']
report=dict(offline=True,controllerAccess=False,before=before,bootSeed=before-1,after=after,
 finding='retained first-scan seed one below previous revision is incremented back to that previous revision',
 collisionObserved=before==after,sourceSha256=hashlib.sha256(Path(config.__file__).read_bytes()).hexdigest())
with (Path(__file__).parent/'restart_collision_02.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
assert before==after,'original collision no longer reproduced'

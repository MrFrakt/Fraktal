"""Read-only inspection of pylogix _forward_open timeout parameters."""
from pathlib import Path
import inspect, json
from pylogix.eip import Connection

W = Path(__file__).parent
info = dict(
    forwardOpen=inspect.getsource(Connection._forward_open),
    buildForwardOpen=inspect.getsource(Connection._build_forward_open_packet),
    controllerAccess=False,
)
with (W / 'inspect_pylogix_03.json').open('x', encoding='utf-8') as f:
    json.dump(info, f, indent=2)
print(json.dumps(dict(passed=True)))

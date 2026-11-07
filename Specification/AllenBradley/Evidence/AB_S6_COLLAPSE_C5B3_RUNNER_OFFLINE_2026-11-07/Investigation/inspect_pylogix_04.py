"""Read-only inspection of pylogix _build_cip_forward_open and _build_eip_header."""
from pathlib import Path
import inspect, json
from pylogix.eip import Connection

W = Path(__file__).parent
info = dict(
    cipForwardOpen=inspect.getsource(Connection._build_cip_forward_open),
    eipHeader=inspect.getsource(Connection._build_eip_header),
    controllerAccess=False,
)
with (W / 'inspect_pylogix_04.json').open('x', encoding='utf-8') as f:
    json.dump(info, f, indent=2)
print(json.dumps(dict(passed=True)))

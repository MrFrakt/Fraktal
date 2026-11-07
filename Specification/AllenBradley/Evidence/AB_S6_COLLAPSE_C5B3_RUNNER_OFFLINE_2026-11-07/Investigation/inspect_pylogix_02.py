"""Read-only inspection of pylogix Connection internals."""
from pathlib import Path
import inspect, json
from pylogix.eip import PLC, Connection

W = Path(__file__).parent
info = dict(
    plcSlots=getattr(PLC, '__slots__', None),
    connInit=inspect.getsource(Connection.__init__),
    connPrivateConnect=inspect.getsource(Connection._connect),
    connPrivateClose=inspect.getsource(Connection._close_connection),
    connGetBytes=inspect.getsource(Connection._get_bytes),
    controllerAccess=False,
)
with (W / 'inspect_pylogix_02.json').open('x', encoding='utf-8') as f:
    json.dump(info, f, indent=2)
print(json.dumps(dict(passed=True)))

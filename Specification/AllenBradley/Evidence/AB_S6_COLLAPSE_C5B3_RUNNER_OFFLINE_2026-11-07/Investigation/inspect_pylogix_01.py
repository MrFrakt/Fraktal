"""Read-only inspection of installed pylogix Connection behavior on Close and idle."""
from pathlib import Path
import inspect, json
import pylogix
from pylogix.eip import PLC, Connection

W = Path(__file__).parent
info = dict(
    version=getattr(pylogix, '__version__', 'unknown'),
    plcCloseSource=inspect.getsource(PLC.Close),
    connCloseSource=inspect.getsource(Connection.close),
    connConnectSource=inspect.getsource(Connection.connect),
    connSendSource=inspect.getsource(Connection.send),
    controllerAccess=False,
)
with (W / 'inspect_pylogix_01.json').open('x', encoding='utf-8') as f:
    json.dump(info, f, indent=2)
print(json.dumps(dict(passed=True, version=info['version'])))

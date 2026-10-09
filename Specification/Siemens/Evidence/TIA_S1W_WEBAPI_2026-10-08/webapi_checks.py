import sys, json, pathlib, os
sys.path.insert(0, r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools")
import tia_webapi as w

pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin"
api = w.WebApi("192.168.0.10", pin, False)
api.login("fraktal")
print("permissions:", json.dumps(api.call("Api.GetPermissions")))
for v in ['"SpikeUnit".Status."Name"', '"SpikeUnit".CylB.Status."Name"', '"SpikeUnit".Status.State', '"SpikeUnit".Mode',
          '"SpikeUnit".CylA.Status.Diagnostic.Since', '"SpikeUnit".CylA.Status.Diagnostic.Since.YEAR',
          '"SpikeUnit".CylA.Status.Diagnostic.Since.NANOSECOND', '"SpikeUnit".CylA.Status', '"SpikeUnit".Core.Exec']:
    try:
        print("read", v, "->", json.dumps(api.call("PlcProgram.Read", {"var": v})))
    except w.WebApiError as e:
        print("read", v, "-> error", e.code, e)
# writes that must be refused: module inputs/status (ExternalWritable False), a hidden member, the response
for v, val in [('"SpikeUnit".CylA.Execute', True), ('"SpikeUnit".CylA.Command', 1), ('"SpikeUnit".Status.State', 3),
               ('"SpikeUnit".Core.Exec', 0), ('"SpikeUnit".HmiResponse.Accepted', True)]:
    try:
        print("write", v, "->", json.dumps(api.call("PlcProgram.Write", {"var": v, "value": val})), "  <-- NOT REFUSED")
    except w.WebApiError as e:
        print("write", v, "-> refused", e.code, e)
# a write that must be accepted: a mailbox argument leaf (Sequence untouched, so the PLC acts on nothing)
print("write HmiRequest.TextValue ->", json.dumps(api.call("PlcProgram.Write", {"var": '"SpikeUnit".HmiRequest.TextValue', "value": "webapi-probe"})))
print("readback ->", json.dumps(api.call("PlcProgram.Read", {"var": '"SpikeUnit".HmiRequest.TextValue'})))
# no token: must get nothing
anon = w.WebApi("192.168.0.10", pin, False)
try:
    print("anonymous read ->", json.dumps(anon.call("PlcProgram.Read", {"var": '"SpikeUnit".Status.State'})), "  <-- NOT REFUSED")
except w.WebApiError as e:
    print("anonymous read -> refused", e.code, e)

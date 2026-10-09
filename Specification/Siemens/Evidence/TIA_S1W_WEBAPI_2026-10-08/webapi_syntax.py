import sys, json, pathlib, os
sys.path.insert(0, r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools")
import tia_webapi as w

pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin"
api = w.WebApi("192.168.0.10", pin, False)
api.login("fraktal")
print("root:", json.dumps(api.call("PlcProgram.Browse", {"mode": "children"})))
for v in ['"SpikeUnit"."Status"."State"', '"SpikeUnit"."Status"."Name"', '"SpikeUnit".Status.Name',
          '"SpikeUnit"."CylA"."Status"."Diagnostic"."Since"."YEAR"']:
    try:
        print("read", v, "->", json.dumps(api.call("PlcProgram.Read", {"var": v})))
    except w.WebApiError as e:
        print("read", v, "-> error", e.code)
for db in ["FRK_Registry", "FRK_Clock", "SpkHal", "SpkResults", "SpkMain"]:
    try:
        kids = api.call("PlcProgram.Browse", {"var": '"%s"' % db, "mode": "children"})
        print("browse", db, "->", json.dumps(kids)[:400])
    except w.WebApiError as e:
        print("browse", db, "-> error", e.code)
for v in ['"FRK_Registry".Rows[0].ParentIndex', '"FRK_Registry"."Rows"[0]."ParentIndex"', '"FRK_Registry".Rows[1]']:
    try:
        print("read", v, "->", json.dumps(api.call("PlcProgram.Read", {"var": v})))
    except w.WebApiError as e:
        print("read", v, "-> error", e.code)

import sys, json, pathlib, os, time, statistics
sys.path.insert(0, r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools")
import tia_webapi as w

pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin"
api = w.WebApi("192.168.0.10", pin, False)
api.login("fraktal")

def timed(label, fn, n=20):
    t = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); t.append((time.perf_counter() - t0) * 1000)
    print("%-44s n=%d median=%.0f ms min=%.0f max=%.0f" % (label, n, statistics.median(t), min(t), max(t)))

fast = ['"SpikeUnit".Status.State', '"SpikeUnit".Busy', '"SpikeUnit".Mode', '"SpikeUnit".CurrentStep.StepNo',
        '"SpikeUnit".Status.FaultActive', '"SpikeUnit".CylA.Status.State', '"SpikeUnit".CylB.Status.State',
        '"SpikeUnit".CylA.OutImm.Extended', '"SpikeUnit".CylB.OutImm.Extended', '"SpikeUnit".HmiResponse.AckSequence']
timed("Api.Ping (no PLC data)", lambda: api.call("Api.Ping"))
timed("1 leaf  (dint)", lambda: api.call("PlcProgram.Read", {"var": fast[0]}))
timed("1 leaf  (string[80] Status.Name)", lambda: api.call("PlcProgram.Read", {"var": '"SpikeUnit".Status."Name"'}))
timed("5 leaves batch", lambda: api.bulk([("PlcProgram.Read", {"var": v}) for v in fast[:5]]))
timed("10 leaves batch (a fast tier)", lambda: api.bulk([("PlcProgram.Read", {"var": v}) for v in fast]))
timed("10 leaves batch, mode=raw", lambda: api.bulk([("PlcProgram.Read", {"var": v, "mode": "raw"}) for v in fast]))

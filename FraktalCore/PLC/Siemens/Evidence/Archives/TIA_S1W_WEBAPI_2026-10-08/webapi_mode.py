import sys, pathlib, os, argparse
sys.path.insert(0, r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools")
import tia_webapi as w

pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin"
api = w.WebApi("192.168.0.10", pin, False)
api.login("fraktal")
mode = lambda: api.call("PlcProgram.Read", {"var": '"SpikeUnit".Mode'})
for kind, val, label in [(3, 1, "SET_MODE MANUAL"), (3, 0, "SET_MODE AUTO")]:
    rc = w.cmd_mailbox(api, argparse.Namespace(user="fraktal", root="SpikeUnit", kind=kind, int=val, timeout=3.0))
    print("%s rc=%d -> Mode=%s" % (label, rc, mode()))

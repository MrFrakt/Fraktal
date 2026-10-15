"""Why did the CPU reset an HTTPS connection? (a) idle keep-alive timeout on one
session, or (b) a second concurrent connection. Read-only."""
import sys, pathlib, os, time
sys.path.insert(0, r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools")
import tia_webapi as w

pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin"
reconnects = [0]
_orig = w.WebApi._connect
def _counting(self, trust_first=False):
    reconnects[0] += 1
    return _orig(self, trust_first)
w.WebApi._connect = _counting
V = {"var": '"FRK_Clock"."CycleMs"'}


def try_read(api, label):
    try:
        api.call("PlcProgram.Read", V)
        print("%-40s ok" % label)
        return True
    except Exception as e:  # noqa: BLE001 - diagnosis prints every failure class
        print("%-40s FAIL %s: %s" % (label, type(e).__name__, e))
        return False


# (a) idle gaps on one connection
for gap in (1, 2, 3, 5, 8, 12):
    api = w.WebApi("192.168.0.10", pin, False)
    api.login("fraktal")
    try_read(api, "fresh connection")
    time.sleep(gap)
    try_read(api, "after %d s idle" % gap)
    api.conn.close()

# (b) two connections, both kept busy alternately
a = w.WebApi("192.168.0.10", pin, False); a.login("fraktal")
b = w.WebApi("192.168.0.10", pin, False); b.login("fraktal")
ok = 0
for i in range(40):
    ok += try_read(a, "A #%d" % i) and try_read(b, "B #%d" % i)
print("alternating A/B: %d/40 pairs ok" % ok)
print("TCP+TLS connects so far:", reconnects[0])
# (c) does the token survive a new TCP connection?
tok = a.token
c = w.WebApi("192.168.0.10", pin, False)
c.token = tok
try_read(c, "token reused on a new connection")

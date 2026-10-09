"""S3 (polling cost): sample the PLC's own cycle time (FRK_Clock.CycleMs, set every
scan by FRK_ClockTick) while idle and while a second Web API session reads the
whole spike Unit in a tight loop. Two sessions at once also exercises S9's
'concurrent clients' item."""
import sys, json, pathlib, os, time, threading, statistics
sys.path.insert(0, r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools")
import tia_webapi as w

pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin"


def session():
    s = w.WebApi("192.168.0.10", pin, False)
    s.login("fraktal")
    return s


reconnects = [0]
_orig = w.WebApi._connect
def _counting(self, trust_first=False):
    reconnects[0] += 1
    return _orig(self, trust_first)
w.WebApi._connect = _counting
sampler = session()
CYCLE = ['"FRK_Clock"."CycleMs"', '"FRK_Clock"."Scans"']


def sample(seconds):
    cycles, t_end = [], time.time() + seconds
    first = None
    while time.time() < t_end:
        (c, _), (n, _) = sampler.bulk([("PlcProgram.Read", {"var": v}) for v in CYCLE])
        cycles.append(float(c))
        first = first or (time.perf_counter(), int(n))
        last = (time.perf_counter(), int(n))
    rate = (last[1] - first[1]) / (last[0] - first[0])
    return cycles, rate


def describe(label, cycles, rate):
    q = statistics.quantiles(cycles, n=20)
    print("%-28s samples=%d cycle ms: median=%.2f p95=%.2f max=%.2f  scans/s=%.0f (mean cycle %.2f ms)"
          % (label, len(cycles), statistics.median(cycles), q[18], max(cycles), rate, 1000.0 / rate))


idle = sample(20)
describe("idle (sampler only)", *idle)

loader = session()
leaves, _ = w.walk(loader, "SpikeUnit", 2000)
vars_ = [w.leaf_var(s) for s, _ in leaves]
stop = threading.Event()
loads = []


def load():
    while not stop.is_set():
        t0 = time.perf_counter()
        loader.bulk([("PlcProgram.Read", {"var": v}) for v in vars_])
        loads.append((time.perf_counter() - t0) * 1000)


th = threading.Thread(target=load, daemon=True)   # never outlives a failed main thread
th.start()
try:
    busy = sample(20)
finally:
    stop.set()
    th.join(timeout=10)
describe("full-tree polling (2nd session)", *busy)
print("loader: %d snapshots of %d leaves, median %.0f ms (concurrent with the sampler)"
      % (len(loads), len(vars_), statistics.median(loads)))
print("MaxCycleMs since start:", sampler.call("PlcProgram.Read", {"var": '"FRK_Clock"."MaxCycleMs"'}))
print("TCP+TLS connects (both sessions, incl. the 2 initial):", reconnects[0])

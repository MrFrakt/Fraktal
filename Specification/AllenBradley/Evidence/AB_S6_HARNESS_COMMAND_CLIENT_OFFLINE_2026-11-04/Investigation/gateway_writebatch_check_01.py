"""Drive the real Dart gateway with the O11 Python command client (offline).

The gateway runs over a recording upstream with write root ``Press``. Checks:
the gateway accepts the client's loopback origin and request; it forwards
exactly the nine Core arguments then ``Sequence``, with the client's types; a
repeated sequence is refused as a result, not a transport failure; a root
outside the write scope is refused with an error. Prints a JSON verdict.
"""
from pathlib import Path
import json
import subprocess
import sys

R = Path(__file__).resolve().parents[5]
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0, str(T))
import fraktal_ab_harness_commands as hc  # noqa: E402

DART = Path('C:/work/fraktal-toolchains/flutter-3.47.5/bin/dart.bat')
PACKAGES = R / 'FraktalCore/HMI/gateway/.dart_tool/package_config.json'
PEER = Path(__file__).with_name('gateway_writebatch_peer.dart')

peer = subprocess.Popen([str(DART), f'--packages={PACKAGES}', str(PEER)], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    port = json.loads(peer.stdout.readline())['port']
    client = hc.GatewayCommands(f'ws://127.0.0.1:{port}/fraktal', timeout=10)
    first = client.write_batch('Press', 42, Kind=4, TargetPath='Press.Door', IntValue=2,
                               BoolValue=True, DurationMs=1500)
    repeated = client.write_batch('Press', 42, Kind=4)
    outside = client.write_batch('Other', 43, Kind=4)
    client.close()
    peer.stdin.write('done\n')
    peer.stdin.flush()
    batches = json.loads(peer.stdout.readline())['batches']
finally:
    try:
        peer.wait(timeout=30)
    except subprocess.TimeoutExpired:
        peer.kill()
expected = hc.encode('Press', 42, dict(Kind=4, TargetPath='Press.Door', IntValue=2,
                                       BoolValue=True, DurationMs=1500))['writes']
checks = dict(
    acceptedLoopbackOriginAndRequest=first == hc.BatchReply(True, True, None),
    forwardedExactlyTheClientRequest=batches == [expected],
    repeatedSequenceRefusedAsResult=repeated.ok is True and repeated.result is False,
    outsideRootRefusedWithError=outside.ok is False and 'HmiRequest scope' in (outside.error or ''),
    peerExit=peer.returncode)
verdict = dict(passed=all(v is True for k, v in checks.items() if k != 'peerExit')
               and peer.returncode == 0, checks=checks,
               replies=dict(first=first.__dict__, repeated=repeated.__dict__,
                            outside=outside.__dict__),
               forwarded=batches, controllerAccess=False)
print(json.dumps(verdict, indent=2))
raise SystemExit(0 if verdict['passed'] else 1)

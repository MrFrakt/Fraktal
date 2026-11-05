"""Both offline v38 targets for the S6 host-services candidate: build, read back, audit.

No controller access: the SDK builds and saves offline only.
"""
from pathlib import Path
import hashlib, json, subprocess, sys

W = Path(__file__).parent
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
SOURCE = W / 's6_host_02.L5X'
SHA = 'D96287645769EB5A8ED6E53EEDE86C5196377030B16C9F62EED8A716D8181F29'
SDK = T / 'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'


def run(label, *args):
    return subprocess.run([sys.executable, str(W / 'run_logged.py'), label, *map(str, args)], cwd=R).returncode


assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == SHA
exits = {}
for target in ('EchoController', 'PhysicalController'):
    output = W / f'{target}_readback_02.L5X'
    assert not output.exists()
    exits['build_' + target] = run(f'build_{target}_02', SDK, '--build-readback', SOURCE, output, target)
    exits['readback_' + target] = run(f'readback_{target}_02', sys.executable, T / 'fraktal_ab_readback.py', SOURCE, output)
    exits['audit_' + target] = run(f'audit_{target}_02', sys.executable, T / 'fraktal_ab_sdk_log_gate.py',
                                   W / f'build_{target}_02.log', '--require', 'Open project', '--require', 'Build',
                                   '--require', 'Save As')
result = dict(passed=all(v == 0 for v in exits.values()), exits=exits, sourceSha256=SHA, controllerAccess=False,
              downloads=0)
with (W / 'build_targets_02.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)

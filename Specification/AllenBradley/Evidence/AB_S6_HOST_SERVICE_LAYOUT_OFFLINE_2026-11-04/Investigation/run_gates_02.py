"""Second gate set: documents after the record exists, the cross-language
golden's determinism, and the Dart decoder gates. No controller is contacted.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
H = R / 'FraktalCore/HMI'
FLUTTER = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat'
PY = sys.executable
exits = {}


def run(label, cwd, *args):
    exits[label] = subprocess.run([PY, str(I / 'run_logged_at.py'), label, str(cwd), *map(str, args)],
                                  cwd=R).returncode


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


run('ab_spec_02', R, PY, 'tools/check_ab_spec.py')
run('consistency_strict_02', R, PY, 'tools/check_consistency.py', '--strict')
regenerated = G / 'v611_golden_regenerated_01.json'
run('golden_regenerate_01', R, PY, I / 'write_v611_golden_01.py', T, regenerated)
fixture = H / 'test/fixtures/cip_host_services_v611.json'
golden = dict(fixtureSha256=digest(fixture),
              regeneratedSha256=digest(regenerated) if regenerated.exists() else None)
golden['identical'] = golden['fixtureSha256'] == golden['regeneratedSha256']
with (G / 'v611_golden_identity_01.json').open('x', encoding='utf-8') as f:
    json.dump(golden, f, indent=2)
run('dart_focused_01', H, FLUTTER, 'test', 'test/cip_host_services_manifest_test.dart',
    'test/cip_owner_revision_test.dart', 'test/cip_manifest_test.dart')
run('flutter_analyze_01', H, FLUTTER, 'analyze')
run('dart_client_analyze_01', H / 'packages/fraktal_opcua_client', FLUTTER.replace('flutter.bat', 'dart.bat'),
    'analyze')
run('flutter_full_01', H, FLUTTER, 'test')
summary = dict(passed=all(c == 0 for c in exits.values()) and golden['identical'], exits=exits,
               goldenIdentical=golden['identical'], controllerAccess=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (G / 'gate_summary_02.json').open('x', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

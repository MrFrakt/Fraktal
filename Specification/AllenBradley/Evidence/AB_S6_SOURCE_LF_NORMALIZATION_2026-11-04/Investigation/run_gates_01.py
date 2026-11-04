"""Normalize, then rerun the suites on the LF bytes. No controller is contacted."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
G.mkdir(exist_ok=True)
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
H = R / 'FraktalCore/HMI'
FLUTTER = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat'
PY = sys.executable
exits = {}


def run(label, cwd, *args):
    # Create-only log and exit record under this folder's Gates/.
    exits[label] = subprocess.run([PY, str(I / 'run_logged_at.py'), label, str(cwd), *map(str, args)],
                                  cwd=R).returncode


def sources():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(T.glob('*.py'))}


run('normalize_lf_01', R, PY, I / 'normalize_lf_01.py')
names = [r['file'] for r in json.loads((G / 'normalization_01.json').read_text(encoding='utf-8'))['files']]
run('diff_check_01', R, 'git', 'diff', '--check', '--', *names)
run('focused_host_01', R, PY, '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover', '-s', T, '-t', T,
    '-p', 'test_fraktal_ab_host_service*.py')
before = sources()
with (G / 'full_ab_source_bindings_before_01.json').open('x', encoding='utf-8') as f:
    json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sources=before), f, indent=2)
run('full_ab_01', R, PY, '-m', 'unittest', 'discover', '-s', T, '-t', T, '-q')
after = sources()
run('dart_focused_01', H, FLUTTER, 'test', 'test/cip_host_services_manifest_test.dart',
    'test/cip_owner_revision_test.dart', 'test/cip_manifest_test.dart')
run('flutter_analyze_01', H, FLUTTER, 'analyze')
run('flutter_full_01', H, FLUTTER, 'test')
summary = dict(passed=all(c == 0 for c in exits.values()) and before == after, exits=exits,
               sourcesUnchangedDuringSuite=before == after, pythonModules=len(before), controllerAccess=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (G / 'gate_summary_01.json').open('x', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

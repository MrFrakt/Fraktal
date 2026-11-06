"""Sequential offline gates for WP6.6 C4c, run 01, over unchanged source 12.

Source 14 builds/readbacks and Capacity run separately after source 13.
Native runtime qualification is deferred to S6-Q.
Every gate runs even if an earlier one fails; the summary lists every exit.
Runs 01/02 are retained superseded investigations: UTF-8 correction and legacy root-import isolation. Fresh root tests pass before run 03. No controller is contacted. The v38 builds, ACD and Capacity of source 12 ran
in the preparation workspace; their records are copied into Gates/Prepare at
sealing, without L5X or ACD.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
G.mkdir(exist_ok=True)
R = Path('C:/work/fraktal-ab-c4-20261106')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
H = R / 'FraktalCore/HMI'
DART = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
PY = sys.executable
exits = {}


def run(label, cwd, *args):
    exits[label] = subprocess.run([PY, str(I / 'run_logged_at.py'), label, str(cwd), *map(str, args)],
                                  cwd=R).returncode


def sources():
    return {p.relative_to(T).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest().upper()
            for p in sorted([*T.glob('*.py'), *T.glob('*.json')])}


def write(name, value):
    with (G / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2)


run('bind_sources_03', R, PY, I / 'bind_sources_01.py', G / 'source_bindings_03.json')
# Gateway inputs are rebound to C4b by hash; no Dart source changes in C4c.

before = sources()
write('full_ab_source_bindings_before_03.json',
      dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sources=before))
run('full_ab_03', T, PY, '-m', 'unittest', 'discover', '-s', T, '-t', T, '-q')
after = sources()
write('full_ab_source_bindings_result_03.json',
      dict(sourcesUnchangedDuringSuite=before == after, files=len(before),
           utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
run('root_03', R, PY, '-m', 'unittest', 'tools.test_check_consistency', 'tools.test_check_ab_spec',
    'tools.test_check_ab_contracts', 'tools.test_check_tia_contracts')
run('ab_spec_03', R, PY, 'tools/check_ab_spec.py')
run('ab_contracts_03', R, PY, 'tools/check_ab_contracts.py')
run('consistency_strict_03', R, PY, 'tools/check_consistency.py', '--strict')
summary = dict(passed=all(c == 0 for c in exits.values()) and before == after, exits=exits,
               sourcesUnchangedDuringSuite=before == after, controllerAccess=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write('gate_summary_03.json', summary)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

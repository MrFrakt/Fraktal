"""Second run of the set-operations gates, after the current-export test fix.

Every gate runs even if an earlier one fails; the summary lists every exit.
No controller is contacted and no image is built for download.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
G.mkdir(exist_ok=True)
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
PY = sys.executable
exits = {}


def run(label, cwd, *args):
    exits[label] = subprocess.run([PY, str(I / 'run_logged_at.py'), label, str(cwd), *map(str, args)],
                                  cwd=R).returncode


def sources():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(T.glob('*.py'))}


def write(name, value):
    with (G / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2)


run('bind_sources_02', R, PY, I / 'bind_sources_02.py', G / 'source_bindings_02.json')
run('focused_host_02', T, PY, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v',
    'test_fraktal_ab_host_sets', 'test_fraktal_ab_host_services', 'test_fraktal_ab_host_service_binding')
run('mutation_host_sets_02', T, PY, I / 'mutate_host_sets_02.py', G / 'mutation_host_sets_02.json')
before = sources()
write('full_ab_source_bindings_before_02.json',
      dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sources=before))
run('full_ab_02', T, PY, '-m', 'unittest', 'discover', '-s', T, '-t', T, '-q')
after = sources()
write('full_ab_source_bindings_result_02.json',
      dict(sourcesUnchangedDuringSuite=before == after, pythonModules=len(before),
           utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
run('root_02', R, PY, '-m', 'unittest', 'tools.test_check_consistency', 'tools.test_check_ab_spec',
    'tools.test_check_ab_contracts', 'tools.test_check_tia_contracts')
run('ab_spec_02', R, PY, 'tools/check_ab_spec.py')
run('ab_contracts_02', R, PY, 'tools/check_ab_contracts.py')
run('consistency_strict_02', R, PY, 'tools/check_consistency.py', '--strict')
summary = dict(passed=all(c == 0 for c in exits.values()) and before == after, exits=exits,
               sourcesUnchangedDuringSuite=before == after, controllerAccess=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write('gate_summary_02.json', summary)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

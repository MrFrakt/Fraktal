"""Sequential offline gates for the O11 harness command client checkpoint.

Every gate runs even if an earlier one fails; the summary lists every exit.
No controller is contacted.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
PY = sys.executable
exits = {}


def run(label, *args):
    exits[label] = subprocess.run([PY, str(I / 'run_logged.py'), label, *map(str, args)],
                                  cwd=R).returncode


def sources():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(T.glob('*.py'))}


def write(name, value):
    with (G / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2)


run('focused_commands_01', PY, '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover', '-v',
    '-s', T, '-t', T, '-p', 'test_fraktal_ab_harness_commands.py')
run('focused_live_01', PY, '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover',
    '-s', T, '-t', T, '-p', 'test_fraktal_ab_canonical_live.py')
run('mutation_commands_01', PY, I / 'mutate_commands_01.py', T)
before = sources()
write('full_ab_source_bindings_before_01.json',
      dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sources=before))
run('full_ab_01', PY, '-m', 'unittest', 'discover', '-s', T, '-t', T, '-q')
after = sources()
write('full_ab_source_bindings_result_01.json',
      dict(sourcesUnchangedDuringSuite=before == after, pythonModules=len(before),
           utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
run('root_01', PY, '-m', 'unittest', 'tools.test_check_consistency', 'tools.test_check_ab_spec',
    'tools.test_check_ab_contracts', 'tools.test_check_tia_contracts')
run('ab_spec_01', PY, 'tools/check_ab_spec.py')
run('ab_contracts_01', PY, 'tools/check_ab_contracts.py')
run('consistency_strict_01', PY, 'tools/check_consistency.py', '--strict')
summary = dict(passed=all(c == 0 for c in exits.values()) and before == after, exits=exits,
               sourcesUnchangedDuringSuite=before == after, controllerAccess=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write('gate_summary_01.json', summary)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

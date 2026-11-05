"""The document gates again, after O12's text was corrected in the review and the plan.

Run 01 bound both documents before the correction. Only Markdown changed
after it, and no tool source did, so this pass rebinds every source and
reruns the document and root gates. The full AB suite of run 01 stands.
"""
from pathlib import Path
import datetime, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
R = Path('C:/Users/SoftIndVM/Fraktal')
PY = sys.executable
exits = {}


def run(label, cwd, *args):
    exits[label] = subprocess.run([PY, str(I / 'run_logged_at.py'), label, str(cwd), *map(str, args)],
                                  cwd=R).returncode


run('bind_sources_02', R, PY, I / 'bind_sources_01.py', G / 'source_bindings_02.json')
run('root_02', R, PY, '-m', 'unittest', 'tools.test_check_consistency', 'tools.test_check_ab_spec',
    'tools.test_check_ab_contracts', 'tools.test_check_tia_contracts')
run('ab_spec_02', R, PY, 'tools/check_ab_spec.py')
run('ab_contracts_02', R, PY, 'tools/check_ab_contracts.py')
run('consistency_strict_02', R, PY, 'tools/check_consistency.py', '--strict')
first = json.loads((G / 'source_bindings_01.json').read_text(encoding='utf-8'))
second = json.loads((G / 'source_bindings_02.json').read_text(encoding='utf-8'))
changed = sorted(a['file'] for a, b in zip(first['files'], second['files']) if a['sha256'] != b['sha256'])
summary = dict(passed=all(c == 0 for c in exits.values()) and all(n.endswith('.md') for n in changed),
               exits=exits, changedSinceRun01=changed, controllerAccess=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (G / 'gate_summary_02.json').open('x', encoding='utf-8', newline='\n') as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

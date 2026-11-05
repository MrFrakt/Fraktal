"""Sequential offline gates for WP6.6 C0b, the O12 document revision: run 02.

Run 01 failed one Dart test: the host bench rendered a predecessor document
through the new revision, which no longer moves without host services. The
bench now stamps it with the recorded pre-collapse revision.

Every gate runs even if an earlier one fails; the summary lists every exit.
No controller is contacted. The v38 builds, ACD and Capacity of source 07
ran in the preparation workspace (C:/work/fraktal-ab-s6-host-20261104/prepare);
their records are copied into Gates/Prepare at sealing, without L5X or ACD.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
G.mkdir(exist_ok=True)
R = Path('C:/Users/SoftIndVM/Fraktal')
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


run('bind_sources_02', R, PY, I / 'bind_sources_01.py', G / 'source_bindings_02.json')
run('dart_analyze_gateway_02', H / 'gateway', DART, 'analyze')
run('dart_test_gateway_02', H / 'gateway', DART, 'test', '-r', 'expanded')
run('focused_python_02', T, PY, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v',
    'test_fraktal_ab_document_revision', 'test_fraktal_ab_host_revision_compatibility',
    'test_fraktal_ab_s3k_revision_compatibility', 'test_fraktal_ab_sets', 'test_fraktal_ab_host_sets',
    'test_fraktal_ab_host_live', 'test_fraktal_ab_live', 'test_fraktal_ab_schema_identity',
    'test_fraktal_ab_manifest_capacity', 'test_fraktal_ab_owner_read_fixture', 'test_fraktal_ab_press_canonical',
    'test_fraktal_ab_line', 'test_fraktal_ab_models', 'test_fraktal_ab_resources', 'test_fraktal_ab_genealogy',
    'test_fraktal_ab_text_resources', 'test_fraktal_ab_signal_tower', 'test_fraktal_ab_v611_image')
before = sources()
write('full_ab_source_bindings_before_02.json',
      dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sources=before))
run('full_ab_02', T, PY, '-m', 'unittest', 'discover', '-s', T, '-t', T, '-q')
after = sources()
write('full_ab_source_bindings_result_02.json',
      dict(sourcesUnchangedDuringSuite=before == after, files=len(before),
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

"""Sequential offline gates for the Dart host adapter checkpoint, third run.

Run 01 was stopped during its Dart tests to take two review fixes: the tray
now clears the adapter's restart backoff wherever the operator clears the
gateway's, and the executable checks its port and rediscovers a controller
without host services once a minute. Run 02 was stopped during its tray
configure step: review found that no test reached the real CIP port, so
the configuration-set scenarios now also run through `CipHostIngress` over
the bench's wire, with the port's own tests beside them, and discovery now
closes its read connection when a controller serves nothing. The partial
logs of runs 01 and 02 are kept unchanged.

Every gate runs even if an earlier one fails; the summary lists every exit.
No controller is contacted. Build outputs go to a temporary folder outside the
evidence (no binary is archived); only their logs are kept.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys, tempfile

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
G.mkdir(exist_ok=True)
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
H = R / 'FraktalCore/HMI'
FLUTTER = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat'
DART = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
CMAKE = 'C:/Program Files/Microsoft Visual Studio/18/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
PY = sys.executable
BUILD = Path(tempfile.mkdtemp(prefix='fraktal_s6_dart_'))
exits = {}


def run(label, cwd, *args):
    exits[label] = subprocess.run([PY, str(I / 'run_logged_at.py'), label, str(cwd), *map(str, args)],
                                  cwd=R).returncode


def sources():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(T.glob('*.py'))}


def write(name, value):
    with (G / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2)


run('bind_sources_03', R, PY, I / 'bind_sources_01.py', G / 'source_bindings_03.json')
run('dart_analyze_client_03', H / 'packages/fraktal_opcua_client', DART, 'analyze')
run('dart_analyze_gateway_03', H / 'gateway', DART, 'analyze')
run('dart_test_gateway_03', H / 'gateway', DART, 'test', '-r', 'expanded')
run('dart_compile_adapter_03', H / 'gateway', DART, 'compile', 'exe', 'bin/fraktal_host_adapter.dart',
    '-o', BUILD / 'fraktal_host_adapter.exe')
run('adapter_usage_03', H / 'gateway', BUILD / 'fraktal_host_adapter.exe', '--help')
run('tray_configure_03', H, CMAKE, '-S', 'native/opcua', '-B', BUILD / 'native', '-DCMAKE_BUILD_TYPE=Release')
run('tray_build_03', H, CMAKE, '--build', BUILD / 'native', '--config', 'Release', '--target', 'fraktal_gateway_tray')
run('flutter_analyze_03', H, FLUTTER, 'analyze')
run('flutter_full_03', H, FLUTTER, 'test')
run('focused_python_03', T, PY, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v',
    'test_fraktal_ab_host_service_binding', 'test_fraktal_ab_host_services', 'test_fraktal_ab_host_sets',
    'test_fraktal_ab_host_live', 'test_fraktal_ab_sets', 'test_fraktal_ab_live', 'test_fraktal_ab_host_events',
    'test_fraktal_ab_canonical_reader')
before = sources()
write('full_ab_source_bindings_before_03.json',
      dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sources=before))
run('full_ab_03', T, PY, '-m', 'unittest', 'discover', '-s', T, '-t', T, '-q')
after = sources()
write('full_ab_source_bindings_result_03.json',
      dict(sourcesUnchangedDuringSuite=before == after, pythonModules=len(before),
           utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
run('root_03', R, PY, '-m', 'unittest', 'tools.test_check_consistency', 'tools.test_check_ab_spec',
    'tools.test_check_ab_contracts', 'tools.test_check_tia_contracts')
run('ab_spec_03', R, PY, 'tools/check_ab_spec.py')
run('ab_contracts_03', R, PY, 'tools/check_ab_contracts.py')
run('consistency_strict_03', R, PY, 'tools/check_consistency.py', '--strict')
# The usage request exits 64 by design; every other gate must exit 0.
expected = {label: 64 if label == 'adapter_usage_03' else 0 for label in exits}
summary = dict(passed=exits == expected and before == after, exits=exits, expectedExits=expected,
               sourcesUnchangedDuringSuite=before == after, controllerAccess=False, buildFolder=str(BUILD),
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write('gate_summary_03.json', summary)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

"""Sequential offline gates for the S6 row-body batching checkpoint.

No controller is contacted. Every gate runs even if an earlier one fails, so a
failure is recorded beside the rest; the summary lists every exit code.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
PY = sys.executable
FLUTTER = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat'
S5 = '979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162'
exits = {}


def run(label, *args):
    result = subprocess.run([PY, str(I / 'run_logged.py'), label, *map(str, args)], cwd=R)
    exits[label] = result.returncode
    return result.returncode == 0


def sources():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(T.glob('*.py'))}


def write(name, value):
    with (G / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2)


G.mkdir(exist_ok=True)
run('focused_live_01', PY, '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover', '-v',
    '-s', T, '-t', T, '-p', 'test_fraktal_ab_canonical_live.py')
run('mutation_batching_01', PY, I / 'mutate_batching_01.py', T)
before = sources()
write('full_ab_source_bindings_before_01.json',
      dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sources=before))
run('full_ab_01', PY, '-m', 'unittest', 'discover', '-s', T, '-t', T, '-q')
after = sources()
write('full_ab_source_bindings_result_01.json',
      dict(sourcesUnchangedDuringSuite=before == after, pythonModules=len(before),
           utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
run('root_01', PY, '-m', 'unittest', 'tools.test_check_consistency', 'tools.test_check_ab_spec',
    'tools.test_check_ab_contracts')
run('ab_spec_01', PY, 'tools/check_ab_spec.py')
run('ab_contracts_01', PY, 'tools/check_ab_contracts.py')
run('consistency_strict_01', PY, 'tools/check_consistency.py', '--strict')
run('canonical_contract_01', PY, T / 'fraktal_ab_s9_contract.py', '--flutter', FLUTTER)

work = I.parent / 'Build'
work.mkdir(exist_ok=True)
source = work / 's5_regenerated_01.L5X'
assert not source.exists()
regenerated = run('regenerate_s5_01', PY, T / 'fraktal_ab_generate.py', 'C:/work/echo38_5580_seed.L5X',
                  source, '--declaration', 'fraktal_ab_genealogy_s4b_owner_demo')
digest = hashlib.sha256(source.read_bytes()).hexdigest().upper() if regenerated else None
sdk = T / 'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
for target in ('EchoController', 'PhysicalController'):
    output = work / (target + '_s5_readback_01.L5X')
    assert not output.exists()
    run('build_' + target + '_01', sdk, '--build-readback', source, output, target)
    run('readback_' + target + '_01', PY, T / 'fraktal_ab_readback.py', source, output)
    run('audit_' + target + '_01', PY, T / 'fraktal_ab_sdk_log_gate.py',
        G / ('build_' + target + '_01.log'),
        '--require', 'Open project', '--require', 'Build', '--require', 'Save As')
summary = dict(passed=all(code == 0 for code in exits.values()) and digest == S5 and before == after,
               exits=exits, generatedSourceSha256=digest, generatedSourceByteIdenticalToS5=digest == S5,
               sourcesUnchangedDuringSuite=before == after, controllerAccess=False, downloads=0,
               originalGenealogyAcdOpened=False,
               utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write('gate_summary_01.json', summary)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)

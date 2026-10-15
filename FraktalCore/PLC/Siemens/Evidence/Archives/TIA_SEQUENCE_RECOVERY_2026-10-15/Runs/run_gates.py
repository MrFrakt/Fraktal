import hashlib, json, subprocess, sys
from pathlib import Path
work = Path(__file__).resolve().parent
repo = Path('C:/Projects/Fraktal')
gates = {
    'tools_verified': ['python', '-m', 'unittest', 'discover', '-s', 'FraktalCore/PLC/Siemens/tools', '-t', 'FraktalCore/PLC/Siemens/tools'],
    'consistency_verified': ['python', 'tools/check_consistency.py'],
    'consistency_tests_verified': ['python', '-m', 'unittest', 'tools.test_check_consistency'],
    'lint_verified': ['python', 'FraktalCore/PLC/Siemens/tools/tia_lint.py'],
}
results = {}
for name, command in gates.items():
    path = work/(name+'.log')
    with path.open('xb') as stream:
        result = subprocess.run(command, cwd=repo, stdout=stream, stderr=subprocess.STDOUT)
    results[name] = {'command': command, 'exit_code': result.returncode, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    assert result.returncode == 0, name
with (work/'gates_verified.json').open('x', encoding='ascii') as stream:
    json.dump(results, stream, indent=2); stream.write('\n')
print(json.dumps({name: row['exit_code'] for name, row in results.items()}))

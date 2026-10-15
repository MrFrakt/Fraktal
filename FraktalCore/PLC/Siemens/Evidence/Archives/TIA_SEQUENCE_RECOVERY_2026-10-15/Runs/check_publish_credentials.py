import json, os, subprocess, sys
from pathlib import Path
repo = Path('C:/Projects/Fraktal')
patterns = []
for name in ('FRAKTAL_TIA_ADMIN_PIN', 'FRAKTAL_TIA_OPERATOR_PIN', 'FRAKTAL_TIA_WEB_PASSWORD'):
    secret = os.environ[name]
    patterns += [secret.encode('utf-8'), secret.encode('utf-16le')]
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=repo).decode('utf-8').split('\0')
checked, findings = 0, []
for name in paths:
    path = repo/name
    if not name or not path.is_file():
        continue
    if not (name.startswith(('FraktalCore/PLC/Siemens/', 'Specification/Siemens/', 'FraktalCore/HMI/')) or name in ('AGENTS.md', 'analysis_options.yaml') or name.startswith('.vscode/')):
        continue
    raw = path.read_bytes()
    checked += 1
    if any(pattern in raw for pattern in patterns):
        findings.append(name)
with Path(sys.argv[1]).open('x', encoding='ascii') as stream:
    json.dump({'checked': checked, 'plaintext_credential_paths': findings, 'complete': not findings}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'checked': checked, 'plaintext_credentials_found': len(findings)}))
assert not findings, 'Plaintext credential matches must be removed from publication scope'

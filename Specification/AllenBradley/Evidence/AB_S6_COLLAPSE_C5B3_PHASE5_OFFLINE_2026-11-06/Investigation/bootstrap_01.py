"""Bootstrap and freeze C5b3 Phase 5 migration entry state."""
from pathlib import Path
import datetime, hashlib, json, subprocess

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()

def save(name, value):
    with (W / name).open('x', encoding='utf-8') as out:
        json.dump(value, out, indent=2)

parent = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
assert parent == '7b793c516bc48bb50ae5b2337e99b8ab63e001bd', parent
save('entry_01.json', dict(
    parentCommit=parent,
    startUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='C5b3 Phase 5 metrics/reports/run-styles canonical and O10 migration, offline',
    controllerAccess=False,
))
owner = ['.vscode/settings.json', 'FraktalCore/PLC/Siemens/Tests/Manifest/README.md', 'analysis_options.yaml']
save('unrelated_before.json', [dict(path=p, sha256=sha(R / p)) for p in owner])
files = subprocess.check_output(
    ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', 'FraktalCore/PLC/Allen-Bradley/tools'],
    cwd=R,
).decode().split('\0')
save('tools_freeze_01.json', dict(
    head=parent,
    files=[dict(path=p, sha256=sha(R / p)) for p in sorted(set(files) - {''})],
))
print(json.dumps(dict(passed=True, parent=parent, files=len(set(files) - {''}))))

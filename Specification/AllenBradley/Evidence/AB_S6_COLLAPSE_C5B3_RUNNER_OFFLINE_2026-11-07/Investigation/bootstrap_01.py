from pathlib import Path
import datetime, hashlib, json, subprocess

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def save(name, value):
    with (W / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2)


parent = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
assert parent == '6865e75fd4e224bd917c9874acc4dfd58d23d84f'
save(
    'entry_01.json',
    dict(
        parentCommit=parent,
        startUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='C5b3 shared runner bootstrap, configuration preservation, tower snapshot and disconnect lifecycle, offline; standalone press launcher follows',
        controllerAccess=False,
    ),
)
save(
    'unrelated_before.json',
    [
        dict(path=p, sha256=sha(R / p))
        for p in (
            '.vscode/settings.json',
            'FraktalCore/PLC/Siemens/Tests/Manifest/README.md',
            'analysis_options.yaml',
        )
    ],
)
print(json.dumps(dict(passed=True, parent=parent, controllerAccess=False)))

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
assert parent == 'c2c0cdb873ff3a694a1d480839e55785bb7097f4'
save(
    'entry_01.json',
    dict(
        parentCommit=parent,
        startUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='C5b3 remaining station-reading HX harnesses (fraktal_ab_press_parity.py, fraktal_ab_phase1_execute.py..fraktal_ab_phase4_execute.py, fraktal_ab_s3_execute.py) migration to canonical/O10 views, offline',
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

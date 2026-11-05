"""run_logged.py with an explicit working directory: label, cwd, command..."""
from pathlib import Path
import datetime, json, subprocess, sys

G = Path(__file__).resolve().parents[1] / 'Gates'
G.mkdir(exist_ok=True)
label, cwd = sys.argv[1], sys.argv[2]
assert label.replace('_', '').isalnum()
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (G / (label + '.log')).open('x', encoding='utf-8') as f:
    result = subprocess.run(sys.argv[3:], cwd=cwd, stdout=f, stderr=subprocess.STDOUT, text=True)
with (G / (label + '_exit.json')).open('x', encoding='utf-8') as f:
    json.dump(dict(startUtc=start, endUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   cwd=cwd, command=sys.argv[3:], exitCode=result.returncode), f, indent=2)
print(json.dumps(dict(label=label, exitCode=result.returncode)))
raise SystemExit(result.returncode)

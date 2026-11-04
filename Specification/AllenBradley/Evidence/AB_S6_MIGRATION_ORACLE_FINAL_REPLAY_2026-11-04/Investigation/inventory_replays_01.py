"""WP6.3 inventory of every sealed replay run (read-only).

A sealed replay is an evidence ``*replay*_exit.json`` record outside archived
source snapshots. For each one this records the evidence folder, recorded
command and exit code, the script and its session workspace (presence, size,
ACD/BAK bytes), and the absolute ``C:/work`` paths the script itself embeds.
Writes one create-only JSON file; runs nothing.
"""
import json
import os
from pathlib import Path
import re
import sys

R = Path(__file__).resolve().parents[5]
E = R / 'Specification/AllenBradley/Evidence'
ABSOLUTE = re.compile(r'C:[/\\]+work[/\\]+[^\'"\s,)]+')


def norm(value):
    return str(value).replace('\\', '/')


rows = []
for exit_record in sorted(E.rglob('*replay*_exit.json')):
    relative = exit_record.relative_to(E).as_posix()
    if '/Source/' in relative or '/Sources/' in relative:
        continue
    record = json.loads(exit_record.read_text(encoding='utf-8'))
    command = [norm(c) for c in (record.get('command') or [])]
    script = next((c for c in command if c.endswith(('.py', '.dart'))), None)
    workspace = None
    if script:
        match = re.match(r'(C:/work/[^/]+/[^/]+)/', script)
        workspace = match.group(1) if match else None
    size = acd = files = 0
    if workspace and os.path.isdir(workspace):
        for root, unused, names in os.walk(workspace):
            for name in names:
                n = os.path.getsize(os.path.join(root, name))
                size, files = size + n, files + 1
                if name.lower().endswith(('.acd', '.bak')):
                    acd += n
    embedded = []
    if script and os.path.isfile(script):
        embedded = sorted({norm(m) for m in ABSOLUTE.findall(
            Path(script).read_text(encoding='utf-8', errors='replace'))})
    label = exit_record.name[:-len('_exit.json')]
    sealed = [p.name for p in exit_record.parent.iterdir()
              if p.name.startswith(label) and not p.name.endswith('_exit.json')]
    rows.append(dict(exitRecord=relative, label=label, exitCode=record.get('exitCode'),
                     command=command, script=script, scriptPresent=bool(script and os.path.isfile(script)),
                     kind='dart' if script and script.endswith('.dart') else 'python',
                     workspace=workspace, workspacePresent=bool(workspace and os.path.isdir(workspace)),
                     workspaceFiles=files, workspaceBytes=size, workspaceAcdBakBytes=acd,
                     embeddedAbsolutePaths=embedded, sealedOutputsBesideExit=sorted(sealed)))
out = Path(sys.argv[1])
with out.open('x', encoding='utf-8') as f:
    json.dump(dict(schema='fraktal.ab.s6-wp63-replay-inventory', schemaVersion=1, replays=rows), f, indent=2)
for r in rows:
    print(f"{r['exitRecord'].split('/')[0][:52]:52s} {r['label'][:28]:28s} exit={r['exitCode']} "
          f"{r['kind']:6s} ws={'ok' if r['workspacePresent'] else 'MISSING'} "
          f"MB={r['workspaceBytes']/1e6:7.1f} acdMB={r['workspaceAcdBakBytes']/1e6:6.1f} "
          f"abs={len(r['embeddedAbsolutePaths'])} sealed={len(r['sealedOutputsBesideExit'])}")
print(len(rows), 'sealed replay runs')

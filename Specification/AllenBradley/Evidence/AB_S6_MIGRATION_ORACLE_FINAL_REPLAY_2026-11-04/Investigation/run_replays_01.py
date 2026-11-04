"""WP6.3: re-execute every sealed Python replay on the pre-collapse tree.

Each replay runs from a fresh copy of its session workspace with today's
tools; originals are never written. Guards:

- every pre-existing file in an original workspace or referenced session
  folder is made read-only for the whole run, with the exact list written
  first and restored in ``finally``;
- (size, mtime) fingerprints of those trees are compared before and after.

A create-only output already present in the copy is deleted from the copy and
the run repeated; every attempt is logged. A replay reproduces when its exit
code equals the recorded one and every produced file with a same-named sealed
counterpart is equal as canonical JSON. Dart wire-timing benchmarks are
excluded: they measure latency, not oracle decoding.
"""
import datetime
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
R = Path('C:/Users/SoftIndVM/Fraktal')
E = R / 'Specification/AllenBradley/Evidence'
WORK = Path(sys.argv[2])
INVENTORY = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))['replays']
EXISTS = re.compile(r"FileExistsError: \[Errno 17\] File exists: '([^']+)'")
IGNORE = shutil.ignore_patterns('*.ACD', '*.acd', '*.BAK', '*.bak', '*.Sem', '__pycache__')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fingerprint(roots):
    result = {}
    for root in sorted(roots):
        for base, unused, names in os.walk(root):
            for name in names:
                p = os.path.join(base, name)
                s = os.stat(p)
                result[p.replace('\\', '/')] = [s.st_size, s.st_mtime_ns]
    return result


def load(path):
    data = path.read_bytes()
    if path.name.endswith('.gz'):
        data = gzip.decompress(data)
    return json.loads(data)


def differences(a, b, at='', out=None, limit=40):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if type(a) is not type(b):
        out.append(at or '/')
    elif isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append(f'{at}/{key}')
            else:
                differences(a[key], b[key], f'{at}/{key}', out, limit)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f'{at}[len]')
        for i, (x, y) in enumerate(zip(a, b)):
            differences(x, y, f'{at}[{i}]', out, limit)
    elif a != b:
        out.append(at or '/')
    return out


selected = [r for r in INVENTORY if r['kind'] == 'python']
excluded = [dict(exitRecord=r['exitRecord'], reason='Dart wire-timing benchmark; measures latency, '
                 'not oracle decoding') for r in INVENTORY if r['kind'] != 'python']
originals = set()
for r in selected:
    for path in [r['workspace'], *r['embeddedAbsolutePaths']]:
        if path:
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            if os.path.isdir(folder):
                originals.add(folder.replace('\\', '/'))
    for arg in r['command']:
        if arg.startswith('C:/work/') and os.path.exists(arg):
            originals.add(os.path.dirname(arg).replace('\\', '/'))
G.mkdir(exist_ok=True)
WORK.mkdir(parents=True, exist_ok=False)
before = fingerprint(originals)
protected = [p for p in before if os.stat(p).st_mode & stat.S_IWRITE]
with (G / 'protected_originals_01.json').open('x', encoding='utf-8') as f:
    json.dump(dict(utc=now(), roots=sorted(originals), files=protected), f, indent=1)
results = []
try:
    for p in protected:
        os.chmod(p, stat.S_IREAD)
    for number, r in enumerate(selected, 1):
        slug = f"{number:02d}_{r['label']}"
        folder = WORK / slug
        folder.mkdir()
        original = copied = None
        if r['workspace'] and r['workspacePresent']:
            original = r['workspace'].replace('\\', '/')
            copy = folder / Path(original).name
            shutil.copytree(original, copy, ignore=IGNORE)
            copied = str(copy).replace('\\', '/')
            # The three spellings a script may embed: forward, raw backslash,
            # and backslash escaped inside a Python string literal.
            spellings = [(original, copied),
                         (original.replace('/', '\\\\'), copied.replace('/', '\\\\')),
                         (original.replace('/', '\\'), copied.replace('/', '\\'))]
            for script in copy.rglob('*.py'):
                text = script.read_text(encoding='utf-8', errors='surrogateescape')
                changed = text
                for old, new in spellings:
                    changed = changed.replace(old, new)
                if changed != text:
                    os.chmod(script, stat.S_IWRITE | stat.S_IREAD)
                    script.write_text(changed, encoding='utf-8', errors='surrogateescape')
        sealed_dir = (E / r['exitRecord']).parent
        sealed_names = set(r['sealedOutputsBesideExit'])
        command = [sys.executable]
        for arg in r['command'][1:]:
            if original and (arg == original or arg.startswith(original + '/')):
                arg = copied + arg[len(original):]
            elif arg.startswith('C:/work/') and os.path.basename(arg) in sealed_names:
                arg = str(folder / os.path.basename(arg)).replace('\\', '/')
            command.append(arg)
        for p in folder.rglob('*'):
            if p.is_file():
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        listing = {p: p.stat().st_mtime_ns for p in folder.rglob('*') if p.is_file()}
        attempts, removed, started = [], [], now()
        for attempt in range(1, 7):
            log = G / f'{slug}_attempt_{attempt:02d}.log'
            with log.open('x', encoding='utf-8') as out:
                proc = subprocess.run(command, cwd=R, stdout=out, stderr=subprocess.STDOUT,
                                      text=True, timeout=3600)
            text = log.read_text(encoding='utf-8', errors='replace')
            attempts.append(dict(attempt=attempt, exitCode=proc.returncode, log=log.name))
            match = EXISTS.search(text)
            target = Path(match.group(1)) if match else None
            if proc.returncode and target is not None and target.resolve().is_relative_to(folder.resolve()) \
                    and target.exists():
                removed.append(str(target.relative_to(folder)).replace('\\', '/'))
                target.unlink()
                listing.pop(target, None)
                continue
            break
        produced = sorted(p for p in folder.rglob('*') if p.is_file()
                          and (p not in listing or listing[p] != p.stat().st_mtime_ns))
        compared = []
        for p in produced:
            twin = sealed_dir / p.name
            if p.name.endswith(('.json', '.json.gz')) and twin.is_file():
                try:
                    diff = differences(load(twin), load(p))
                except ValueError as error:
                    diff = [f'unreadable: {error}']
                compared.append(dict(file=p.name, equal=not diff, differences=diff))
        final = attempts[-1]['exitCode']
        results.append(dict(number=number, slug=slug, exitRecord=r['exitRecord'],
                            recordedExit=r['exitCode'], replayExit=final, attempts=attempts,
                            removedFromCopy=removed, command=command, startedUtc=started, endedUtc=now(),
                            produced=[str(p.relative_to(folder)).replace('\\', '/') for p in produced],
                            compared=compared, contentCompared=bool(compared),
                            reproduced=final == r['exitCode'] and all(c['equal'] for c in compared)))
        print(json.dumps(dict(slug=slug, recorded=r['exitCode'], replay=final,
                              compared=len(compared), reproduced=results[-1]['reproduced'])), flush=True)
finally:
    for p in protected:
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
after = fingerprint(originals)
changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
summary = dict(schema='fraktal.ab.s6-wp63-replay-run', schemaVersion=1, utc=now(),
               selected=len(selected), excluded=excluded, results=results,
               reproduced=sum(r['reproduced'] for r in results),
               reproducedWithContent=sum(r['reproduced'] and r['contentCompared'] for r in results),
               exitOnly=[r['slug'] for r in results if r['reproduced'] and not r['contentCompared']],
               notReproduced=[r['slug'] for r in results if not r['reproduced']],
               originalsUnchanged=not changed, originalChanges=changed[:50],
               protectedFiles=len(protected), readOnlyRestored=True, controllerAccess=False)
with (G / 'replay_run_01.json').open('x', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(json.dumps({k: summary[k] for k in ('selected', 'reproduced', 'reproducedWithContent', 'exitOnly',
                                          'notReproduced', 'originalsUnchanged', 'protectedFiles')}))
raise SystemExit(0 if not summary['notReproduced'] and not changed else 1)

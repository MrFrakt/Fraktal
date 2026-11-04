"""WP6.3 sealed capture replays, run 02: swap a copy in at the original path.

Run 01 copied only each script's folder elsewhere. Scripts read absolute paths
stored in their inputs, read sibling session folders and write outputs into
siblings, so most could not run (all recorded in run 01's outputs). Here the
whole session root is swapped instead:

1. journal, then rename ``C:/work/<root>`` to ``<root>.wp63-original``;
2. copy it back to the original path (ACD/BAK excluded) with a marker file;
3. delete from the COPY only the files the recorded run wrote (mtime inside
   its recorded start/end window), then run the recorded command unchanged;
4. keep the produced files, remove the marked copy, rename the original back.

Originals are read-only throughout and fingerprinted before and after. Nothing
original is deleted; only marked copies are removed. Every phase is journaled,
so an interruption is recovered by renaming ``*.wp63-original`` back.
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
IGNORE = shutil.ignore_patterns('*.ACD', '*.acd', '*.BAK', '*.bak', '*.Sem', '*.sem')
MARKER = '.wp63-replay-copy'
SUFFIX = '.wp63-original'
VOLATILE = re.compile(r'(?i)(seconds|utc|elapsedms|durationms|elapsed|duration)$')
EXCLUDED = {
    'capacity_profile_replay_01': 'capacity forecast over the shared observations registry, which '
    'gained later calibrations; the forecast rule refuses a target below the latest calibration. '
    'Not an oracle capture replay.'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def epoch_ns(text):
    return int(datetime.datetime.fromisoformat(text).timestamp() * 1e9)


def root_of(path):
    match = re.match(r'(C:/work/[^/]+)', path)
    return match.group(1) if match else None


def fingerprint(roots):
    result = {}
    for root in sorted(roots):
        for base, unused, names in os.walk(root):
            for name in names:
                p = os.path.join(base, name)
                s = os.stat(p)
                result[p.replace('\\', '/')] = [s.st_size, s.st_mtime_ns]
    return result


def writable(path):
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def remove_copy(root):
    assert (Path(root) / MARKER).is_file() and Path(root + SUFFIX).is_dir(), 'refusing to remove a non-copy'
    shutil.rmtree(root, onexc=lambda f, p, e: (writable(p), f(p)))


def load(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.name.endswith('.gz') else data)


def differences(a, b, at='', out=None, limit=60):
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


def journal(entry):
    with (G / 'swap_journal_02.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(utc=now(), **entry)) + '\n')


selected = [r for r in INVENTORY if r['kind'] == 'python' and r['label'] not in EXCLUDED]
excluded = [dict(exitRecord=r['exitRecord'], reason=EXCLUDED.get(
    r['label'], 'Dart wire-timing benchmark; measures latency, not oracle decoding'))
    for r in INVENTORY if r not in selected]
roots = set()
for r in selected:
    for path in [r['script'], *r['command'], *r['embeddedAbsolutePaths']]:
        if path and root_of(path) and os.path.isdir(root_of(path)):
            roots.add(root_of(path))
assert not any(os.path.exists(root + SUFFIX) for root in roots), 'a previous swap was not restored'
WORK.mkdir(parents=True, exist_ok=False)
before = fingerprint(roots)
protected = [p for p in before if os.stat(p).st_mode & stat.S_IWRITE]
with (G / 'protected_originals_02.json').open('x', encoding='utf-8') as f:
    json.dump(dict(utc=now(), roots=sorted(roots), files=protected), f, indent=1)
results = []
try:
    for p in protected:
        os.chmod(p, stat.S_IREAD)
    for number, r in enumerate(selected, 1):
        slug = f"{number:02d}_{r['label']}"
        root = root_of(r['script'])
        exit_record = json.loads((E / r['exitRecord']).read_text(encoding='utf-8'))
        # From the exact start: an input a preceding step wrote just before is kept.
        window = (epoch_ns(exit_record['startUtc']),
                  epoch_ns(exit_record['endUtc']) + 5_000_000_000)
        keep = WORK / slug
        keep.mkdir()
        journal(dict(slug=slug, phase='rename-original', root=root))
        os.rename(root, root + SUFFIX)
        deleted, attempts, produced, started = [], [], [], now()
        try:
            # Marker first: even a partial copy is recognisably ours.
            os.makedirs(root)
            (Path(root) / MARKER).write_text(slug, encoding='utf-8')
            shutil.copytree(root + SUFFIX, root, ignore=IGNORE, dirs_exist_ok=True)
            journal(dict(slug=slug, phase='copy-placed', root=root))
            for base, unused, names in os.walk(root):
                for name in names:
                    p = os.path.join(base, name)
                    writable(p)
                    if name != MARKER and window[0] <= os.stat(p).st_mtime_ns <= window[1]:
                        deleted.append(os.path.relpath(p, root).replace('\\', '/'))
                        os.remove(p)
            listing = {os.path.join(b, n): os.stat(os.path.join(b, n)).st_mtime_ns
                       for b, unused, ns in os.walk(root) for n in ns}
            command = [sys.executable, *r['command'][1:]]
            log = G / f'{slug}_run_02.log'
            with log.open('x', encoding='utf-8') as out:
                proc = subprocess.run(command, cwd=R, stdout=out, stderr=subprocess.STDOUT,
                                      text=True, timeout=3600)
            attempts.append(dict(exitCode=proc.returncode, log=log.name))
            for b, unused, ns in os.walk(root):
                for n in ns:
                    p = os.path.join(b, n)
                    if n != MARKER and listing.get(p) != os.stat(p).st_mtime_ns:
                        relative = os.path.relpath(p, root).replace('\\', '/')
                        produced.append(relative)
                        target = keep / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(p, target)
        finally:
            if os.path.isdir(root) and (Path(root) / MARKER).is_file():
                remove_copy(root)
                journal(dict(slug=slug, phase='copy-removed', root=root))
            if not os.path.exists(root):
                os.rename(root + SUFFIX, root)
                journal(dict(slug=slug, phase='original-restored', root=root))
        sealed_dir = (E / r['exitRecord']).parent
        compared = []
        for relative in produced:
            name = Path(relative).name
            twin = sealed_dir / name
            if name.endswith(('.json', '.json.gz')) and twin.is_file():
                superset = None
                try:
                    sealed, current = load(twin), load(keep / relative)
                    diff = differences(sealed, current)
                    if diff and isinstance(sealed, dict) and isinstance(current, dict) \
                            and isinstance(sealed.get('rows'), list) and isinstance(current.get('rows'), list):
                        # Glob-scoped replays grow with the evidence tree: are the sealed rows all still there?
                        superset = all(row in current['rows'] for row in sealed['rows'])
                except ValueError as error:
                    diff = [f'unreadable: {error}']
                volatile = [d for d in diff if VOLATILE.search(d.rsplit('/', 1)[-1])]
                compared.append(dict(file=relative, equal=not diff, volatileOnly=bool(diff) and diff == volatile,
                                     sealedRowsSubset=superset, differences=diff))
        final = attempts[-1]['exitCode'] if attempts else None
        content_ok = all(c['equal'] or c['volatileOnly'] for c in compared)
        results.append(dict(number=number, slug=slug, exitRecord=r['exitRecord'], recordedExit=r['exitCode'],
                            replayExit=final, attempts=attempts, deletedFromCopy=deleted, produced=produced,
                            compared=compared, contentCompared=bool(compared), startedUtc=started,
                            endedUtc=now(), reproduced=final == r['exitCode'] and content_ok))
        print(json.dumps(dict(slug=slug, recorded=r['exitCode'], replay=final, compared=len(compared),
                              reproduced=results[-1]['reproduced'])), flush=True)
finally:
    for p in protected:
        if os.path.exists(p):
            writable(p)
after = fingerprint(roots)
changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
summary = dict(schema='fraktal.ab.s6-wp63-replay-run', schemaVersion=2, utc=now(), selected=len(selected),
               excluded=excluded, results=results,
               reproduced=sum(r['reproduced'] for r in results),
               reproducedWithContent=sum(r['reproduced'] and r['contentCompared'] for r in results),
               exitOnly=[r['slug'] for r in results if r['reproduced'] and not r['contentCompared']],
               volatileDifferencesOnly=[r['slug'] for r in results if r['reproduced'] and any(
                   c['volatileOnly'] for c in r['compared'])],
               notReproduced=[r['slug'] for r in results if not r['reproduced']],
               originalsUnchanged=not changed, originalChanges=changed[:50],
               swapsRestored=not any(os.path.exists(root + SUFFIX) for root in roots),
               protectedFiles=len(protected), controllerAccess=False)
with (G / 'replay_run_02.json').open('x', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(json.dumps({k: summary[k] for k in ('selected', 'reproduced', 'reproducedWithContent', 'exitOnly',
                                          'volatileDifferencesOnly', 'notReproduced', 'originalsUnchanged',
                                          'swapsRestored')}))
raise SystemExit(0 if not summary['notReproduced'] and not changed and summary['swapsRestored'] else 1)

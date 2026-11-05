"""One-line mutants of the HostEvents delivery and the V6.11 projection, each killed by a test.

As for the adapter's earlier mutation run: each mutant is written to its file,
its selected tests run, the original bytes are restored and their SHA-256
asserted. A mutant is killed only when its tests ran and failed. The unmutated
sources first pass every selected test.
"""
from pathlib import Path
import datetime, hashlib, json, re, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
HMI = R / 'FraktalCore/HMI'
G = HMI / 'gateway'
DART = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
FLUTTER = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat'
EVENTS = G / 'lib/src/host_adapter/host_events.dart'
READER = HMI / 'packages/fraktal_opcua_client/lib/src/cip_host_service.dart'
PUBLICATION = HMI / 'packages/fraktal_opcua_client/lib/src/cip_publication.dart'
CAP = 'the sealed session 03 capture '
REF = 'the batch refuses what it cannot vouch for '
DEL = 'delivery writes the engineering cursor and sink bytes '

MUTANTS = [
    ('the ring slot off by one', EVENTS, 'final slot = (head - count + offset) % cap + 1,',
     'final slot = (head - count + offset) % cap,', 'gateway', [CAP + 'the canonical ring decodes to the legacy batch read natively']),
    ('sequence continuity unchecked', EVENTS, '    if (sequence != newest - count + offset + 1 ||\n',
     '    if (false ||\n', 'gateway', [REF + 'a discontinuous sequence']),
    ('a parent beyond its count accepted', EVENTS,
     'named.take(parents).any((n) => n.isEmpty) || named.skip(parents).any((n) => n.isNotEmpty)',
     'named.take(parents).any((n) => n.isEmpty)', 'gateway', [REF + 'a parent beyond its count']),
    ('an event acknowledged without its commit', EVENTS,
     "      seen = event['Sequence'] as int;\n      _commit(epoch, seen);\n",
     "      seen = event['Sequence'] as int;\n", 'gateway',
     [DEL + 'a repeated batch delivers nothing new; a newer one only its new events']),
    ('sink lines not ended as Python ends them', EVENTS,
     "${Platform.isWindows ? '\\r\\n' : '\\n'}", "\\n", 'gateway',
     [DEL + 'first delivery: the overwritten interval, then every held event']),
    ('an epoch loss record misnamed', EVENTS, "'reason': 'publisherEpochChanged',", "'reason': 'epochChanged',",
     'gateway', [DEL + 'a publisher epoch change is a loss record']),
    ('a torn read kept', READER, '    if (await revision() != before) return null;\n', '', 'gateway',
     [CAP + 'a read is kept only between two equal even revisions']),
    ('the ring owner row not admitted', PUBLICATION, "          if (r['Service'] == 4) r['CanonicalRoot'] as String\n",
     "          if (r['Service'] == 99) r['CanonicalRoot'] as String\n", 'hmi',
     ['the projection accepts V6.11 and publishes the host-event ring']),
]
SUITES = {'gateway': (G, [DART, 'test', 'test/host_events_test.dart', '-r', 'expanded']),
          'hmi': (HMI, [FLUTTER, 'test', 'test/cip_v611_capture_test.dart', '-r', 'expanded'])}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(suite, names):
    cwd, base = SUITES[suite]
    pattern = '^(' + '|'.join(re.escape(n) for n in names) + ')$'
    done = subprocess.run([*base, '--name', pattern], cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')
    output = done.stdout + done.stderr
    ran = all(f': {n}' in output or f' {n}' in output for n in names)
    verdict = ('passed' if done.returncode == 0 and 'All tests passed' in output and ran
               else 'failed' if done.returncode == 1 and 'Some tests failed' in output and ran
               else 'invalid')
    return done.returncode, verdict, output.strip().splitlines()[-3:]


originals = {p: p.read_bytes() for p in (EVENTS, READER, PUBLICATION)}
hashes = {p: digest(p) for p in originals}
for label, path, old, new, _, _ in MUTANTS:
    assert originals[path].decode('utf-8').count(old) == 1, label
report = dict(started=datetime.datetime.now(datetime.timezone.utc).isoformat(), baseline={}, mutants=[],
              sources={str(p.relative_to(R)).replace('\\', '/'): h for p, h in hashes.items()})
for suite in SUITES:
    names = sorted({n for *_, s, ns in MUTANTS if s == suite for n in ns})
    report['baseline'][suite] = dict(zip(('exit', 'verdict', 'tail'), run(suite, names)), tests=names)
    print(json.dumps(dict(baseline=suite, verdict=report['baseline'][suite]['verdict'])), flush=True)
if all(b['verdict'] == 'passed' for b in report['baseline'].values()):
    for label, path, old, new, suite, names in MUTANTS:
        try:
            path.write_bytes(originals[path].decode('utf-8').replace(old, new).encode('utf-8'))
            code, verdict, tail = run(suite, names)
        finally:
            path.write_bytes(originals[path])
        assert digest(path) == hashes[path], label
        report['mutants'].append(dict(mutant=label, file=path.name, tests=names, exit=code, verdict=verdict,
                                      killed=verdict == 'failed', tail=tail))
        print(json.dumps(dict(mutant=label, verdict=verdict)), flush=True)
for p in originals:
    assert digest(p) == hashes[p]
report['passed'] = (all(b['verdict'] == 'passed' for b in report['baseline'].values())
                    and len(report['mutants']) == len(MUTANTS) and all(m['killed'] for m in report['mutants']))
report['finished'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(dict(passed=report['passed'], mutants=len(report['mutants']),
                      killed=sum(m['killed'] for m in report['mutants']))))
raise SystemExit(0 if report['passed'] else 1)

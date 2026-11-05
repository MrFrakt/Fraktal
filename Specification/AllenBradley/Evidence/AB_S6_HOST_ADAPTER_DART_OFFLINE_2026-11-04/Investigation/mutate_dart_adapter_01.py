"""One-line mutants of the Dart host adapter and its CIP port, each killed by a test.

Dart cannot load a mutated library in memory, so each mutant is written to
its source file, the selected bench tests run, and the original bytes are
restored and their SHA-256 asserted before the next mutant. The unmutated
sources first pass every selected test. A mutant survives when its tests
pass; the run fails if any does. Writes a JSON report to the path given.
"""
from pathlib import Path
import datetime, hashlib, json, re, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
G = R / 'FraktalCore/HMI/gateway'
DART = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
SERVICE = G / 'lib/src/host_adapter/root_service.dart'
PORT = R / 'FraktalCore/HMI/packages/fraktal_opcua_client/lib/src/cip_host_service.dart'
SETS, LIVE, CIP = 'configuration sets ', 'live documents ', 'the CIP port '

MUTANTS = [
    ('a missing set answered as found', SERVICE,
     '    } on PathNotFoundException {\n      return _status(job, CipHost.refused);',
     '    } on PathNotFoundException {\n      return _status(job, CipHost.ok);',
     SETS + 'a missing set and a full store refuse'),
    ('a full store not refused', SERVICE,
     'return await _status(job, full ? CipHost.refused : CipHost.ok);',
     'return await _status(job, CipHost.ok);',
     SETS + 'a missing set and a full store refuse'),
    ('an import commit not kept', SERVICE,
     '      committed = document;\n', '',
     SETS + 'an import in pieces is stored on commit'),
    ('a restore that hides its losses', SERVICE,
     '        losses.add((key, error.message));\n', '',
     LIVE + 'a lost document is restored as a loss'),
    ('a boolean rendered as a number', SERVICE,
     "? ((values[c.ordinal - 1] as int) != 0 ? 'TRUE' : 'FALSE')",
     "? '${values[c.ordinal - 1]}'",
     SETS + "save, list, load, export and delete go through the adapter's store"),
    ('invalid value text coerced', SERVICE,
     '        types.add(-1);\n', '        types.add(kind);\n',
     SETS + 'a stored value the controller cannot parse is sent as invalid, never coerced'),
    ('the catalog never published', SERVICE,
     '      if (headers.isEmpty) return _status(job, CipHost.ok);',
     '      return _status(job, CipHost.ok);',
     SETS + "save, list, load, export and delete go through the adapter's store"),
    ('a keep that never writes', SERVICE,
     '        medium!.write(key, document);\n', '',
     LIVE + 'a download is restored from the medium and then kept'),
    ('the commit written before the payload', PORT,
     "        (row['RequestSymbol'] as String, payload),\n        (row['CommitSymbol'] as String, commit)\n",
     "        (row['CommitSymbol'] as String, commit),\n        (row['RequestSymbol'] as String, payload)\n",
     CIP + 'writes the payload, then its commit, and returns the acknowledgement'),
    ('any reply taken as the acknowledgement', PORT,
     "      if (((answer['AckSequence'] as int) & 0xffffffff) == sequence) return answer;",
     '      return answer;',
     CIP + 'an unacknowledged request is never resent'),
    ('a refused write carried on', PORT,
     '        if (written.status != 0)\n',
     '        if (written.status != 0 && symbol.isEmpty)\n',
     CIP + 'a refused write is never resent, and the next request reopens the connection'),
    ('a capability read with the wrong key column', PORT,
     "await keyText(r['WriteKeyKey'] as int),",
     "await keyText(r['LabelKey'] as int),",
     CIP + 'reads the reply and the facts exactly as the controller holds them'),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(names):
    """Exit code, verdict and tail. Only a run whose tests all ran counts as a verdict."""
    pattern = '^(' + '|'.join(re.escape(n) for n in names) + ')$'
    args = [DART, 'test', 'test/host_adapter_bench_test.dart', '-r', 'expanded', '--name', pattern]
    done = subprocess.run(args, cwd=G, capture_output=True, text=True, encoding='utf-8', errors='replace')
    output = done.stdout + done.stderr
    ran = all(f': {n}' in output for n in names)
    verdict = ('passed' if done.returncode == 0 and 'All tests passed' in output and ran
               else 'failed' if done.returncode == 1 and 'Some tests failed' in output and ran
               else 'invalid')
    return done.returncode, verdict, output.strip().splitlines()[-3:]


originals = {path: path.read_bytes() for path in (SERVICE, PORT)}
hashes = {path: digest(path) for path in originals}
for label, path, old, new, _ in MUTANTS:
    assert originals[path].decode('utf-8').count(old) == 1, label
selected = sorted({test for *_, test in MUTANTS})
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
base_exit, base_verdict, base_tail = run(selected)
report = dict(started=started, baseline=dict(exit=base_exit, verdict=base_verdict, tail=base_tail, tests=selected),
              sources={str(p.relative_to(R)).replace('\\', '/'): h for p, h in hashes.items()}, mutants=[])
print(json.dumps(dict(baseline=base_verdict)), flush=True)
if base_verdict == 'passed':
    for label, path, old, new, test in MUTANTS:
        text = originals[path].decode('utf-8')
        try:
            path.write_bytes(text.replace(old, new).encode('utf-8'))
            code, verdict, tail = run([test])
        finally:
            path.write_bytes(originals[path])
        assert digest(path) == hashes[path], label
        report['mutants'].append(dict(mutant=label, file=path.name, test=test, exit=code, verdict=verdict,
                                      killed=verdict == 'failed', tail=tail))
        print(json.dumps(dict(mutant=label, verdict=verdict)), flush=True)
for path in originals:
    assert digest(path) == hashes[path]
report['passed'] = base_verdict == 'passed' and all(m['killed'] for m in report['mutants']) \
    and len(report['mutants']) == len(MUTANTS)
report['finished'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(dict(passed=report['passed'], baseline=base_verdict, mutants=len(report['mutants']),
                      killed=sum(m['killed'] for m in report['mutants']))))
raise SystemExit(0 if report['passed'] else 1)

"""WP6.3: every migration-oracle test, by name, on the pre-collapse tree.

The set is derived, not listed: every test module that imports an MO-class
module in census classification 03, which includes the one MO-class test
module. Tool sources are hashed before and after so the result binds them.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
G = Path(__file__).resolve().parents[1] / 'Gates'
CENSUS = R / 'Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json'


def sources():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(T.glob('*.py'))}


census = json.loads(CENSUS.read_text(encoding='utf-8'))
rows = {x['module']: x for x in census['consumers'] + census['unaffected']}
oracles = {m for m, x in rows.items() if x.get('effectiveClassification') == 'MO'}
tests = sorted(m for m, x in rows.items() if m.startswith('test_')
               and {i['module'] for i in x['imports']} & oracles)
assert all((T / f'{m}.py').is_file() for m in tests), 'a census test module is missing'
before, started = sources(), datetime.datetime.now(datetime.timezone.utc).isoformat()
with (G / 'mo_tests_01.log').open('x', encoding='utf-8') as log:
    proc = subprocess.run([sys.executable, '-m', 'unittest', '-v', *tests], cwd=T,
                          stdout=log, stderr=subprocess.STDOUT, text=True)
after = sources()
text = (G / 'mo_tests_01.log').read_text(encoding='utf-8', errors='replace')
ran = next((line for line in text.splitlines() if line.startswith('Ran ')), None)
result = dict(schema='fraktal.ab.s6-wp63-mo-tests', schemaVersion=1, census=CENSUS.relative_to(R).as_posix(),
              oracleModules=sorted(oracles), testModules=tests, exitCode=proc.returncode, ran=ran,
              startedUtc=started, endedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              sourcesUnchangedDuringRun=before == after, sourceHashes=before)
with (G / 'mo_tests_01.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(dict(testModules=len(tests), exitCode=proc.returncode, ran=ran,
                      sourcesUnchanged=before == after)))
raise SystemExit(proc.returncode or (before != after))

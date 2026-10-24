"""Frame sources versus the reads recorded in every accepted native S3h pair."""
import glob, gzip, json, os, re, sys
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
tools, evidence = sys.argv[1:3]
sys.path.insert(0, tools)
import fraktal_ab_canonical_observation as observation
import fraktal_ab_genealogy_s3h_demo as demo
app = demo.application()
expected = set(observation.legacy_sources(app))
dims = {n: c for n, (k, c) in observation._declared(app).items()}
files = sorted(f for f in glob.glob(evidence + '/candidate_regressions_01_*_[0-9][0-9].json.gz'))
rows = []
for path in files:
    d = json.load(gzip.open(path, 'rt'))
    if not d.get('passed'): continue
    pair = d['pair']
    canonical = {r['tag'] for r in pair['capture']['records']}
    legacy = [r['tag'] for r in pair['rawReads'] if r['tag'] not in canonical]
    bases = {re.sub(r'\[\d+\]$', '', t) for t in legacy}
    indices = [int(m.group(1)) for t in legacy for m in [re.search(r'\[(\d+)\]$', t)] if m]
    rows.append(dict(file=os.path.basename(path), reads=len(legacy), equal=bases == expected,
                     missing=sorted(expected - bases), extra=sorted(bases - expected),
                     indicesWithinFrame=all(i < dims[re.sub(r'\[\d+\]$', '', t)] for t in legacy
                                            for m in [re.search(r'\[(\d+)\]$', t)] if m for i in [int(m.group(1))])))
summary = dict(captures=len(rows), allEqual=all(r['equal'] and r['indicesWithinFrame'] for r in rows),
               frameLegacySources=len(expected), readsPerCapture=sorted({r['reads'] for r in rows}))
print(json.dumps(summary))
print(json.dumps([r for r in rows if not r['equal']][:3]))

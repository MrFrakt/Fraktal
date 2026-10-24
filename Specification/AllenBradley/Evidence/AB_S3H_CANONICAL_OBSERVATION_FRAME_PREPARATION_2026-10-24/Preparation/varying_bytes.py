"""Which record bytes ever differ across accepted S3h captures (empirical)."""
import glob, gzip, json, sys
from collections import defaultdict
root = sys.argv[1]
files = sorted(f for f in glob.glob(root + '/candidate_regressions_01_*_[0-9][0-9].json.gz') if 'window' not in f)
first = {}; varying = defaultdict(set); sizes = {}; n = 0
for f in files:
    d = json.load(gzip.open(f, 'rt'))
    if not d.get('passed') and 'pair' not in d: continue
    pair = d['pair']; n += 1
    recs = {r['tag']: bytes.fromhex(r['rawHex']) for r in pair['capture']['records']}
    for r in pair['rawReads']:
        if r['rawHex']: recs[r['tag']] = bytes.fromhex(r['rawHex'])
    for tag, raw in recs.items():
        sizes[tag] = len(raw)
        if tag not in first: first[tag] = raw; continue
        base = first[tag]
        for i, (a, b) in enumerate(zip(base, raw)):
            if a != b: varying[tag].add(i)
print('captures', n)
tot = 0; totv = 0
for tag in sorted(sizes, key=lambda t: -sizes[t]):
    v = varying[tag]; tot += sizes[tag]; totv += len(v)
    # contiguous 4000-byte windows touched
    blocks = len({i // 3988 for i in v})
    print(f'{tag:40s} {sizes[tag]:7d} varying={len(v):6d} blocks3988={blocks}')
print('total', tot, 'varying', totv)

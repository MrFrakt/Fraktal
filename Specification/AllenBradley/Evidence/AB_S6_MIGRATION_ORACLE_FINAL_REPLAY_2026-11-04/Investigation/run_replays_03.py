"""WP6.3 run 03: are the five WriteRevision replays different ONLY by the S5 fix?

Run 02 stopped each of these replays at its first unequal Access pair, and every
inspected difference was ConfigPage ``WriteRevision``, the field the recorded S5
write-revision correction changed in the oracle (commit 8cd2060f1, one line in
fraktal_ab_s3f_equivalence). Here, in the swapped COPY only, each script's strict
reference assertion is replaced by one that tolerates differences solely on
paths ending ``/WriteRevision`` with equal types, records each one, restores the
sealed value and continues. Any other difference still fails. A replay whose
output then equals its sealed output differs only by that documented field.

All isolation is run 02's: swap-in-place, marker-checked copy removal, read-only
originals, fingerprints and a journal. Run 02's script is left unchanged; its
source is loaded, relabelled ``_03`` and given one patch call by anchored edits.
"""
import json
import os
from pathlib import Path
import stat
import sys

I = Path(__file__).resolve().parent
TARGETS = {
    'AB_PRESS_S3_EXIT_RUNTIME_2026-10-25/Session/pair_replay_01_exit.json',
    'AB_S3K_CANONICAL_ATTEMPT_2026-10-25/Download/partial_pair_replay_01_exit.json',
    'AB_S3K_CANONICAL_ATTEMPT_2026-10-25/Download/partial_pair_replay_02_exit.json',
    'AB_S3K_CANONICAL_REVISION_RETRY_RUNTIME_2026-10-25/Runtime/pair_replay_01_exit.json',
    'AB_S3K_CANONICAL_RUNTIME_2026-10-25/Runtime/pair_replay_01_exit.json'}
STRICT = ("assert expected['values']==pair['projection']['values'] and "
          "expected['types']==pair['projection']['types'],path.name+' independent reference differs'")
HELPER = '''import json as __wp63_json, os as __wp63_os
def __wp63_tolerate(expected, pair, path):
    sealed = pair['projection']
    assert expected['types'] == sealed['types'], path.name + ' independent reference types differ'
    keys = set(expected['values']) | set(sealed['values'])
    diff = sorted(k for k in keys if expected['values'].get(k, '<absent>') != sealed['values'].get(k, '<absent>'))
    assert all(k.endswith('/WriteRevision') for k in diff), path.name + ' differs beyond WriteRevision'
    with open(__wp63_os.environ['WP63_TOLERATED'], 'a', encoding='utf-8') as out:
        out.write(__wp63_json.dumps(dict(file=path.name, paths=len(diff),
                  today=sorted({expected['values'][k] for k in diff}),
                  sealed=sorted({sealed['values'][k] for k in diff}))) + '\\n')
    for k in diff:
        expected['values'][k] = sealed['values'][k]
'''


def patch(script):
    # The copy inherits the originals' read-only attribute until run 02 clears it.
    os.chmod(script, stat.S_IWRITE | stat.S_IREAD)
    text = script.read_text(encoding='utf-8')
    assert '__future__' not in text and text.count(STRICT) == 1, script
    script.write_text(HELPER + text.replace(STRICT, '__wp63_tolerate(expected, pair, path)'), encoding='utf-8')


inventory = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
selected = [r for r in inventory['replays'] if r['exitRecord'] in TARGETS]
assert len(selected) == len(TARGETS)
narrowed = I / 'replay_inventory_03_targets.json'
with narrowed.open('x', encoding='utf-8') as f:
    json.dump(dict(inventory, replays=selected), f, indent=2)
work = Path(sys.argv[2])
os.environ['WP63_TOLERATED'] = str(work / 'tolerated.jsonl')
base = (I / 'run_replays_02.py').read_text(encoding='utf-8')
edits = [("'swap_journal_02.jsonl'", "'swap_journal_03.jsonl'"),
         ("'protected_originals_02.json'", "'protected_originals_03.json'"),
         ("'replay_run_02.json'", "'replay_run_03.json'"),
         ("f'{slug}_run_02.log'", "f'{slug}_run_03.log'"),
         ("            journal(dict(slug=slug, phase='copy-placed', root=root))\n",
          "            journal(dict(slug=slug, phase='copy-placed', root=root))\n"
          "            WP63_PATCH_HOOK(Path(r['script']))\n")]
for old, new in edits:
    assert base.count(old) == 1, old
    base = base.replace(old, new)
sys.argv = [str(I / 'run_replays_03.py'), str(narrowed), str(work)]
namespace = dict(__name__='__main__', __file__=str(I / 'run_replays_02.py'), WP63_PATCH_HOOK=patch)
exec(compile(base, str(I / 'run_replays_02.py') + ' (run 03 edits)', 'exec'), namespace)

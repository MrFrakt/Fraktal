"""Prepare an append-only tier/queue outcome sealer without changing session inputs."""
from pathlib import Path
import hashlib
import json

W = Path(__file__).parent
base = Path('C:/work/fraktal-ab-s4b-timing-20261027/offline_01/seal_runtime_01.py')
text = base.read_text(encoding='utf-8')

def change(old, new, count=1):
    global text
    assert text.count(old) == count, (old, text.count(old), count)
    text = text.replace(old, new)

change('actual desktop timing outcome', 'actual tier/queue outcome')
change('call_65010f20595041d78cea54b482b0f09f:0', 'call_a6801bdef7184d1c95927b1b41c26fde:0', 2)
change('AB_S4B_DESKTOP_TIMING_', 'AB_S4B_TIER_QUEUE_', 3)
change('fed4a614842da063744c56dfa37c9bf029f84b716ba08265faa18f3a6ab4c03f',
       '6acef0cd97d1c7028cb9098928c3b70da0f5cff2b0748d041cf9f2f9b4eea1ca')
change('S4b desktop phase-timing qualification', 'S4b tier/queue qualification')
change('Approve guarded S4b desktop timing session', 'Approve guarded S4b tier/queue retry')
change('fraktal.ab.s4b-desktop-timing-runtime', 'fraktal.ab.s4b-tier-queue-runtime')
change('authorize_timing_session_01', 'authorize_tier_queue_session_01', 3)
change('The original response age bracket and\nage arithmetic remain in their original positions. No reads, snapshot values,\nproofs, retries, deadlines, freshness limits or write policy change.',
       'The response-processing clock now starts at worker message receipt, so it\nincludes the serialized worker queue within the existing server-processing\nbracket. The source/leaf age boundaries and frontend arithmetic are unchanged.\nPrimitive-array scheduling now uses the manifest-published logical leaf set\nand its consumed members: excluded arrays are skipped and all-slow consumed\narrays follow the slow tier. Explicit targeted reads retain their original\nproof. Snapshot values/types, row proofs, retries, deadlines, Good/expiry limits\nand write policy remain unchanged.\n\nThe archived capture replay reduces reads from **990 to 810** and guarded groups\nfrom **297 to 237**, removing **60** excluded profiler-array reads. All **976**\nconsumed values/types remain exactly equal to the pre-change replay and the\nindependent oracle. Those are replay counts, not native latency measurements.')
change('The preparation binds **660 HMI tests passed /12 skipped**, 40 trace-enabled\nfocused tests, analyzer, Windows build and enforced lockfile, using Flutter\n**3.47.5 /Dart 3.13.4** and the identical 318-input mirror. Three existing HMI\nsource/test files add diagnostics.',
       'The preparation binds **665 HMI tests passed /12 skipped**, 53 trace-enabled\nfocused tests, analyzer, Windows build and enforced lockfile, using Flutter\n**3.47.5 /Dart 3.13.4** and the identical 319-input mirror. Three existing HMI\nsource/test files change and one new array-tier test file is added. The five\nnew array cases pass; the archived old implementation fails four of them.\nThe freshness counterexample covers queue-plus-read processing without changing\nsource timestamps or quality limits.')
change("schemaVersion=1,", "schemaVersion=1,tierQueueCorrection=q['tierQueueCorrection'],")
with (W/'seal_runtime_01.py').open('x', encoding='utf-8', newline='') as f:
    f.write(text)
print(json.dumps(dict(prepared=True, sourceSha256=hashlib.sha256(base.read_bytes()).hexdigest(),
    outputSha256=hashlib.sha256((W/'seal_runtime_01.py').read_bytes()).hexdigest())))

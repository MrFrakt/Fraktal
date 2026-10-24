"""Replay native boundary bytes and summarize measured task timing, offline."""
from pathlib import Path
import gzip,hashlib,json,statistics,sys
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_canonical_reader as reader
import fraktal_ab_genealogy_s3g_demo as demo
import fraktal_ab_s3g_native_checks as checks
fixture=json.loads((R/'candidate_regressions_01.json').read_text());held=fixture['s3gNativeChecks']
decoded=reader.decode_record(bytes.fromhex(held['rawHex']),held['symbol']['handle'],held['templates'])
assert decoded==held['result']
native=checks.verify_result(demo.application(),decoded)
native.update(controllerAccess=False,rawSha256=hashlib.sha256(bytes.fromhex(held['rawHex'])).hexdigest(),
    rawPayloadBytes=len(bytes.fromhex(held['rawHex'])),independentReference=True)
with (R/'native_boundary_replay_01.json').open('x') as f:json.dump(native,f,indent=2)
timing={}
for name,prefix,last,maximum,overlap in (
    ('candidate','FRK_Press_CanonicalTiming.','LastScanUs','MaxScanUs','OverlapCount'),
    ('baseline','FRK_Press_HealthProbe.','TaskLastScanUs','TaskMaxScanUs','TaskOverlapCount')):
    evidence=json.loads((R/(name+'_timing_01.json')).read_text());samples=evidence['samples']
    timing[name]=dict(samples=len(samples),medianUs=statistics.median(s['values'][prefix+last] for s in samples),
        minimumUs=min(s['values'][prefix+last] for s in samples),maximumLastUs=max(s['values'][prefix+last] for s in samples),
        cumulativeMaximumUs=max(s['values'][prefix+maximum] for s in samples),overlaps=max(s['values'][prefix+overlap] for s in samples))
    assert len(samples)==20 and timing[name]['overlaps']==0
with (R/'timing_summary_01.json').open('x') as f:json.dump(dict(passed=True,unit='microseconds',timing=timing),f,indent=2)
source=ROOT/'Specification/AllenBradley/Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21/Reference/genealogy_current.L5X.gz'
raw=gzip.decompress(source.read_bytes())
assert hashlib.sha256(raw).hexdigest()=='91bf67c9101eae863cf29c1a9df6413d7256ab056d985394587f0183aa525714'
with (R/'genealogy_reference.L5X').open('xb') as f:f.write(raw)
print(json.dumps(dict(passed=True,native=native,timing=timing)))

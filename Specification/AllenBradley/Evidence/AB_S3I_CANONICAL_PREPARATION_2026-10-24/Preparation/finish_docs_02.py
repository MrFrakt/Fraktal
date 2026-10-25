from pathlib import Path
import json,hashlib
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pin=(W/'canonical.sha256').read_text().strip()
capacity=json.loads((W/'capacity_review.json').read_text())
p=ROOT/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';s=p.read_text(encoding='utf-8')
old='S3i implementation/build/model gates in progress; native session separately gated'
new='S3i offline image A5FAFA46…7E36C42 prepared at 87% Capacity; [preparation](Evidence/AB_S3I_CANONICAL_PREPARATION_2026-10-24.md); native session approval required'
assert s.count(old)==1;p.write_bytes(s.replace(old,new).encode())

addition='''
## S3i offline preparation — 2026-10-24

The approved Line/shift scope is implemented in the opt-in stage 11 profile.
Sixteen frozen gaps and two missing Core Line fields are added; history has
eight physical V3 slots, 21 fields per occupied row and PLC count discovery.
The Line owner stores update time quality in versioned private LineStateV2;
old stage layouts and source hashes are unchanged. Durations, unsigned words,
Float32 factors and timestamps follow the approved finite target contract.

The prepared ACD is `A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42`.
Automatic Studio Capacity is 2,763,512 used / 382,216 available / 3,145,728
Blocks (87%), an 83,380 Block increase over accepted S3h with its frame.
Both v38 targets compile and read back equivalently. All 2,178 AB tests and
74 root tests pass; 88 accepted S3h pairs replay unchanged. Failed model,
compiler, test and read-back runs remain in the preparation payload.

Eight first-scan publication checks are prepared: empty/full/partial history,
unsigned/Float32 wrap, unchanged-marker caching, pending calendar/latched
targets, and exact LDT upper-bound acceptance/refusal. They temporarily set
only the two fixed Line owner records, restore both byte-for-byte in the same
scan and rebuild publication from the restored owners. They do not set the
clock or simulate the calendar producer. They have passed the ST model only;
native execution, actual calendar lifetime/closure coverage, scan measurement
and the wider S3 press/rendition gates remain unaccepted.

No controller operation was performed. The prepared session is inert until
current exact-image approval: MANUAL normalization when needed; fresh guarded
preflight/backup; Program/download/Run; eight first-scan checks; five-document
restore and 41 inherited candidate cases with read-only Line/trace/config
pairs; all-path sizes/scan measurement; genealogy rollback and five-document
restore/31 baseline cases; MANUAL cleanup/final checks. Fault clears, clock
changes, hard kills and vendor-state edits are excluded. See
[the preparation evidence](Evidence/AB_S3I_CANONICAL_PREPARATION_2026-10-24.md).
'''
for name in ('AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md'):
    p=ROOT/'Specification/AllenBradley'/name;s=p.read_text(encoding='utf-8')
    assert '## S3i offline preparation — 2026-10-24' not in s
    p.write_bytes((s.rstrip()+'\n'+addition).encode())

report=dict(passed=True,canonicalSha256=pin,sourceSha256=sha(W/'s3i_bench_05.L5X'),
    usedBlocks=capacity['UsedStandardBlocks'],availableBlocks=capacity['AvailableBlocks'],
    deltaUsedBlocks=capacity['DeltaUsedStandardBlocks'],controllerOperations=0,nativeAccepted=False,
    caseScope='Eight first-scan publication vectors, 41 inherited candidate and 31 baseline cases; calendar producer lifetime remains open')
with (W/'prepared_summary_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))

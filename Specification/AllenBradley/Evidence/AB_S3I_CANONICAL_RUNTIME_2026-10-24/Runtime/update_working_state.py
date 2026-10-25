from pathlib import Path
import json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text(encoding='utf-8'))
target=d['approvedRemainingSurfaceCorrection'];assert target['stageStatus']['S3i']=='offline-prepared-native-session-approval-required'
target['stageStatus']['S3i']='publication-native-pass-calendar-lifetime-open'
target['s3iPublicationRuntime']=dict(publicationAccepted=True,stageExitPassed=False,
    evidence='Evidence/AB_S3I_CANONICAL_RUNTIME_2026-10-24.md',
    preparedAcdSha256='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42',
    candidateChecks=41,nativePublicationVectors=8,baselineChecks=31,pairedReplays=88,idlePaths=3968,
    nativeRootBytes=134720,observationFrameBytes=173792,usedStandardBlocks=2763512,
    availableBlocks=382216,totalBlocks=3145728,observedLiveShiftHistoryCounts=[0],
    calendarProducerLifetimeAccepted=False,sessionApprovalConsumed=True)
assert not d['active'] and not target['runtimeAccepted']
p.write_bytes((json.dumps(d,indent=2,ensure_ascii=False)+'\n').encode())

p=AB/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';s=p.read_text(encoding='utf-8')
marker='**Latest, 2026-10-24: remaining-S3 inventory reconciled; contract review'
assert s.count(marker)==1
status='''**Latest, 2026-10-24: S3i publication passes on genealogy/Echo; calendar
lifetime remains open.** The approved A5FAFA46…7E36C42 image passed 41 candidate,
eight native publication vectors and 31 restored-baseline checks. All 88
same-frame pairs replay independently at 3,360–3,968 typed paths. Capacity is
87% (2,763,512 / 3,145,728 Blocks); median LastScan is 875.5 µs, cumulative
max 8,405 µs, zero overlaps. Genealogy is restored, MANUAL/idle/logged out with
five saved/live documents equal. Every live pair had zero occupied shift
history rows: synthetic publication vectors do not close natural calendar,
target-lifetime or retained Program/Run gates. Prepare those next, before S3i
exit or S3j. Read [runtime evidence](Evidence/AB_S3I_CANONICAL_RUNTIME_2026-10-24.md).
The read-only observer's missing stage-11 result label was corrected before
controller changes; all 2,178 AB /74 root tests pass. The session approval is
consumed. No commit or push; V2 remains inactive.

**Earlier, 2026-10-24: remaining-S3 inventory reconciled; contract review'''
s=s.replace(marker,status,1)
old='S3i offline image A5FAFA46…7E36C42 prepared at 87% Capacity; [preparation](Evidence/AB_S3I_CANONICAL_PREPARATION_2026-10-24.md); native session approval required'
new='[S3i publication runtime](Evidence/AB_S3I_CANONICAL_RUNTIME_2026-10-24.md) passed 41+8+31 checks, 88 pairs, 87% Capacity; natural calendar/populated-live-history/target-lifetime/Program-Run gates remain open'
assert s.count(old)==1;s=s.replace(old,new)
p.write_bytes(s.encode())
addition='''
## S3i publication runtime — 2026-10-24

The approved A5FAFA46…7E36C42 session passed 41 candidate checks, eight native
publication vectors and 31 restored-baseline checks. All 88 paired captures
replay independently at 3,360–3,968 typed paths (2–29 attempts under unchanged
100-poll/five-second bounds). Root/frame sizes are 134,720 / 173,792 bytes;
Capacity remains 87%. Native LastScan median is 875.5 µs, cumulative max
8,405 µs, zero overlaps. Genealogy is restored in Run, not faulted, MANUAL/idle,
logged out, not restoring, original policy and five saved/live documents equal.
No new dumps, clock changes or fault clears; this session approval is consumed.

S3i exit is still open: every ordinary live pair had ShiftHistoryCount 0.
The eight first-scan vectors prove publication of synthetic populated rows,
not natural calendar closure/target lifetime or retained Program/Run behavior.
Prepare that follow-up using public operations and fresh published timestamps;
private clock tags stay inaccessible and no clock set is authorized. S3j must
wait for the S3i exit. Actual press ST/SFC/ladder and S4–S7 remain open.

The Python observer's missing stage-11 result label was repaired before any
controller change; its one-file read-only delta and both 170-source pin sets
are recorded. All 2,178 AB and 74 root tests pass. No PLC image, read/comparison
policy, write vector or bound was changed by that repair. See
[runtime evidence](Evidence/AB_S3I_CANONICAL_RUNTIME_2026-10-24.md).
'''
for name in ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md'):
    p=AB/name;s=p.read_text(encoding='utf-8');assert '## S3i publication runtime — 2026-10-24' not in s
    p.write_bytes((s.rstrip()+'\n'+addition).encode())
print('Working plan, handover, notes and inactive target updated; S3i exit remains open')

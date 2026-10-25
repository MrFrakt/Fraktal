from pathlib import Path
import json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
name='Evidence/AB_S3I_CANONICAL_LIFETIME_PREPARATION_2026-10-24.md'
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text(encoding='utf-8'))
target=d['approvedRemainingSurfaceCorrection']
assert target['stageStatus']['S3i']=='publication-native-pass-calendar-lifetime-open'
target['s3iLifetimePreparation']=dict(evidence=name,currentSessionApproved=False,plcImageChanged=False,
    preparedAcdSha256='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42',
    maxCalendarCommits=64,normalCalendarCommits=38,retainedProgramRunCycles=1,
    privateClockAccess=False,clockSet=False,abTests=2189,rootTests=74,nativeAccepted=False)
p.write_bytes((json.dumps(d,indent=2,ensure_ascii=False)+'\n').encode())
addition='''
## S3i calendar lifetime follow-up prepared — 2026-10-24

The next natural-calendar/retained-Program-Run fixture is ready offline for
unchanged ACD A5FAFA46…7E36C42 (measured 87% Capacity). It uses a fresh published
Line.LastUpdate, one twelve-hour interval ending three minutes later, target
40 → requested 99, queued original-calendar restoration, two real newest-first
history rows and exact before/after Line value/type equality across one
Program/Run cycle without downloading in that cycle. No private clock access
or clock set is added. Normal path: 38 public Line commits, ceiling 64 including
cleanup; operator-session and exact-target guards remain strict.

All 2,189 AB /74 root tests pass, as do eleven focused emitted-ST lifetime
tests, six negative authorization cases and the guarded helper build. The
170 inherited source bindings and PLC image are unchanged; two fixture/test
sources are added. All 88 prior native pairs replay unchanged. The required
v38 compiler/read-back and Capacity results transfer by exact image hash.

No controller access or change occurred in this preparation. Current owner
approval is still required for the fresh download, public calendar writes and
retained cycle; the earlier session approval is consumed. Proposed session
repeats the 41 candidate checks, adds calendar/retention proof, then rolls back
and restores five documents/31 baseline checks. Fault clears, clock changes,
power operations and hard kills remain excluded. S3i exit and S3j stay open.
See [preparation evidence](Evidence/AB_S3I_CANONICAL_LIFETIME_PREPARATION_2026-10-24.md).
'''
for filename in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
                 'AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md'):
    p=AB/filename;s=p.read_text(encoding='utf-8')
    assert '## S3i calendar lifetime follow-up prepared — 2026-10-24' not in s
    p.write_bytes((s.rstrip()+'\n'+addition).encode())
print('Working notes updated; S3i/native approval remain open')

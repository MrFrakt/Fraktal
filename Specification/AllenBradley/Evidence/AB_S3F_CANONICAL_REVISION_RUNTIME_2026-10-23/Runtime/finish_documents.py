from pathlib import Path
import datetime,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
v=json.loads((R/'runtime_verification_01.json').read_text());assert v['passed'] and v['s3fStageComplete'] and v['acceptedTotalRows']==74 and v['actualRecordedRows']==125
sha=lambda raw:hashlib.sha256(raw).hexdigest()
old=json.loads((R/'source_verification_01.json').read_text())['sha256'];current=json.loads((R/'source_verification_02.json').read_text())['sha256']
changed={p:dict(candidate=pin,current=current[p]) for p,pin in old.items() if current[p]!=pin}
assert {Path(p).name for p in changed}=={'fraktal_ab_part_execute.py','test_fraktal_ab_part_execute.py'}
for p,row in changed.items():assert sha((R/'ExecutedCandidateSource'/Path(p).name).read_bytes())==row['candidate']
with (R/'executed_source_audit_01.json').open('x') as f:json.dump(dict(passed=True,controllerAccess=False,candidateBindings=143,currentBindings=143,changesAfterCandidate=changed,plcSourceUnchanged=True,explanation='After candidate acceptance, the fixture AUTO return waits only for mode application. The controller owns subsequent START release. The stricter pre-HOME wait is unchanged. Current full suite and 31 baseline rows pass; exact candidate source copies are retained.'),f,indent=2)
NAME='AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23';report=E/(NAME+'.md');assert not report.exists()
text='''# S3f retained revision and active-model native acceptance

2026-10-23, America/Mexico_City. Local FactoryTalk Logix Echo, 127.0.0.1 slot 0,
1756-L81E v38.011, serial `601FC87B`. **S3f exit passes at this Echo scope.**
V2 remains inactive; later publication surfaces, Dart/HMI, physical retention
and commissioned CIP Security acceptance remain open. No commit or push.

## Authorization and exact artifacts

The owner answered **“Approve the follow-up session”** to
`call_b8e9e258f03f4b089d447c3e1e056603:0`. The approved scope includes fresh
backup/deploy, 41 inherited candidate checks, two simulated CHANGEOVERs via
the existing tooling confirmation, one retained Program/Run cycle without a
download, read-only measurements, genealogy rollback and 31 baseline checks.
Fault clearing and clock setting were excluded and were not performed.
This exact session is complete and its authorization consumed.

- Prepared ACD: `BD030AEB01D58469D452D877A9CFF2868B79DE45055A3795D1D1479BB2771183`.
- Generated PLC source: `B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3`.
- SDK-saved deployed ACD: `4838C32ED0E54DC7DFC0260D612D8E05541A6EB3391FB7C2D7AB4312B4177494`.
- Fresh uploaded backup: `B2744B32938D96F632DC505DAFAEC895D34BA07905A1BF11A3DFE179FEDD0379`.
- Immutable genealogy ACD: `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

The immutable original was hash-checked and only a new copy opened for rollback.
All SDK operations and strict read-back/access audits pass. The prepared image
retains both v38 compiler/read-back/access qualifications in the
[preparation record](AB_S3F_CANONICAL_REVISION_PREPARATION_2026-10-23.md).
Neither native ACD files nor actual credential files are archived.

## Accepted native checks

**74 checks pass:** 31 inherited candidate rows, two Access rows, eight
configuration rows, one active-model round-trip row, one retained restart,
and 31 restored genealogy rows. The accepted fixture is
`Runtime/candidate_regressions_05.json`; the accepted baseline is
`Runtime/baseline_regressions_02.json`.

The model vector performs model 1 → 2 → 1 through the ordinary CHANGEOVER
chains and tooling decision 2/answer 1. Active ModelCode and revision change;
live configuration, all banks, public fixture inputs and mode restore exactly.
Private ModelRequest is never written.

The retained restart has exactly two successful mode changes and **no download**.
Root/page revisions agree and change **745193095 → 1646242802**. Records, banks,
catalogue, active model, mode, data policy and page content remain equal.
The one-assignment first-scan fix prevents the reproduced old-token collision;
the lower/equal/zero/wrap cases also remain model-tested.

All **93 accepted paired captures** replay from native bytes, including complete
fragment frames and independently reconstructed provider contexts. They contain
2,617 / 2,567 / 2,217 paths and logical types for page 0 / page 1 / an empty page.
Seven modules are discovered generically without a station declaration.
Accepted acquisition attempts range **1–27**. Each proof still requires equal,
positive, even whole-scan generations, within **100 attempts / five seconds**.

The read-only observer now balances the same bounded fragment packets across
four independently guarded connections. All acquisition completes before the
closing generation sample; decoding/reassembly follows it. Malformed, partial,
overlapping and missing fragments remain refusals. The generic reader and PLC
image are unchanged. Regeneration still gives the exact prepared source hash.

## Memory, payload and scan

Automatic Studio Capacity: **73%; 2,298,448 used / 847,280 available /
3,145,728 total Blocks**, +36 versus the first S3f image. Blocks are not claimed
to be bytes. The accepted image can now join the measured calibration set.

Native canonical records total **133,156 bytes**: root 109,232, definitions
7,308, alarm metadata 16,616. Twenty native TASK timing samples per image:

| Image | Median last scan (µs) | Cumulative maximum (µs) | Overlaps |
|---|---:|---:|---:|
| S3f candidate, after retained restart | 835 | 4,573 | 0 |
| Restored genealogy | 99 | 1,168 | 0 |

These are Echo measurements, not physical-controller bounds.

## Failed runs retained and apparatus corrections

Every attempt remains in the payload. **125 actual recorded checks** include
51 extra rows from interrupted runs; they do not increase the 74 accepted count.

| Run | Result and recovery |
|---|---|
| Opening verifier 01 | Local compressed-filename mapping error, before authorization/controller action; corrected verifier 02 passes. |
| Candidate 01 | Page-1 acquisition exhausted 100 attempts; two Access rows recorded; cleanup passed. |
| Candidates 02, 03 | The interrupted query left page 1 selected while the fixture expected page 0. Cleanup LOGIN also met still-busy hashing (727). Settled MANUAL normalization and public QUERY_CONFIG(page 0/model 0) passed. |
| Candidate 04 | 30 rows recorded, including all configuration/model vectors; START before an inherited HOME was refused with unit-not-ready key 739. Cleanup passed. |
| Baseline 01 | 19 rows recorded; an overstrict fixture wait after HOME timed out. Cleanup passed. |

The fixture now waits for HOME mode application and terminal reset before
START. Returning to AUTO waits for mode application; the next START still
consumes the controller's authoritative release report. No release predicate
or validation was weakened. The current full suite and baseline pass. Exact
candidate-executed copies of the two subsequently adjusted fixture/test files
are retained under `Runtime/ExecutedCandidateSource/`, with hash bindings in
`Runtime/executed_source_audit_01.json`. Current source bindings total **143**.

## Gates and final state

- AB discovery: **2,114 tests / 280.805s / OK**.
- Repository gate tests: **74 tests / 3.963s / OK** (and repeated after document updates).
- Both v38 compilers, prepared/downloaded read-back and access, SDK audits,
  exact native replay, specification/contracts and strict consistency pass.
- Final checks: Run/not faulted/Remote, scanning, MANUAL=1/idle/logged out,
  not restoring, all five saved/live documents equal, policy and frozen
  preflight equal, immutable original hash unchanged.
- All 21 predecessor seals / 4,328 artifacts verify unchanged before sealing.
- Flutter gates are not applicable: no HMI source changed. Physical and CIP
  Security acceptance are outside this Echo session and remain pending at S7.

Raw outputs, precise commands, timings, source bindings, failed attempts,
rollback audits and SHA-256s are in the sibling payload's `manifest.json`.
S3g contract inventory/offline review is next; this completed session grants
no further controller-changing operation.
'''
with report.open('x',encoding='utf-8') as f:f.write(text)
def replace_block(path,start,end,replacement):
 text=path.read_text(encoding='utf-8');a=text.index(start);b=text.index(end,a)
 path.write_text(text[:a]+replacement+text[b:],encoding='utf-8')
summary='''**Latest, 2026-10-23: S3f exit passes on Echo.** The authorized revision
follow-up completed 74 accepted checks (42 candidate, one retained Program/Run,
31 restored genealogy), with 93 independently replayed paired captures and
2,114 AB / 74 root tests passing. Revision changes 745193095 → 1646242802 across
the no-download restart; retained configuration/banks/policy/page stay equal.
Both model CHANGEOVERs and exact restoration pass. Capacity is 73%, 2,298,448
used / 847,280 available / 3,145,728 total Blocks. Candidate scan is 835 µs
median / 4,573 µs maximum; restored genealogy 99 / 1,168 µs; zero overlaps.
Read [revision runtime evidence](Evidence/AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23.md).
All failed attempts are retained (125 actual rows, 74 accepted); four read-only
connections and fixture mode-application waits leave the PLC image and generic
reader unchanged. Echo is restored to genealogy, Run/not faulted/Remote,
MANUAL=1/idle/logout, five saved/live documents equal, policy/preflight equal.
Current sources: 143. This session approval is consumed; V2 remains inactive.
S3g inventory/review is next; further native changes need their own current approval.

'''
replace_block(AB/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','**Latest follow-up, 2026-10-23:**','**Completed session, 2026-10-23:**',summary)
replace_block(AB/'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','**Latest, 2026-10-23: S3f revision follow-up prepared offline.**','**Completed, 2026-10-23: S3f runtime passes at the recorded scope.**',summary)
p=AB/'AB_CANONICAL_PUBLICATION_S3F_NOTES_2026-10-23.md';text=p.read_text(encoding='utf-8');a=text.index('**Latest:**');b=text.index('The owner approved',a);p.write_text(text[:a]+summary+'The following preparation/first-session details are historical.\n\n'+text[b:],encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3F_REVISION_FOLLOWUP_2026-10-23.md';text=p.read_text(encoding='utf-8');p.write_text('# S3f retained revision and active-model follow-up\n\n'+summary+'## Preparation history\n\n'+text.split('\n',1)[1],encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';data=json.loads(p.read_text());section=data['approvedConfigurationCorrection'];section.update(runtimeAccepted=True,runtimeAcceptedAtRecordedScope=True,runtimeEvidence='Evidence/'+NAME+'.md',previousRuntimeEvidence='Evidence/AB_S3F_CANONICAL_RUNTIME_2026-10-23.md',remainingNativeGates=[]);assert data['active'] is False;p.write_text(json.dumps(data,indent=2)+'\n')
p=AB/'AB_CAPACITY_OBSERVATIONS_2026-10-21.json';data=json.loads(p.read_text());assert len(data['samples'])==7
prep=E/'AB_S3F_CANONICAL_REVISION_PREPARATION_2026-10-23';capacity=prep/'Preparation/capacity_review.json'
data['samples'].append(dict(label='S3f',source='Evidence/'+prep.name+'/Preparation/genealogy_s3f_revision_01.L5X.gz',sourceSha256='b71e30abbe8221aaa39a0df8eeb934897fe0a4b0711047efdc7d653a20ae7cf3',capacity='Evidence/'+prep.name+'/Preparation/capacity_review.json',capacitySha256=sha(capacity.read_bytes()),acdSha256=v['preparedAcdSha256'],runtimeEvidence='Evidence/'+NAME+'.md'))
p.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(dict(passed=True,report=str(report),stageComplete=True,capacityObservations=8,activeV2=False)))

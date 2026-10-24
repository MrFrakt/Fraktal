# S3e canonical Access/data policy/audit: accepted Echo runtime

Date **2026-10-22**, America/Mexico_City; payload UTC timestamps are October 23.
Target: local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
Accepted scope: **2,154 genealogy values and types**, including Access/data
policy and enrichment of the existing 64-slot event ring. Shipping V1/Part III
remain authoritative; V2 stays inactive. This is no full-Core, physical-controller,
production scheduler or HMI acceptance claim.

The owner approved the exact image and guarded backup/download/candidate/
rollback/baseline session, including the two fixed Access vectors. The response
and scope are in `Session/authorization.json`. Fault clearing and clock changes
were outside scope and did not occur. No commit/push. Authorization is consumed.

## Bound artifacts and native gates

| Artifact | SHA-256 |
|---|---|
| Generated source | `3BFFCEADB98EC7B7B7AA05550202CC187C736A8C2B22C75B7B7D158BE4F5AD87` |
| Original prepared ACD pin | `95E85B507387A548553688C1B5CCF52D7D99B35751C68F1B02DE92AC2A1B240B` |
| SDK-saved candidate | `8D6A476193C421CE7ADDE6933EFAC3C4C7F501E7A1EECC79E64D86EB9CEDB2EC` |
| Fresh uploaded backup | `C3B31F147AEDDAB795C0A7550E57DE1C899A2FE4ED032FEFEF8A4776291925B8` |
| Immutable genealogy original | `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084` |

The original pin was not replaced after SDK saves. Restoration verified/copied
the immutable genealogy original, then opened/downloaded only the copy. Its
final SDK-saved hash is `EB888C422BA3EC367CAC768A1C7913BF33A649B8EC1AFA5C8F0C3CA8FAEAA9C1`.
The original was never opened and its hash is unchanged. Backup, candidate and
rollback SDK logs pass content audits. Backup uses Save/Save As because its
upload operation is named Open Project From Controller. Candidate and restored
read-backs are equivalent; backup/rollback access equals the exact sealed
109-tag genealogy policy. Candidate's 133-tag image and canonical member
access pass, including both read-only metadata bindings.

Both v38 compiler/build/read-back/access gates are reused from the exact
unchanged [preparation](AB_S3E_CANONICAL_PREPARATION_2026-10-22.md): 111 UDTs,
seven AOIs, 48 executable bodies, 21 SFC steps and 30,949 authored initial values.
The PLC image, task period, lifecycle, authority checks and original stimuli
were not changed during this session.

## Acceptance and the audit-index mistake

`candidate_regressions_01` completes **31/31 inherited rows and both approved
Access checks** on its first run, with document and policy cleanup passing.
Every saved comparison matches all 2,154 values/types. The first post-session
audit nevertheless fails with `manual policy transition missing` because it
incorrectly tests **Required[1]** for MANUAL.

Native dispatch writes `Required[HmiRequest.IntValue]`; the owner's action map
defines MANUAL as **zero-based gate 2**. The legacy oracle presents that slot
as Required[3]; approved D2 mapping makes it canonical **Required[2]**. The
original full captures already show 0 and 1 at that correct path, including
1 in the logged-out capture. No native publication defect was found.

Before identifying the wrong index, a temporary read-only observer was added
after the fixture's existing manual-policy commands. It made the same bad
assumption and stopped an unnecessary repeat, `candidate_regressions_02`, at
`existing manual policy change must be observed at its commit`. That repeat
recorded **one passing inherited row and two passing Access checks**; its six
comparisons also matched all 2,154 values/types. Its assertion was wrong.
Document/policy cleanup passed again.

The temporary observer/test edits were restored byte-for-byte. **All 76 prepared
root source hashes match again**, including every generator/PLC input. Both
erroneous variants, the temporary tests, failed outputs and original correct
observer are retained. The temporary fake-parent test passed its same incorrect
assumption and is not used as final acceptance evidence. Final original fixture
tests pass separately. The corrected post-session audit derives MANUAL's index
from `fraktal_ab_access.GATES[fraktal_ab_mailbox.MANUAL_COMMAND]`; it accepts the
original complete immutable captures under the original six-phase criteria.
This corrects the gate's index without weakening its required coverage.

`Runtime/candidate_acceptance_02.json` records that acceptance. The first failed
audit and partial repeat remain failures. No further candidate matrix was run.
Idle equivalence and generic discovery after cleanup also pass, and the original
baseline fixture passes **31/31** after genealogy restoration.

## Accepted values and behaviors

| Accepted observations | Result |
|---|---|
| Candidate inherited rows | 31/31 |
| Additional Access rows | 2/2 |
| Restored-baseline rows | 31/31, first run |
| Decision captures | 4 |
| Held/fault captures | 14; both kinds at ST/SFC/LD |
| Sequence captures | 21; seven cases per rendition |
| Reset captures | 8, four before/after pairs; all renditions |
| Access captures | 6 |
| Paired captures including idle | 54, independently replayed |
| Generic discovery | 7 modules, 2,154 paths |

Access phases observe LoginBusy, failed unknown-user login with no authority,
successful login, logout, one changed/restored class policy, and the inherited
manual-policy transition. Manual Required[2] and the exercised class ReadLevel
both show 0/1. Audit text matches the owner for failed login and operator actions,
including actor/action fields, while retaining the one existing event ring.
The unsigned result-sequence logical type is UInt32; its high-bit conversion is
model/unit-tested, with no native high-bit injection performed.

All paired values/types match, with only the five explicit D2 array-bound
mappings. Raw native records and legacy raw responses independently re-decode
to identical canonical snapshots and oracle values in `capture_replay_01`.
The **whole-scan equal-even proof and 100-attempt/five-second limits are unchanged**.
Accepted attempts range **1-41**, over two independently guarded read-only
connections; V6.2 metadata uses equal manifest/configuration/fragment revision
tokens. The tighter acquisition margin remains an S4 transport/scheduling risk.

Sequence coverage retains fast completed steps, mode clearing, sparse handled
notes, HELD/resume, abort, adopted fault and single-reset restart across all three
renditions. Active/closed events, state-flag transitions, Blocking release, ring
wrap and positive closed duration are observed; maximum duration is 1,660 ms.
Active-slot states observed are EMPTY=0 and ACTIVE=1. WAIT_RESET remains
model-only coverage. Arbitrary actor bytes, signed formatting extremes, invalid
class identities/schema, data-denial capability detail and counter high bits
were not injected into the controller in this session. Existing full-Core gaps
and the lack of an EM/concurrent-leg fixture remain explicit.

There are **67 recorded regression rows** across the session:
31 + 2 accepted candidate, 1 + 2 partial repeat, 31 baseline. **64 are the planned
accepted matrix and three are extra rows** from the partial repeat. Each of the
two fixed-vector executions sends one unknown-user LOGIN and two class-level
commands (change/restore): six known mailbox commands. Initial MANUAL checking
needed zero writes; candidate and baseline cleanup each needed existing
LOGIN/SET_MODE(1)/LOGOUT frames: six more. Thus **12 known additional mailbox
commands** are recorded separately from inherited fixture activity. Individual
tag-write calls were not instrumented; rows are not an exact write count.

## Capacity, native sizes and scan

Qualified automatic Studio Capacity is **49%**: **1,568,852 used /
1,576,876 available / 3,145,728 total Blocks**, **+278,836 over S3d**. The
source-preserving two-sample receipt is sealed in preparation. Blocks are not
assumed bytes; this offline estimate is distinct from online memory.

The held-out six-sample forecast was 1,439,517 Blocks, error -129,335
(-8.2439%), planning budget 1,681,312. Forecasts remain advisory with no
guaranteed error bound. The accepted measurement is added as the seventh
catalog observation only after candidate and restored-baseline acceptance.

| Native record | Template / complete payload bytes |
|---|---:|
| Press root | 77,856 |
| Sequence definitions | 7,308 |
| Alarm metadata | 16,616 |
| Total | 101,780 |

Each Template byte size equals the complete native raw payload size. No source
count or transport-overhead assumption substitutes for these measurements.

| Native TASK observation, 20 samples | Candidate | Restored genealogy |
|---|---:|---:|
| LastScanUs median | 817 | 99 |
| LastScanUs range | 816-817 | 99-100 |
| Cumulative MaxScanUs | 4,033 | 1,167 |
| OverlapCount | 0 | 0 |

Workload/history differ, including the partial repeat. These observations do
not isolate publication cost by subtraction.

## Closing gates and state

- Exact unchanged preparation AB suite: **Ran 2078 tests in 280.759s / OK**,
  reused after all 76 root sources were verified to match again.
- Fresh root suite: **Ran 74 tests in 2.112s / OK**.
- Final original fixture-observer tests: **Ran 15 tests in 0.027s / OK**.
- Spec/contracts: pass. Strict consistency: **0 error(s), 0 warning(s)**.
- Whitespace: pass with CR-at-EOL configuration.
- Both unchanged v38 native builds and candidate/rollback read-back/access: pass.
- HMI/Flutter: not applicable; this work made no HMI change.

Final checks confirm exact identity, Echo service/listener, **Run, not faulted,
Remote, scanning, actual MANUAL=1/idle, logged out, not restoring**, all five
saved/live documents equal, original policy/preflight and unchanged immutable
genealogy hash. **16 predecessor seals / 2,854 artifacts** verify unchanged.

The payload manifest hashes all archived artifacts and this report. Actual
credential files/contents and native ACDs are excluded; failed runs are retained.
The S3e authorization is consumed. **S3f preparation is next**; future controller
work requires its own exact-image gates and current explicit authorization.

"""Record only completed offline read-surface work; never authorize a session."""
from pathlib import Path
import hashlib, json, sys
R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
S=R/'Specification/AllenBradley'
sha=lambda b:hashlib.sha256(b).hexdigest()
paths=[S/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',S/'AB_FROZEN_CONTRACTS_V2.json',S/'AB_CANONICAL_PUBLICATION_S3K_NOTES_2026-10-25.md']
before={p.relative_to(R).as_posix():sha(p.read_bytes()) for p in paths}
for p in paths:
    with (W/('before_'+p.name)).open('xb') as f:f.write(p.read_bytes())
notes='''# S3k engineering notes - mailbox, reports and remaining Unit fields

Non-normative working notes, 2026-10-25. The semantic contract is already
owner-approved in the [remaining-S3 review](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md).
S3k is in progress: read surfaces, the versioned report owner and R4 compile
offline. Command binding awaits the [A/B owner choice](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md).
No S3k controller operation is authorized or performed. The restored genealogy
baseline remains loaded; read-only identity/preflight checks pass. No commit or push.

## Inventory and implemented read surfaces

The approved inventory's stage labels select exactly **133 frozen paths**:
126 mailbox/report, five production fields and two Features flags. Of the 126,
122 describe the complete 24-slot release report, three the response and one
the request Sequence. Nine additional Core request arguments are discovery
surface, not cyclic process values. There are 39 Core operation ordinals,
including NONE=0. Supported/refused operations remain declaration-dependent.

The stage-13 engineering profile publishes those 133 paths with Core widths,
UInt32 counter/sequence bits, shared derived Starved/Blocked conditions and
native BOOL Features flags. A safe input tap supplies only request Sequence.
The report renderer resolves portable keys/source identities through shared
PLC text, updates on acknowledgement, clears all unused rows, publishes ACK
last, and invalidates corrupt or overflowed reports. Its invalid state stays
latched until a new response; unknown diagnostics preserve the legacy key and
signed-number fallback. Full request arguments are not yet published.

The independent S3k oracle extends the accepted S3j reference by the exact
133-path inventory. It reads only safe request Sequence, response/report and
existing approved inputs; it never samples Frame, Secret or staged credentials.

## Reports and R4

The private V2 report owner derives capacity from Core MAX_RELEASE_REASONS=24.
Earlier profiles retain their released eight-entry owner. All append/open/
close/copy emitters receive the declaration. The new owner marks Overflow,
refuses invalid indices without array access and cannot release an incomplete
report. Generation checks reachable Start-report completeness against 24.

R4 replaces repeated manual-command CASE routing with generated module/command
tables and one bounded dispatcher. Cache the exact Busy and directional permit
facts **inside the mailbox handler, after its session/data/config prologue and
immediately before dispatch**. Accepted intent is applied automatically in the
existing generated module scan path, preserving same-scan Execute drop and
ManualCmd behavior. No project call is added. Missing permits retain the
existing device HELD behavior rather than adding a stricter action gate.

## Command ABI decision remains open

The earlier engineering idea of aliasing the entire legacy request into the
canonical request is not selected. The existing request embeds staged services;
its declared-size tally is 9,448 bytes, not a measured native Template size.
It cannot simply be written whole under the current unfragmented-payload rule.

The [concrete review](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
asks the owner to choose A: a compact typed Core payload, PLC routing, one owner
and temporary legacy Frame adapter; or B: the frozen Frame ingress with fully
PLC-published generic encoding/lookup metadata. No dependent command binding
is implemented while this required choice is pending. Core BoolValue must be
a genuine BOOL; the old overloaded private DINT cannot be relabelled.

ConfigSet/ConfigProvider extensions must remain discoverable and validated
until their S6 replacement owners exist. Generic cyclic acquisition must never
sample command payloads. Secret exclusion must cover uncommitted bytes and
bytes beyond LEN before any readable frame or persisted capture exists.
The safe Sequence tap is not qualification of that complete command policy.
There must be one dispatcher, bounded snapshot/commit ordering, explicit
competing-ingress refusal, and no reconnect replay. Full operation/service
inventory and boundary proofs remain mandatory.

## Completed offline gates

Work: `C:/work/fraktal-ab-s3k-20261025/`, especially `read_surface_01/`.
Evidence: [offline record](Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md).

- **2,264 AB tests** pass; **74 root tests**, spec/contracts and strict
  consistency gates pass. Executed model tests cover all 24 reasons, overflow,
  invalid indices, ACK clearing/caching, signed fallback, counter bit patterns,
  corrupt descriptors and released/new manual action/report equivalence.
- Generated read-surface source `ADA479AC...01FD515` compiles on both v38
  EchoController and PhysicalController targets with zero import warnings/
  errors. Strict read-back matches 64 bodies and 58,314 initial values; native
  effective-access audits pass. The generated inert owner probe also passes.
- Offline ACD `CB180CDD...6F0ED6` opens, builds, saves, reopens and reads back
  equivalently. It is an incomplete engineering image, not a deployment offer.
- Automatic Studio Capacity: **1,807,120 used / 1,338,608 available / 3,145,728
  total Blocks**, **57% displayed**, +64,040 versus accepted S3j. No S3k scan
  measurement has been made; its controller runtime is unaccepted.
- All **12 accepted image pins** regenerate byte-identically. All **1,385
  archived captures** replay with their exact historical schemas/rules.
- Failed development checks and the build-driver comparison of a stale export
  are preserved. Correct final source/export pairs pass; an intermediate full
  suite whose source changed is explicitly superseded by suite 02.

## Next and remaining gates

Resolve the A/B ABI choice, freeze its detailed wire/state table, implement
command discovery/owner integration and prove secret exclusion and all service
bindings. Then run the complete S3k offline gates on the full image, measure
Capacity and prepare native report/request regressions with exact restoration.
Only after that can a current, exact-image authorization request be made for
the guarded native session, inherited regressions, value/type equivalence and
scan measurement. This partial image is not authorized for download.

S3 final also needs press ST/SFC/LD equivalence and real-module identity/offline
proof. S4-S7, physical/security acceptance and the later persistence, station
write-posture, hardware and commit/push decisions remain open. V2 stays inactive.
'''
paths[2].write_bytes(notes.replace('\n','\r\n').encode())
plan=paths[0].read_bytes()
anchor='**Latest, 2026-10-25: S3j native acceptance passes on genealogy/Echo.**'.encode()
assert plan.count(anchor)==1
intro='''**Latest, 2026-10-25: S3k read surfaces and R4 pass offline; command ABI choice pending.**
The approved 133 read paths, versioned 24-reason owner and table-driven manual
dispatcher compile/read back on both v38 targets; effective access passes.
All 2,264 AB and 74 root tests pass. Twelve accepted image pins regenerate
byte-identically and all 1,385 prior captures replay. The incomplete offline
image uses 1,807,120 / 3,145,728 Blocks (57% displayed), +64,040 versus S3j.
No S3k download, native regression or scan measurement has occurred.
The [command ABI review](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
asks A (typed Core payload and temporary legacy adapter, one owner) or B
(frozen Frame with published encoding/lookups). The whole legacy request also
embeds staged services and cannot simply become one bounded payload. Dependent
command binding waits for this choice; the semantic contract is already approved.
Next: chosen command binding, secret exclusion and service discovery, complete
offline gates, then separately authorized exact-image native acceptance. Genealogy
is unchanged, V2 inactive, no commit/push. Read [offline evidence](Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md)
and [engineering notes](AB_CANONICAL_PUBLICATION_S3K_NOTES_2026-10-25.md).

**Earlier, 2026-10-25: S3j native acceptance passes on genealogy/Echo.**'''
paths[0].write_bytes(plan.replace(anchor,intro.replace('\n','\r\n').encode()))
v=json.loads(paths[1].read_bytes())
scope=v['approvedRemainingSurfaceCorrection']
assert scope['stageStatus']['S3k']=='pending'
scope['stageStatus']['S3k']='read-surfaces-r4-offline-pass-command-abi-choice-pending'
scope['s3kOfflineReadSurfaces']={
 'evidence':'Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md',
 'readPaths':133,'releaseReasonCapacity':24,'tableDrivenManualDispatch':True,
 'fullCommandBindingImplemented':False,'commandBindingChoicePending':True,
 'commandBindingReview':'AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md',
 'nativeAccepted':False,'controllerChangesAuthorized':False,'controllerChangesPerformed':False,
 'sourceSha256':'ADA479ACA4305DD07E512ABDDC16446E9FDB220562A641FC0E6F026C201FD515',
 'offlineAcdSha256':'CB180CDD8F6ED31380C3D288B13FA746313BC8A5E1F1677CBF3630FEAF6F0ED6',
 'abTests':2264,'rootTests':74,'acceptedImagesByteIdentical':12,'priorCapturesReplayed':1385,
 'usedStandardBlocks':1807120,'availableBlocks':1338608,'totalBlocks':3145728,
 'displayedUsagePercent':57,'deltaUsedVsS3jBlocks':64040,'scanMeasured':False}
paths[1].write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+'\n').replace('\n','\r\n').encode())
with (W/'documentation_updates_01.json').open('x',encoding='utf-8') as f:
    json.dump({p.relative_to(R).as_posix():{'beforeSha256':before[p.relative_to(R).as_posix()],'afterSha256':sha(p.read_bytes())} for p in paths},f,indent=2)
print(json.dumps({'updated':[p.name for p in paths],'controllerChangesAuthorized':False}))

"""Record S3h acceptance only after all native and offline replay gates pass."""
from pathlib import Path
import hashlib,json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
v=json.loads((R/'runtime_verification_01.json').read_text())
assert v['passed'] and v['acceptedTotalChecks']==72 and v['allNativeSessionSourcesUnchanged']
timing=v['timing'];tr=v['traceObservations'];a=v['attempts'];c=timing['candidate'];b=timing['baseline']
name='AB_S3H_CANONICAL_RUNTIME_2026-10-23'
summary=f'''**Latest, 2026-10-23: S3h exit passes on Echo.** All 72 planned checks
pass: 41 candidate cases and 31 restored-genealogy regressions. All 88 paired
captures replay exactly from native bytes and independent legacy-owner/provider
references, with the finite approved Core type changes and five D2 bounds.
Full-ring page totals are 3,950 / 3,900 / 3,550; occupied physical event slots
follow PLC Count. The whole-scan proof accepts in {a['minimum']}–{a['maximum']} polls
under the unchanged 100-poll/five-second limit, with one-millisecond pacing
only after an unchanged even generation. Four sockets retain one pending read
each. All 159 prepared source files remain unchanged; the bound 2,149 AB and
74 root tests, both v38 builds/read-backs/access and exact-image Capacity apply.

Automatic Capacity is 79%: 2,501,720 used / 644,008 available / 3,145,728 total
Blocks, +94,520 over accepted S3g. Native records total 157,668 bytes:
133,744 root / 7,308 definitions / 16,616 alarm metadata. Candidate TASK median/
cumulative maximum is {c['medianUs']:g} / {c['cumulativeMaximumUs']:g} µs;
restored genealogy {b['medianUs']:g} / {b['cumulativeMaximumUs']:g} µs; zero overlaps
in both 20-sample sets. These are observations under different workloads,
not an isolated publication-cost measurement. S3h is now the tenth accepted
Capacity calibration sample. Earlier failed native attempts stay sealed.

Genealogy is restored: Run/not faulted/Remote/scanning, MANUAL=1/idle/logout,
not restoring, all five saved/live documents and original policy/preflight
equal. No fault clear or clock change occurred. This exact session's approval
is consumed; further controller changes need a new current scope. V2 remains
inactive; no commit or push. Read
[S3h runtime evidence](Evidence/{name}.md).
S3i Line inventory is next; 149 legacy paths remain across S3i–S3k, followed
by S4–S7. This is genealogy/Echo acceptance, not completion of canonical AB.

'''
for filename,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/filename;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: paced S3h retry prepared; current authorization pending.**',
             '**Earlier paced S3h retry preparation (completed above):**',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';old=p.read_text(encoding='utf-8')
old=old.replace('**Latest, 2026-10-23: paced S3h retry prepared; current authorization pending.**',
                '**Earlier paced S3h retry preparation (completed above):**',1)
p.write_text(old.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';t=p.read_text(encoding='utf-8')
assert '## S3h Echo acceptance (2026-10-23)' not in t
p.write_text(t+'\n\n## S3h Echo acceptance (2026-10-23)\n\n'+summary,encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
m=d['approvedTraceabilityCorrection'];m.update(runtimeAccepted=True,runtimeAcceptedAtRecordedScope=True,
 runtimeEvidence='Evidence/'+name+'.md',remainingNativeGates=[],runtimeScope='Local Echo 601FC87B genealogy fixture; physical/CIP Security, other declarations and later stages remain open',
 sessionAuthorizationConsumed=True,controllerChangesAuthorized=False,retryPrepared=False,
 lastNativeAttempt='Evidence/'+name+'.md',lastNativeAttemptPassed=True,sourceBindings=159,
 runtimeChecks=dict(candidate=41,baseline=31,total=72),pairedCaptures=88,
 nativePayloadBytes=157668,nativeRecordBytes=[133744,7308,16616],timingUs=timing,
 traceObservations={k:x for k,x in tr.items() if k not in ('rows',)})
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
p=AB/'AB_CAPACITY_OBSERVATIONS_2026-10-21.json';d=json.loads(p.read_text());assert len(d['samples'])==9
source='Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23/Preparation/s3h_candidate_03.L5X.gz'
capacity='Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23/Preparation/capacity_review.json'
assert (AB/source).is_file()
d['samples'].append(dict(label='S3h',source=source,sourceSha256=v['sourceSha256'],capacity=capacity,
 capacitySha256=hashlib.sha256((AB/capacity).read_bytes()).hexdigest(),acdSha256=v['preparedAcdSha256'],
 runtimeEvidence='Evidence/'+name+'.md'))
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h canonical traceability runtime — 2026-10-23

**S3h passes at the recorded genealogy/Echo scope.** The owner approved
`call_9b203bdff24848999469abe17a76ee4f:0`, “Approve this guarded paced S3h
retry”, for local Echo `601FC87B`, 127.0.0.1 slot 0, 1756-L81E v38.011.
All 72 planned checks pass and genealogy is restored. This session consumes
its exact-artifact approval. Fault clears and clock changes were excluded.

| Gate | Result |
|---|---|
| Fresh target, service/listener, fault/Remote and preflight | Pass; five saved/live documents and original policy match |
| Fresh upload/backup | Pass; SDK Save As and baseline tag/access audit |
| Deployment | Program/download/Run; SDK log, exact generated-source read-back/access and guards pass |
| Candidate fixture | 31 inherited regressions + two Access + eight configuration checks = 41, restored inputs/policy |
| Paired reads | 88 exact path/type/value comparisons, re-decoded from native frames and independently reconstructed reference/provider contexts |
| Page bounds | Full ring: 3,950 / 3,900 / 3,550 paths; variable occupied prefix follows independently bracketed PLC Count |
| Entire-scan proof | Equal positive even generation; {a['minimum']}–{a['maximum']} polls, original 100 polls/five seconds including all waits |
| Transport | Four sockets, at most one request outstanding per socket, 47 complete read packets; decoding after closing sample |
| Generic idle acquisition | Pass, discovered through Symbol/Template/manifest; no station declaration in reader |
| Native sizes | 133,744 root + 7,308 definitions + 16,616 alarm metadata = 157,668 bytes |
| Candidate TASK | 20 samples, median {c['medianUs']:g} µs, LastScan range {c['minimumUs']}–{c['maximumLastUs']} µs, cumulative max {c['cumulativeMaximumUs']} µs, zero overlaps |
| Restored baseline TASK | 20 samples, median {b['medianUs']:g} µs, LastScan range {b['minimumUs']}–{b['maximumLastUs']} µs, cumulative max {b['cumulativeMaximumUs']} µs, zero overlaps |
| Automatic Capacity | 2,501,720 used / 644,008 available / 3,145,728 total Blocks, 79%; +94,520 vs accepted S3g |
| Rollback and final checks | Hash-checked genealogy copy, strict sealed-reference read-back, 31/31 regressions, five-document restore, original policy, Run/not faulted/Remote/scanning, MANUAL/idle/logout/not restoring |
| Source and offline gates | All 159 files unchanged during session; 2,149 AB / 74 root tests; both v38 build/read-back/access proofs reused by byte-identical source/image; strict cheap gates pass |
| Fault clear / clock change / commit / push | None |

The 278 added paths are Part (40), HostEvents (220), Nameplate (10),
SignalTower (seven) and MachineState (one). Only the approved 36 type
corrections and unset Part timestamp empty-string-to-zero change; the other
242 added values/types remain exact. Existing genealogy/delivery extensions,
record/parent/event capacities, producer algorithms and ownership are unchanged.
Historical parents and resource text are read from captured event storage.
The PLC-published Count selects consumed physical event slots.

Observed occupied counts: `{tr['occupiedCountsObserved']}`; empty/partial/full
ring observed: `{tr['emptyRingObserved']}` / `{tr['partialRingObserved']}` /
`{tr['fullRingObserved']}`; wrapped: `{tr['wrappedObserved']}`. Part present
states: `{tr['partPresentObserved']}`; timestamps: `{tr['partStampsObserved']}`;
parent counts: `{tr['partParentCountsObserved']}`. PressDwell/RamPosition
measurements, cleared rows, historical-parent independence and captured resource
text pass. Empty/epoch/boundary cases retain their explicit offline qualification
where not observed natively. All 31 native owner rows, including signal-tower
tests, pass; exact observed canonical tower states are in the payload, with
all-seven mirror-state combinations qualified offline rather than inferred.

Candidate and baseline timing use different workloads; their difference does
not isolate publication cost. The Capacity observation is the exact prepared
image's Studio measurement, reused by hash and now added as the tenth accepted
calibration sample. Firmware/family/physical/CIP Security acceptance remain
separate. V2 is inactive; S3i–S3k still have 149 legacy paths, then S4–S7 remain.

Earlier native failures and paced-retry preparation remain sealed unchanged.
The observer's one-millisecond unchanged-even wait was qualified with 1,000
baseline proxy captures before download. It preserves the same comparison,
connections, packet coverage, deadlines and attempt count. No extra native
stimulus or retry loop was added to this accepted session.

Prepared ACD SHA-256: `{v['preparedAcdSha256']}`.
Generated source SHA-256: `{v['sourceSha256']}`.
SDK-saved spent ACD SHA-256: `{v['sdkSavedAcdSha256']}`.
Fresh backup SHA-256: `{v['backupAcdSha256']}`.
The immutable genealogy original was hash-checked/copied, never opened.
Native ACD binaries and credentials are not archived.

Work folder: `{R.as_posix()}`. Payload:
[manifest]({name}/manifest.json). Prior 32 seals / 7,749 artifacts verify
unchanged; all new raw captures, logs, exact outputs and source bindings are
archived. Further controller changes require a new current scope.
'''
with (AB/'Evidence'/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(passed=True,s3hStageCompleteAtRecordedScope=True,acceptedChecks=72,
 capacityCalibrationSamples=10,v2Active=False,authorizationConsumed=True)))

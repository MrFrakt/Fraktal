from pathlib import Path
import json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
v=json.loads((R/'failed_session_closure_01.json').read_text());assert not v['stageAccepted'] and v['baselineRestored']
assert json.loads((R/'restore_readback_01.log').read_text())['Equivalent']
summary='''**Latest, 2026-10-23: the guarded S3h retry failed the coherence gate;
genealogy is restored.** The first three Access captures match 3,742 paths/types
exactly, with the five approved D2 bound corrections. The fourth capture
(`class_policy_changed`) exhausts 100 polls: 93 waiting for a fresh scan,
three odd-generation polls and four complete read windows, each crossing one
scan boundary. There is no accepted value/type mismatch. All four sockets
retain one outstanding read each; the 100-attempt/five-second gate is unchanged.

Candidate cleanup, hash-checked genealogy rollback, all 31 baseline regressions,
strict rollback read-back and final Run/not-faulted/Remote/scanning,
MANUAL=1/idle/logout/not-restoring, five saved/live documents and original
policy/preflight equality pass. No fault clear or clock change occurred.
The current retry approval is consumed. S3h remains incomplete; the 41 candidate
checks, complete traceability coverage and candidate timing remain open.

All 159 bound sources remain unchanged during this attempt; the sealed
2,148 AB / 74 root tests and exact-image v38/Capacity proofs still apply.
Capacity remains 79%, not added as accepted calibration. Native record sizes
from the three valid captures are 133,744 / 7,308 / 16,616 bytes. The next
offline task is to pace fresh-generation polling and reduce acquisition
overhead; another native session requires a newly prepared, reviewed scope.
V2 remains inactive; no commit or push. Read
[retry-attempt evidence](Evidence/AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md).

'''
for name,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/name;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: S3h retry prepared; current session approval pending.**',
             '**Earlier S3h retry preparation (attempt completed above):**',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8')
t=t.replace('**Latest, 2026-10-23: S3h retry prepared; current session approval pending.**',
            '**Earlier S3h retry preparation (attempt completed above):**',1)
p.write_text(t.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
m=d['approvedTraceabilityCorrection'];m.update(runtimeAccepted=False,controllerChangesAuthorized=False,
 sessionAuthorizationConsumed=True,lastNativeAttempt='Evidence/AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md',
 lastNativeAttemptPassed=False,partialPairedCaptures=3,baselineRestored=True,sourceBindings=159,
 retryPrepared=False,retrySessionConsumed=True,remainingNativeGates=[
 'fresh-edge polling and transport timing within unchanged 100-attempt/five-second proof',
 'complete 41 candidate checks and traceability coverage','final generic/idle acquisition and candidate scan',
 'successful complete native session with rollback'])
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h guarded native retry — 2026-10-23

**S3h remains incomplete. Genealogy is restored.** The current owner approved
`call_b3c6555953654068a83f787a8b82de5e:0`, “Approve this guarded S3h retry”,
for Echo `601FC87B`, 127.0.0.1 slot 0, 1756-L81E v38.011. This exact session
is finished and consumes its approval. No fault clear or clock change occurred.

| Gate | Result |
|---|---|
| Identity/service/listener/Remote/not-faulted, MANUAL/idle/logout, five documents | Pass |
| Fresh backup | Pass; SDK Save As and baseline access audits pass |
| C6B42327…5D7D9DC deployment | Pass; Program/download/Run; SDK log, strict source read-back and access pass |
| Paired comparison | Three Access captures pass at 3,742 paths/types; only five D2 bounds normalized |
| Fourth capture | `class_policy_changed` fails before comparison: no completed PLC scan held across paired window |
| Failed acquisition history | 100 polls: 93 waitingFreshScan, three odd, four complete read windows; all four advance one scan |
| Candidate fixture | Incomplete; one unknown-user refusal row passes, zero inherited final rows; planned 41 cases remain unaccepted |
| Candidate cleanup | Input/policy restoration passes |
| Genealogy rollback | Hash-checked copy downloaded; SDK log/access and strict sealed-reference read-back pass |
| Baseline | 31/31 regressions pass, restored documents/policy |
| Final readiness | Run, not faulted, Remote, scanning; MANUAL=1/idle/logout/not restoring; five saved/live documents and preflight/policy equal |
| Candidate idle/generic/timing/complete traceability coverage | Skipped after failure; remain open |
| Exact-image build/Capacity gates | Reused by source/ACD hash; both v38 targets, read-backs/access and 79% Capacity remain valid |
| Source closure | All 159 source files unchanged during native session; preparation's 2,148 AB and 74 root tests apply |
| Fault clears / clock changes / commit / push | None |

The observer uses four prewarmed sockets with one outstanding request each,
fresh completed-generation scheduling, full fragment/MSP byte coverage and
decoding after its closing generation sample. The unchanged gate is 100 polls
and five seconds. This retry shows a scheduling limit: repeated waiting polls
consume 93 attempts before only four complete read windows can be attempted.
Each of those windows crosses one scan boundary. This is transport/coherence
failure, not an observed path/type/value mismatch. No field, feature, bound,
task period or validation rule was relaxed. No new download is authorized.

The next offline work will qualify paced polling and reduce read-window
overhead before a concrete new retry is proposed. Native records from the
successful captures total 157,668 bytes: 133,744 root, 7,308 definitions and
16,616 alarm metadata. Exact-image automatic Studio Capacity remains
2,501,720 used / 644,008 available / 3,145,728 total Blocks (79%). S3h is
not added to accepted calibration. Baseline TASK samples are retained;
candidate timing was not reached.

An offline inspection initially compared old/new D2 paths directly and failed.
Its retained correction uses the existing five-bound comparator; all three
stored captures replay and compare exactly. This did not change native code,
comparison acceptance or any controller action. Both audit versions and logs
are archived, alongside the failed native capture.

Prepared ACD SHA-256: `{v['preparedAcdSha256']}`.
Generated source SHA-256: `{v['sourceSha256']}`.
SDK-saved spent ACD SHA-256: `{v['sdkSavedAcdSha256']}`.
Fresh backup SHA-256: `{v['backupAcdSha256']}`.
The immutable original genealogy ACD was only hash-checked and copied, never
opened. Credentials and ACD binaries are not archived.

Work folder: `{R.as_posix()}`. Payload:
[manifest](AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23/manifest.json).
Earlier preparation and failed-attempt evidence remain sealed unchanged.
V2 stays inactive. Overall S3 completion, Dart client/gateway retirement,
physical and CIP Security acceptance remain open.
'''
with (AB/'Evidence/AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md').open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(passed=True,stageAccepted=False,baselineRestored=True,approvalConsumed=True)))

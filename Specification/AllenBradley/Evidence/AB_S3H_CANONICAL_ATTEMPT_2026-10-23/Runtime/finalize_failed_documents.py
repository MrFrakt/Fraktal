from pathlib import Path
import hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley'
v=json.loads((R/'failed_session_closure_01.json').read_text());assert not v['stageAccepted'] and v['baselineRestored']
summary='''**Latest, 2026-10-23: S3h native attempt stopped at the coherence gate;
genealogy is restored.** Ten paired captures matched all paths/types exactly,
but configuration capture six exhausted 100 attempts under the unchanged
five-second, four-connection proof. The 47-request read plan (42 fragments,
five batches) needs lower latency; no value tolerance or retry-budget extension
is accepted. Candidate fixture cleanup and genealogy rollback pass, followed
by all 31 baseline regressions and final Run/not-faulted/Remote/scanning,
MANUAL=1/idle/logout, five saved/live documents and policy/preflight equality.
No fault clear or clock change occurred. This session authorization is consumed.

Before download a reference callback incorrectly treated its Boolean path
selector as a document. It now takes occupied Count from the independently
bracketed owner. Two regression tests were added; all 2,140 AB / 74 root /
13 focused tests and cheap gates pass. PLC source/ACD and generic reader
remain byte-identical; only the reference and its tests changed before download.
The prepared Capacity gate stays 79%; the pending stage is not calibrated as
accepted. Native record sizes from successful pairs are 133,744 / 7,308 /
16,616 bytes, 157,668 total. S3h remains incomplete; V2 stays inactive.
Read [failed-attempt evidence](Evidence/AB_S3H_CANONICAL_ATTEMPT_2026-10-23.md).

'''
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md'):
    p=AB/name;t=p.read_text(encoding='utf-8');needle='**Latest, 2026-10-23: S3h offline preparation passes; native authorization pending.**'
    assert t.count(needle)==1;t=t.replace(needle,summary+'**Earlier S3h offline preparation (native attempt recorded above):**',1);p.write_text(t,encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8');t=t.replace('\n\n','\n\n'+summary,1);p.write_text(t,encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';data=json.loads(p.read_text());assert not data['active'];m=data['approvedTraceabilityCorrection']
m.update(runtimeAccepted=False,controllerChangesAuthorized=False,sessionAuthorizationConsumed=True,
    lastNativeAttempt='Evidence/AB_S3H_CANONICAL_ATTEMPT_2026-10-23.md',lastNativeAttemptPassed=False,
    partialPairedCaptures=10,baselineRestored=True,abTests=2140,focusedTests=13,
    remainingNativeGates=['same-scan acquisition latency within unchanged 100-attempt/five-second proof',
        'complete 41 candidate checks and lifecycle/full-ring coverage','final generic/idle acquisition and candidate scan','successful complete native session with rollback'])
p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h canonical native attempt — 2026-10-23

**S3h is not accepted.** This exact-image session stopped at a read-only
whole-scan acquisition failure and restored genealogy. Its current owner
approval was `call_ee9b48ca64a744a5a7221f84bf3615a1:0`, “Approve this guarded
S3h session”, for local Echo `601FC87B`, 127.0.0.1 slot 0, 1756-L81E v38.011.
The completed attempt consumes that authorization. No further controller
change is authorized by it. Fault clears and clock changes were excluded.

| Check | Outcome |
|---|---|
| Fresh guard, MANUAL/idle/logout and five-document preflight | Pass; no initial normalization writes needed |
| Fresh SDK upload/backup | Pass; Save As log audit and exact sealed baseline tag/access policy pass |
| Approved C6B42327…5D7D9DC download | Pass; Program/download/Run, SDK log, exact source read-back/access, identity/fault/keyswitch guards |
| Candidate captures | Ten exact path/type/value comparisons pass; configuration capture six fails before comparison |
| Failure | Equal positive even entire-scan generation could not be held within 100 attempts/five seconds; 95 complete read windows and five initially odd samples |
| Read plan | Four connections; 47 requests: 42 native fragments and five MSP batches; complete coverage, no skipped field |
| Full candidate fixture | Incomplete: zero inherited final rows; partial Access/config operation walk only |
| Cleanup | Candidate input/policy cleanup reports restored; automatic hash-checked genealogy rollback and access audit pass |
| Baseline fixture | All 31 regressions pass; documents/policy restored |
| Final readiness | Run/not faulted/Remote/scanning; MANUAL=1/idle/logout; not restoring; all five saved/live documents and original policy/preflight equal |
| Final S3h generic/idle read, 20-sample scan and complete coverage | Skipped after candidate failure; remain open |
| Capacity | Prepared exact-image automatic gate remains 79%: 2,501,720 / 644,008 / 3,145,728 used/available/total Blocks |
| Fault clear / clock change / commit / push | None |

The observer caught one reference callback defect before download: `canonical`
is a Boolean selecting old/new D2 bounds, not a document. Occupied host Count
now comes from the independently bracketed owner, including the held sample
after warm-up. Two targeted callback regressions were added. Current-source
gates pass: 2,140 AB tests (272.948 s), 74 root tests and 13 focused tests;
specification/contracts/strict consistency/whitespace also pass. Regeneration
is byte-identical to the approved PLC source and ACD, so both v38 compiler/
read-back/access proofs still apply. Those historical preparation payloads
remain unchanged. The reference and its tests are the only pre-download source
corrections; all 157 source bindings stay unchanged during native execution.

Successful capture attempts range from one to 67. The failed capture records
all 100 attempts; no same-state proof, value result or type result is invented.
No validation budget, task period, physical bound, feature or provider contract
was relaxed. The next engineering task is to reduce read-only transport latency
before proposing a fresh exact-image session. Native root/definition/alarm
metadata sizes from the successful captures are 133,744 / 7,308 / 16,616 bytes,
157,668 total. These partial measurements are not a complete S3h acceptance.

Prepared source SHA-256: `{v['sourceSha256']}`.
Approved ACD SHA-256: `{v['preparedAcdSha256']}`.
SDK-saved spent ACD SHA-256: `{v['sdkSavedAcdSha256']}`.
Fresh backup SHA-256: `{v['backupAcdSha256']}`.
The immutable genealogy original remains hash-pinned and was never opened;
rollback used its hash-checked copy. Credentials and native ACD binaries are
not archived.

Work folder: `{R.as_posix()}`. Payload:
[manifest](AB_S3H_CANONICAL_ATTEMPT_2026-10-23/manifest.json). Logs, exit codes,
all ten successful and the failed capture, 100-attempt history, source bindings,
current approval, baseline results and final readiness are preserved. V2 stays
inactive. Physical/CIP Security and later stages remain separate gates.
'''
with (AB/'Evidence/AB_S3H_CANONICAL_ATTEMPT_2026-10-23.md').open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(recorded=True,stageAccepted=False,passingPairs=10,baselineRows=31,genealogyRestored=True,authorizationConsumed=True)))

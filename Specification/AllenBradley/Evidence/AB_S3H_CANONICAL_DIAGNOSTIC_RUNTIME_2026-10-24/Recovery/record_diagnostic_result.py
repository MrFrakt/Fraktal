from pathlib import Path
import json
R=Path(__file__).parent;AB=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
NAME='AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24'
v=json.loads((R/'diagnostic_session_closure_01.json').read_text())
assert v['passed'] and v['candidateDownloadSucceeded'] and not v['stageAccepted']
summary=f'''**Latest, 2026-10-24: Echo recovery and S3h diagnostic download succeeded;
S3h stops at the unchanged coherence gate. Genealogy is restored.** The owner's
current “retry download on echo” instruction resumed the unused diagnostic
scope. Exact identity/service/listener/Remote/no-fault checks passed, but the
genealogy preflight refused a missing manifest. Two raw Symbol reads proved an
empty RemoteProgram controller. A separate empty-only helper restored a
hash-checked copy of the already-approved genealogy ACD, ran all 31 baseline
checks and re-entered the original preflight/backup/S3h driver without changing
its guards. The recovery helper initially lacked SDK FtspAdapter.exe and
stopped before download; the exact existing SDK dependency was added and the
failed log retained. Seven authorization cases and warning-clean build pass.

The C6 S3h download, SDK audit, read-back and access audit pass. The instrumented
fixture independently replays **64 exact pairs**, with 30 candidate checks
passing, one SFC `abort` check failing at acquisition, and 10 checks not reached.
The failed proof uses all 100 allowed polls in 267.188 ms: 38 unchanged-even
waits, 46 odd polls and 16 complete windows. Five close in the next odd
generation (+1); eleven close after the next even commit (+2). Wire windows
are 7,975.6 / 9,838.55 / 15,090.6 µs min/median/max; opening-to-closing spans
are 8,690 / 10,649.35 / 15,870.6 µs against the 10 ms task period. Immediately
after failure both TASK mirrors report LastScan 1,065 µs, cumulative max
8,402 µs and zero overlaps. This sample is not per-window task timing or the
missing final 20-sample candidate scan gate. No accepted pair mismatches a
value or type; mixed-generation bytes stay unaccepted.

Candidate cleanup, strict hash-checked genealogy rollback/read-back, all 31
final baseline checks, MANUAL normalization and final readiness/preflight
pass. Final baseline native timing is 99 µs median, 1,167 µs cumulative max,
zero overlaps (20 samples). Total recorded checks this continuation are 93:
92 pass, one candidate fails; these include the separate initial 31-check
recovery. No emulator crash, new native dump, hard kill, fault clear, clock
change or service/power toggle occurred. The session approval is consumed.

The owner's reverse-engineering report and final Ghidra log now explain the
libComms +0x50C2A4 NULL dereference on the expected-length I/O error-logging
path. The report attributes its startup trigger to corrupted power-down state
after the earlier forced shutdown. This session corroborates the instruction/
logging-call chain and matching binary hash; it does not reproduce that
corruption. Keep orderly shutdown after faults and inspect controller dump
folders before a later reboot. No vendor binary/state-file patch is applied.
Read [diagnostic runtime and recovery evidence](Evidence/{NAME}.md).
All 159 source and two wrapper bindings stay exact. S3h remains incomplete and
V2 inactive; the next blocker is reliable read-coherence timing. No commit/push.

'''
brief=f'''**Latest, 2026-10-24: Echo is recovered and the S3h download succeeded;
the diagnostic fixture stopped at SFC `abort` coherence.** There are 64 exact
independent pair replays, 30 passing candidate checks, one failed acquisition
and 10 checks not reached. The original 100-poll/five-second rule is unchanged.
Genealogy rollback/read-back, all 31 baseline checks, final readiness and saved/
live document equality pass. No new native dump or controller fault occurred.
The session approval is consumed; S3h is incomplete and V2 inactive. Continue
from [diagnostic runtime evidence](Evidence/{NAME}.md) and plan §2. The external
reverse-engineering report/log are preserved there; prefer orderly shutdown
after faults and inspect controller dump folders before a later reboot.
No hard kill, fault clear, clock change, vendor patch, commit or push.

'''
for filename,anchor,addition in (
    ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n',summary),
    ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n',brief),
    ('AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','# S3h preparation: Part, host events, identity and signal tower\n\n',brief)):
    p=AB/filename;text=p.read_text(encoding='utf-8');assert text.count(anchor)==1 and NAME not in text
    old='**Latest, 2026-10-24:';assert text.count(old)==1
    text=text.replace(old,'**Earlier post-reboot observation, 2026-10-24:',1)
    p.write_text(text.replace(anchor,anchor+addition,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';document=json.loads(p.read_text());assert not document['active']
document['approvedTraceabilityCorrection'].update(
    diagnosticPrepared=False,diagnosticControllerChangesAuthorized=False,
    diagnosticSessionApprovalConsumed=True,diagnosticNativeDownloadAttempted=True,
    diagnosticBlockedByClosedExternally=False,diagnosticBlockedByEmulatorStartupCrash=False,
    currentBaselineReadinessVerified=True,controllerRecoveredAfterExternalColdBoot=True,
    diagnosticRuntimeEvidence='Evidence/'+NAME+'.md',diagnosticCandidateDownloadSucceeded=True,
    diagnosticCandidateChecksPassed=30,diagnosticCandidateChecksFailed=1,diagnosticCandidateChecksNotReached=10,
    independentPartialReplays=64,diagnosticFailure='SFC abort acquisition: unchanged 100-poll same-scan gate',
    initialRecoveryBaselineChecks=31,diagnosticRollbackBaselineChecks=31,
    diagnosticNewNativeDumps=False,diagnosticCoherenceGatePassed=False,
    reverseEngineeringReport='Evidence/'+NAME+'/Recovery/Reference/echo_crash_re_2026-10-24.md')
p.write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')
report=f'''# Echo recovery and S3h instrumented diagnostic session — 2026-10-24

**The download retry succeeded; S3h acceptance did not. Genealogy is restored
and ready.** Exact controller 601FC87B / 127.0.0.1 / slot 0 / v38.011 was
reachable again, RemoteProgram/Remote and not faulted. Its normal genealogy
manifest guard refused; two successful raw Symbol lists were empty. The
original diagnostic preflight was preserved.

The current owner instruction “retry download on echo”, together with the
recorded unused diagnostic approval `call_b76d12f2f038411386f83c339fcd94e0:0`,
was used to restore the already-approved genealogy source to that verified
empty controller. This follows the separately qualified S2 empty-only recovery
pattern; it does not manufacture a candidate deployment sentinel or authorize
replacement of an unknown/nonempty project. The helper rechecks the exact
identity, no-fault, RemoteProgram and two empty raw lists immediately before
download. It opens only a hash-checked copy of genealogy D67561C4…4084; the
original ACD is never opened. Its owner Capacity baseline remains 720,352 /
3,145,728 Blocks. Seven authorization cases pass; its build has zero warnings
and errors. The first SDK launch lacked FtspAdapter.exe and failed at Open
project before any controller operation; the existing SDK's exact adapter was
added, and the failed log/copy remain. Recovery download, SDK log gate,
read-back/access audits, five-document restoration, all 31 baseline checks
and final checks passed. The unchanged S3h driver then required fresh preflight,
backup and backup-policy audit before the candidate.

| Result | Measured scope |
|---|---|
| S3h prepared image | C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC |
| Candidate download / SDK audit / read-back / access audit | Pass / pass / pass / pass |
| Candidate checks | 30 pass, one SFC abort acquisition fails, 10 not reached |
| Paired captures | 64 exact native-byte independent replays; one failed coherence proof |
| Recovery baseline / final rollback baseline | 31 / 31 pass |
| Total recorded checks this continuation | 93: 92 pass, one candidate fails |
| Candidate Capacity | Exact-image reuse: 2,501,720 used / 644,008 available / 3,145,728 total Blocks (79%) |
| Native record payload | 133,744 + 7,308 + 16,616 = 157,668 bytes, measured from actual Templates/raw records |
| Final baseline TASK sample set | 20 samples; 99 µs median, 1,167 µs cumulative max; zero overlaps |
| Final state | Run, no controller fault, Remote, scanning, MANUAL/idle, logged out, not restoring; policy/preflight and five saved/live documents equal |
| New native dumps / hard kills / fault clears / clock changes | 0 / 0 / 0 / 0 |

The 30 successful candidate checks comprise 20 inherited base rows, two Access
rows and eight configuration rows. The failed SFC abort base row is recorded
with passed=false; it is not counted as successful. Initial recovery and final
rollback are distinct 31-row baseline runs. These counts do not establish the
planned complete 41-candidate / 31-final-baseline stage exit.

## Acquisition finding

The final diagnostic window contains 100 original poll attempts: 38 unchanged-
even waits, 46 odd generations and 16 full read windows. All waits count toward
the unchanged limit. The proof stops after 267.188 ms because the poll count
is exhausted, within the unchanged five-second time ceiling. There are 116
generation reads, including the 16 closing reads. Five complete windows close
in the next odd generation (delta +1); eleven close at the next even commit
(delta +2). None satisfies equal-positive-even generation, so none of those
raw frames is accepted or compared as a canonical snapshot.

| Timing, µs | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Four-socket wire acquisition | 7,975.6 | 9,838.55 | 15,090.6 |
| Opening-read start to closing-read end | 8,690.0 | 10,649.35 | 15,870.6 |

The generated periodic task remains 10 ms. Immediately after failure, before
the inherited fixture cleanup, all eight existing TASK mirror reads succeed:
both owners show Scan/Samples 17,121, LastScan 1,065 µs, cumulative MaxScan
8,402 µs and OverlapCount zero. This is one post-failure observation, not a
per-window CPU trace. It establishes neither a task overrun nor the missing
final 20-sample candidate timing gate. The recorded read/closing spans leave
insufficient reliable margin for the existing proof; they do not justify
increasing budgets, changing the task period, accepting mixed generations or
loosening value/type comparisons.

The wrapper adds bounded clock/list bookkeeping inside acquisition and writes
gzip evidence afterward. Results are instrumented. The 64 successful captures
re-decode and independently reconstruct the owner/provider oracle exactly,
including finite approved Core type/value corrections. Their successful proof
attempts range from 2 to 79. The failed raw frames are explicitly unaccepted.
The first analysis report floor-divided generation deltas and labelled five
odd closes as zero scan deltas. Its corrected revision records exact deltas
and parity; both versions are retained, and revision 2 governs this report.

## Vendor crash diagnosis and operational rules

The owner supplied
`C:/Users/SoftIndVM/Documents/ReverseEngineerAgent/notes/studio5000/echo_crash_re_2026-10-24.md`.
Its SHA-256 is fc656498f4053b619de3069ac23d6e28797c83fa5bfb398cf45605f0014a3ccf.
The final Ghidra log and installed libComms hash bind the same v38.011 module
as the earlier dumps. Inspection corroborates the faulting CMP through ESI at
RVA 0x50C2A4 and the expected-length I/O failure's call to the record writer
through the trace-context global. The report identifies an unguarded NULL
trace-context dereference and attributes the short startup restore I/O to
power-down state corrupted after the earlier forced shutdown. This session
did not reproduce the corruption or apply a vendor-binary patch.

The report and final Ghidra log are preserved as text references. Neither the
native memory dumps nor the power-down state or credential files are copied
into this evidence. The owner's external cold-boot script is not executed by
this session. Our two raw empty lists establish the actual live state observed
after that external recovery; the baseline was reloaded before S3h.

Preserve the owner's operating rule: prefer orderly shutdown after a controller
fault; avoid hard-killing the emulator/service, and inspect controller dump
folders for new dumps before a later reboot. The external report explains that
leftover dumps can slow subsequent service starts. The SDK wrapper's initial
missing-file exception is distinct from a native emulator crash. No native
dump existed before the candidate or after final rollback in this session.

## Validation and remaining boundary

The fresh full AB suite passes 2,149 tests. All 74 root tests, specification,
frozen-contract, strict consistency and whitespace checks pass in the attached
new logs. All 159 project and two wrapper source bindings remain exact. Both
v38 build/read-back and Capacity gates are reused by exact source/pristine
prepared-image hashes; no PLC or HMI source changed. Flutter is not applicable.
All 38 predecessor records / 8,615 artifacts are re-hashed unchanged by the seal.

The complete candidate matrix, all-rendition/88-pair trace exit, final generic/
idle acquisition and final 20-sample candidate timing were not reached. S3h
remains incomplete and frozen V2 inactive. The current session approval is
consumed. Next work is reliable acquisition within the unchanged coherence
proof, using these timing records. Another controller-changing session needs
its own current scope; fault clears and clock changes remain excluded.

Recovery work: `{R.as_posix()}`. Diagnostic native run:
`C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb`.
Append-only [payload manifest]({NAME}/manifest.json). Failed runs are retained.
No commit or push.
'''
with (AB/'Evidence'/(NAME+'.md')).open('x',encoding='utf-8') as out:out.write(report)
print(json.dumps(dict(recorded=True,controllerRecovered=True,candidateDownloadSucceeded=True,stageAccepted=False)))

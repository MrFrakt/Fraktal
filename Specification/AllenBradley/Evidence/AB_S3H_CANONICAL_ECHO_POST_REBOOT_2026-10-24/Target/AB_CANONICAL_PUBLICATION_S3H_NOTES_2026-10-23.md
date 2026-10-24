# S3h preparation: Part, host events, identity and signal tower

**Latest, 2026-10-24: the owner rebooted Windows; the virtual controller
still crashes during startup.** Echo service is Running, but 601FC87B remains
ClosedExternally with no emulator/CIP listener. The fresh dump repeats the
same libComms.dll exception and frame offsets. This continuation was read-only;
the existing diagnostic approval remains unused. Current baseline readiness
is unverified, S3h incomplete and V2 inactive. Continue from the
[post-reboot evidence](Evidence/AB_S3H_CANONICAL_ECHO_POST_REBOOT_2026-10-24.md) and plan §2; another power/reset/
recreation operation needs its own authorized scope. No commit or push.

**Earlier, 2026-10-23: authorized Echo restart failed during emulator startup.**
The one-shot approval `call_37bd66c3442340b08084fd7b2deb2ce5:0` was used:
IsEnabled false applied; re-enable was requested and the native emulator
exited with code 1. The service remains Running; controller 601FC87B remains
enabled/ClosedExternally, RemoteProgram/Remote, not faulted, with no CIP
listener. No PLC download, tag write, mode command, fault clear or clock
change ran. The original S3h diagnostic approval remains recorded and unused.

Fresh native crash metadata records 0xC0000005 in v38.011 libComms.dll at
offset 0x50C2A4, with exception parameters [0, 0]. The x86 frame chain stays
in libComms before runtime-library thread frames. Private vendor symbols are
unavailable; the underlying cause remains unconfirmed. Earlier service logs
also record an emulator shutdown timeout/forced close and the same startup
exit before this authorized attempt. Controller definitions/state files stay
in place. The full memory dump is not archived; only metadata/control-address
stack frames and selected logs are recorded.

Rockwell's Echo 4.00 release notes describe an initialization issue for which
a Windows-host reboot is recommended. That is a possible next recovery step;
ASLR is unconfirmed here. Read [restart result](Evidence/AB_S3H_CANONICAL_ECHO_RESTART_2026-10-23.md).
S3h remains incomplete and V2 inactive; no further restart is authorized by
the consumed one-shot approval. No commit or push.

**Earlier restart preparation: the virtual controller was
ClosedExternally.** Read-only SDK metadata identifies the exact 601FC87B /
127.0.0.1 / slot 0 / v38.011 controller, enabled, RemoteProgram, Remote,
not faulted. The emulator process and 44818 listener are absent. SDK loaded-
project/path strings are empty; that does not prove the persisted PLC image
is empty while the emulator is unavailable. No new controller change ran.

A separate one-shot disable/re-enable helper is prepared and compile-clean.
Six offline authorization cases pass. It verifies exact identity/GUID/firmware/
slot/Remote/not-faulted and the reviewed ClosedExternally/RemoteProgram state
immediately before use, and refuses if an emulator/listener appears. It changes
only IsEnabled false then true, through the public SDK. It does not download,
change keyswitch/mode, clear a fault or set a clock. This added restart needs
current explicit approval under AGENTS.md §3a; its approval template is false.
The original diagnostic approval remains recorded and unused. After restart,
normal identity/session/document guards run; an unverified baseline stops
before any diagnostic download. Read
[restart preparation](Evidence/AB_S3H_CANONICAL_ECHO_RESTART_PREPARATION_2026-10-23.md). S3h is incomplete; V2 stays inactive.

**Earlier diagnostic preflight: Echo service was stopped.**
The owner approved `call_b76d12f2f038411386f83c339fcd94e0:0`, “Approve this
guarded S3h diagnostic session”. The resumed service/identity guards refuse:
FactoryTalk Logix Echo Service is Stopped, there is no 44818 listener, and
this process is not an elevated Administrator. No upload, download, mode
change or tag write ran. The prepared C6 ACD and diagnostic source pins still
match; no deployment sentinel or backup artifact exists. Current approval
remains recorded and unused; it is not being requested again.

The initial command orchestration continued after the first failed guard.
The backup helper independently refused before upload; all four failed logs
are retained. The replacement runner checks each return code and stops before
starting the next dependent phase. Owner action is the handover's documented
elevated `Start-Service "FactoryTalk Logix Echo Service"`. Once service is
back, fresh exact-identity/fault/keyswitch/HMI-session/document guards run again.
Fault clears remain excluded. Read
[service preflight](Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_SERVICE_PREFLIGHT_2026-10-23.md). S3h/V2 acceptance is unchanged.

**Earlier active-workload S3h diagnostic preparation;
current authorization pending.** The failed paced retry is sealed: 39 exact
independent replays, first HELD coherence failure, successful rollback and all
31 baseline regressions. Larger message requests do not offer a useful path:
4,000/4,002 bytes connect; 8,000/16,000/60,000 are refused. An immediate-send
event-loop prototype does not establish a reliable latency gain and is not
in the implementation. No production reader/observer/PLC source changed.

A separate guarded wrapper now records per-window and generation-read timing,
keeps the last attempted raw frames explicitly unaccepted, and reads the eight
existing native TASK mirror scalars after an acquisition failure, before the
inherited fixture cleans up. It preserves the exact original exception,
100-poll/five-second history, four sockets/one pending request, comparisons
and all existing 41 candidate vectors. Evidence compression/writes happen
after the proof. Timing calls/in-memory rows add small observer overhead;
the native result will be labelled as instrumented diagnostics. Four wrapper
tests pass, including authorization refusal and error/history preservation.

All 159 existing source bindings remain exact, so their 2,149 AB / 74 root
tests and exact-image two-target v38/79% Capacity proofs apply. A fresh C6
image/helper is ready; fresh read-only baseline checks pass. No new native
write is authorized or performed. Proposed scope is the same guarded backup,
C6 download, inherited candidate fixture with diagnostics, and hash-checked
genealogy rollback/31 baseline checks/final cleanup. Failure still stops the
fixture and triggers rollback; there is no extra retry loop or acceptance claim.
Read [diagnostic preparation](Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23.md). V2 stays inactive;
fault clears, clock changes, commit and push remain excluded.

**Earlier paced S3h retry stops at active HELD coherence;
genealogy is restored.** All 39 Access/configuration captures compare and replay
exactly from native bytes and independently reconstructed owner/provider contexts.
The two Access and eight configuration cases pass, but the first HELD capture
fails before comparison: 100 polls contain 77 unchanged-even waits, six odd
polls and 17 complete read windows; every window crosses one scan boundary.
Pacing removed the earlier tight-poll starvation but did not establish active
workload timing. The 1,000 baseline proxy passes do not transfer to this active
HELD state. No path, type or value mismatch was observed in an accepted pair.

Candidate cleanup, hash-checked rollback, all 31 baseline regressions, strict
rollback read-back and final Run/not-faulted/Remote/scanning, MANUAL=1/idle/
logout/not-restoring, five saved/live documents and original policy/preflight
equality pass. All 159 sources remain unchanged; 2,149 AB / 74 root tests and
the exact-image compiler/79% Capacity proofs still apply. The current session
approval is consumed. No fault clear, clock change, commit or push occurred.

S3h remains incomplete. Complete inherited/active/traceability checks, generic
idle acquisition and candidate TASK timing were not reached. No accepted
Capacity calibration sample is added; V2 stays inactive. The next task is to
reduce and instrument active-workload acquisition latency, keeping the same
100-poll/five-second positive equal-even proof. Read
[paced retry attempt](Evidence/AB_S3H_CANONICAL_PACED_RETRY_ATTEMPT_2026-10-23.md). No further download is authorized.

**Earlier paced S3h retry preparation (attempt completed above):**
The prior retry is sealed with genealogy restored and all 31 baseline checks
passing. Its failed capture spent 93/100 polls waiting for a fresh generation.
The observer now waits one millisecond after an unchanged even generation.
Every poll and wait remains inside the same 100-attempt/five-second gate;
the next iteration checks the deadline before another read. Closing positive
equal-even proof, four connections, one pending request each, all 47 packets,
post-window decoding, PLC image and candidate stimuli are unchanged.

The installed four-connection observer passes 1,000 consecutive read-only
baseline proxy captures in 2–54 polls.
These use the legacy scan counter and immutable payloads and do not establish
S3h canonical acceptance. An eight-connection experiment showed similar median
latency; it is retained as an experiment and is not shipped. All 2,149 AB tests
(276.776 s), 74 root tests and strict cheap gates pass. The 159-file source
closure differs only in the pacing implementation and its test. Regeneration
is byte-identical to source E83B9A2C…567315 and ACD C6B42327…5D7D9DC, so the
existing two-target v38 compiler/read-back/access and 79% automatic Capacity
proofs apply. A fresh one-shot helper builds with zero warnings/errors.

Fresh read-only preflight/readiness checks pass on restored genealogy. No new
download, mode change or tag write is authorized or performed. The next native
scope remains fresh backup, this exact image, 41 candidate checks/read-only
equivalence and scan, genealogy rollback and 31 baseline checks/final cleanup.
Fault clears and clock changes remain excluded. S3h remains incomplete and V2
inactive; no commit or push. Read
[paced retry preparation](Evidence/AB_S3H_CANONICAL_PACED_RETRY_PREPARATION_2026-10-23.md).

**Earlier guarded S3h retry failed the coherence gate;
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

**Earlier S3h retry preparation (attempt completed above):**
The failed attempt remains sealed and genealogy remains restored. A qualified
read-only observer now multiplexes four sockets with one pending request each,
and starts acquisition on a newly completed generation. Every waiting poll
counts against the original 100 attempts/five seconds. The closing equal-positive-
even proof, complete byte coverage and post-window decoding are unchanged.
Twenty baseline timing-proxy captures pass in 4–32 polls, with identical bytes;
these are transport diagnostics, not S3h canonical acceptance.

All 2,148 AB tests (270.165 s), 74 root tests and the focused transport/
scan-start tests pass. The source closure binds 159 files. Source L5X and ACD
are byte-identical to the original qualified S3h image: `C6B42327...5D7D9DC`.
Both v38 build/read-back/access and automatic Capacity (79%) gates are reused
by exact hash. A fresh one-shot helper/workspace is ready; no retry controller
operation is authorized. Next requires current approval for backup, this exact
download, 41 candidate checks/read-only captures, genealogy rollback and 31
baseline checks. No fault clear, clock change, commit or push. V2 remains inactive.
Read [retry preparation](Evidence/AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23.md).

**Latest, 2026-10-23: S3h native attempt stopped at the coherence gate;
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

The owner approved the 36 finite type corrections and dependent offline work
on 2026-10-23 (`call_f7da50b3655c43e4be6d7145b8b02c9b:0`). No native S3h
operation is authorized. Read the [approved review](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md)
and [preparation evidence](Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23.md).

The implementation adds 278 consumed legacy paths: Part 40, HostEvents 220,
Nameplate 10, SignalTower seven and MachineState one. All 278 frozen values
match executed generated ST and the independent legacy-owner reference.
Only the enumerated 36 types change: sixteen UInt32 sequences, three Int16
ring counters, seventeen DateTime stamps; unset Part Stamp becomes zero.
Other 242 values/types, consumed bounds and existing owners remain exact.

Versioned S3h records mirror committed Part/genealogy/event storage. The Part
and event caches invalidate by revision/epoch and first scan; the append-only
model-catalog count also invalidates event value lookup. LREAL operands widen
before scale division, with typed Decorated LREAL definition initializers.
One qualified calendar routine converts stored UTC dates/clocks into native
LDT nanoseconds. Historical parents and resource text come from captured
event storage. Empty result/parent slots clear; no historical data comes from
the current Part. PLC Count selects occupied physical event slots. The same
existing service owns MachineState and all seven SignalTower outputs.
Declared nameplates are initialized in PLC records at Core widths, including
the fixture's quote/dollar/CDATA-ending identity text.

Eleven focused tests cover empty/partial/full/wrapped rings, epoch reset,
captured resource text and signed numeric limits, model values, exact Double
1/3 and 1.001 scaling, timestamps, result/parent clearing, fail-closed bounds/
ASCII, indication mirrors and the finite path/type list. The full AB suite
passes 2,138 tests in 277.202 s; root tests pass 74. Both v38 build/read-back/
access gates and the prepared ACD read-back pass. Eight prior stage image pins
and sealed snapshot replays remain unchanged; 157 source files are bound.

Automatic Studio Capacity is 2,501,720 / 644,008 / 3,145,728 used/available/
total Blocks (79%), +94,520 over accepted S3g. The advisory calibrated estimate
was 2,501,330 Blocks. The pending image is not added to accepted calibration.
ACD SHA-256: `C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC`.
Generated L5X SHA-256: `E83B9A2CD9593718026528CCDBD83A1EAD6C8A52948FC6616006DAFFB0567315`.

Failed runs remain append-only: the initial focused model stopped at BOOL
comparison; a temporary interpreter workaround was removed after the native
compiler rejected that comparison. Final ST validates numeric owner flags.
The first native import also found three identifiers longer than 40 characters;
shorter generated identifiers and a boundary test correct it. The first full
suite found one stale test treating newly approved stage 10 as invalid; stage 11
is now the explicit first unsupported stage. Final full tests pass.

Fresh baseline read-only checks pass. S3h native equivalence, record sizes,
TASK scan, rollback and 41+31 regression checks await current authorization.
The equal-positive-even generation proof remains 100 attempts/five seconds.
V2 stays inactive. No HMI change, controller write, fault clear, clock change,
commit or push occurred in this preparation.

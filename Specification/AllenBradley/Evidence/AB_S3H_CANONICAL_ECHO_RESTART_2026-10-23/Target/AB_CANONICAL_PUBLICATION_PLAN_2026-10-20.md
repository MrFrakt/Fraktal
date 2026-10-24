# Fraktal/AB canonical publication — implementation plan

Non-normative plan, 2026-10-20. It executes the decisions in
[AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md](AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md)
(D1–D9). Where the two differ, the design note's decisions win and this plan is
corrected. Part III stays authoritative until a stage amends it.

## 1. Goal and definition of done

AB reaches the HMI the way TC3 and TIA do:

- the PLC publishes the canonical Core module tree;
- one generic session client discovers it through the controller's own Symbol
  and Template objects plus the manifest, with no station declaration at
  runtime.

The work is done when **all** of the following hold:

1. **Value equivalence.** A generic reader recovers every canonical path the
   Python projection serves today, with identical values and types. The only
   exceptions are the five D2 array-bound corrections and the explicitly
   versioned [owner-approved S3f corrections](AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md):
   the 110 enumerated Core types, bounded page windows, 12 missing Core fields,
   PLC-owned revision/timestamps and validated provider responses. The owner also
   approved the [200 S3g numeric corrections](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)
   on 2026-10-23, including exact Core Float32 arithmetic and UInt32 bucket wrap. The
   [224 dependent value paths](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md)
   are also approved: 64 OEE validity flags and 160 profiler row values. No general
   numeric coercion, ignored path or tolerance is permitted. The owner also approved
   the [36 S3h type corrections](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md),
   including unset Part timestamp empty string to zero; the other 242 added paths
   retain exact values and types. The frozen genealogy
   capture (4,437 legacy paths) stays immutable; page-window shape and additional
   Core fields have their own explicit S3f oracle. This holds for genealogy and
   the press declaration in all three AUTO renditions.
2. **Desktop.** The desktop HMI connects with `cip://<controller>` through a
   generic `CipSessionClient` in `fraktal_opcua_client`. It is read-only unless
   the target has a commissioned CIP Security policy (D9).
3. **Web.** The Dart gateway serves Web clients from the same client
   (`--plc-endpoint cip://…`), with Core §14 writes over `wss://`.
4. **Retirement.** The Python projection, the Python gateway and the Dart
   spike (`HMI/lib/data/cip/`) are removed. §3.8b persistence, configuration
   sets and the host-event sink have new owners (S6). The old generated
   contexts are gone, and the canonical structures are the working storage.
5. **Documents.** Part III, frozen contracts V2, `OPCUA_TRANSPORT.md`,
   `AGENTS.md`, the AB README and the new-station guide describe the final
   behaviour. Every gate is green.
6. **Acceptance.** Echo acceptance passes per stage; physical and CIP Security
   acceptance pass on a v37+ capable controller (S7).

## 2. State at hand-over (2026-10-20)

**Latest, 2026-10-23: authorized Echo restart failed during emulator startup.**
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

**Earlier S3h native attempt stopped at the coherence gate;
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

**Earlier S3h offline preparation (native attempt recorded above):**
The owner-approved 36 type corrections and unset Part stamp correction are
implemented with 278 additional consumed paths. The emitted ST and independent
reference reproduce all 278 frozen genealogy values exactly. Eleven focused
tests, 2,138 AB tests (277.202 s), 74 root tests, both v38 builds,
strict read-backs/access and specification/contracts/strict-consistency pass.
All eight prior accepted images and sealed generic snapshots remain exact;
the generic reader is unchanged. The source closure binds 157 files.

Prepared ACD `C6B42327...5D7D9DC` has automatic Studio Capacity of
2,501,720 used / 644,008 available / 3,145,728 total Blocks (79%),
+94,520 over accepted S3g. No capacity figure was requested from the owner.
The empirical forecast was 2,501,330 Blocks; it remains advisory. With a full
host ring, expected page totals are 3,950 / 3,900 / 3,550. Empty/partial rings
retain only their occupied physical paths, from the PLC Count. Cumulative
legacy inventory is 4,288 of 4,437, leaving 149 paths for later stages.

Fresh read-only checks confirm genealogy is still Run/not faulted/Remote/
scanning, MANUAL=1/idle/logout/not-restoring; five saved/live documents and
policy/preflight match. S3h has not been downloaded. Native equivalence,
record sizes, scan and rollback remain open; the whole-scan gate stays
100 attempts/five seconds. Next is separate current authorization for this
exact image, inherited 41 candidate checks, read-only traceability captures,
genealogy rollback and 31 baseline checks. No fault clear, clock change,
commit or push is authorized. V2 remains inactive. Read
[S3h preparation evidence](Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23.md).

**Earlier, 2026-10-23: S3g exit passes on Echo.** All 83 planned checks
pass on their first runs: 41 candidate cases, nine OEE boundary vectors, two
profiler high-bit vectors and 31 restored-genealogy regressions. All 88 paired
captures replay exactly from native bytes and independent provider/metric
references, at 3,672 / 3,622 / 3,272 paths/types. The unchanged whole-scan proof
accepts in 1–75 attempts within 100 attempts/five seconds. All 151 prepared
sources, including the PLC/image and generic reader, are unchanged; their
2,127 AB and 74 root tests remain bound to the preparation seal.

Automatic Capacity is 76%: 2,407,200 used / 738,528 available / 3,145,728 total
Blocks, +108,752 over accepted S3f. Native root/definitions/alarm metadata total
145,084 bytes (121,160 / 7,308 / 16,616). Candidate scan median/max is
868 / 5,273 µs; restored genealogy 99 / 1,168 µs; zero overlaps. These are Echo
observations under different workloads, not isolated publication costs.

Genealogy is restored: Run/not faulted/Remote/scanning, MANUAL=1/idle/logout,
not restoring, all five saved/live documents and policy/preflight equal. No
fault clear or clock change occurred. This exact session authorization is
consumed. V2 remains inactive; no commit or push. Read
[S3g runtime evidence](Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23.md).
S3h offline preparation is now complete as recorded above; further controller
changes need separate current approval.

**Earlier S3h inventory (2026-10-23):** 278 added legacy paths bring
cumulative coverage to 4,288, leaving 149. The [contract review](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md)
enumerates 36 Core type corrections: 16 UInt32 event sequences, three Int16
ring counters and 17 DateTime stamps. The unset Part timestamp would change
from the legacy empty string to canonical zero within that same list; all
242 other added paths stay exact. Existing AB genealogy/delivery extensions,
append/epoch/measurement/tower owners and consumed bounds stay unchanged.
The owner approved these finite corrections and dependent offline work on
2026-10-23 (`call_f7da50b3655c43e4be6d7145b8b02c9b:0`). S3h offline implementation now passes the preparation gates above;
no S3h controller-changing operation is authorized. All 151 accepted S3g sources and 26 seals / 6,059 artifacts verify
unchanged. Read [S3h inventory evidence](Evidence/AB_S3H_CANONICAL_INVENTORY_2026-10-23.md).

**Earlier S3g offline preparation, 2026-10-23 (session completed above):** both approved amendments
are implemented: 200 Core numeric types and 224 dependent values, with exactly
1,055 additional consumed paths. The independent Core Float32/UInt32 reference
and actual emitted ST pass 13 focused tests, 2,127 full AB tests (291.415 s),
74 root tests, specification/contracts/strict-consistency and whitespace gates.
The complete image passes both v38 builds, exact read-back and access audits;
all seven accepted prior stage images and sealed capture replays remain exact.
The generic reader is unchanged.

Prepared ACD `CCE00F97...B4A6331` has measured automatic Studio Capacity of
2,407,200 used / 738,528 available / 3,145,728 total Blocks (76%), +108,752
over accepted S3f. Source `50E0F897...104DAE91` includes a separately generated
bench routine: nine first-scan OEE boundary vectors and two high-bit profiler
rows. The latter save/restore six fixed DINT owner cells in that same scan,
before normal publication. Results are read-only and outside the canonical tree.
No controller-changing operation is authorized or performed. Fresh read-only
checks pass on restored genealogy: Run/not faulted/Remote/scanning,
MANUAL=1/idle/logout/not-restoring, five documents and policy equal.

Next is current authorization for this exact image and the guarded S3g native
session: backup, Program/download/Run, 41 candidate regressions plus 11 native
boundary results, read-only 3,672 / 3,622 / 3,272-path equivalence/size/scan,
genealogy rollback and 31 baseline regressions/final checks. Native equivalence,
scan, hardware and CIP Security acceptance remain open. No commit or push.
Read [complete preparation evidence](Evidence/AB_S3G_CANONICAL_PREPARATION_2026-10-23.md).

**Earlier S3g schema checkpoint, 2026-10-23 (superseded above):** owner approval records the 200 numeric
corrections. The schema covers all 1,055 paths; native REAL/INT and the existing
UInt32 bit representation need no generic decoder changes. The schema and health
mapper pass both v38 compiler/read-back/access gates in an explicitly offline,
uncalled type/health probe. Four focused tests and 2,118 full AB tests pass;
S3f source still regenerates exactly B71E30AB...0AE7CF3.

Boundary analysis found 224 dependent value paths omitted by the type-only
allow-list: 64 OEE validity flags and 160 profiler row values. Their exact Core
counterexamples and [review draft](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md)
were approved by the owner on 2026-10-23 (question
`call_43d1f40d2efb4ab69d699df590f3c0bc:0`). The combined finite allowance is
424 paths: 200 numeric types and 224 dependent values. Full algorithms and
all complete-image gates remain required before deployment. No complete S3g deployment image,
exact-image Capacity, native equivalence/scan or session is prepared. The layout
forecast is advisory only. No controller access or changing operation occurred;
the last verified live image is restored genealogy from the S3f session.
Read [checkpoint evidence](Evidence/AB_S3G_CANONICAL_SCHEMA_2026-10-23.md).

**Latest, 2026-10-23: S3f exit passes on Echo.** The authorized revision
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
S3g offline preparation is described above; further native changes need their own current approval.

**Next stage, S3g inventory (2026-10-23):** 1,055 added legacy paths bring
cumulative legacy coverage to 4,010. Core declarations differ at 200 numeric
paths (64 Float, 101 UInt32, 35 Int16), including explicit OEE rounding/wrap
consequences. The [contract review](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)
was approved by the owner for contract/offline work on 2026-10-23. S3g
implementation is now in progress. No S3g controller operation is authorized.

**Completed session, 2026-10-23:** the authorized S3f runtime session passes
at its recorded scope: 31 inherited candidate rows, two Access checks, eight
configuration cases and 31 restored-baseline rows. All 88 paired captures replay
identically, including complete native fragments and independent provider
contexts. Pages contain 2,617 / 2,567 / 2,217 paths/types. The observer now balances
bounded fragment packets across two read-only connections inside the unchanged
100-attempt/five-second whole-scan proof (1-59 accepted attempts); the PLC image
and generic reader are unchanged. Two observer failures and a full repeat for
missing MANUAL policy observations remain archived (113 actual rows, 72 accepted).
140 current sources are bound; 2,108 AB tests and 74 root tests pass. See
[runtime evidence](Evidence/AB_S3F_CANONICAL_RUNTIME_2026-10-23.md). Genealogy,
Run/not faulted, MANUAL=1/idle/logout, five documents, policy and preflight are
restored. This exact session approval is consumed. S3f retained restart and
active-model native revision vectors remain open before its full exit; S3g is
not started. No commit/push or further controller operation is authorized by
the completed session.

**Prior preparation, 2026-10-23:** S3f offline implementation has both v38
compiler/read-back/access gates and a prepared ACD, pin A05695F1...E3EB66.
Automatic Studio Capacity passes at 73%: 2,298,412 used / 847,316 available /
3,145,728 total Blocks (+729,560 over S3e). Closing gates pass: 2,104 AB tests,
74 root tests, specification/contracts and strict consistency. The
[preparation evidence](Evidence/AB_S3F_CANONICAL_PREPARATION_2026-10-23.md) binds
138 sources and retains all failed runs. The [S3f notes](AB_CANONICAL_PUBLICATION_S3F_NOTES_2026-10-23.md)
and V6.3 wire draft describe bounded pages, corrected Core types and validated
PLC-held provider responses. The fixture prepares 31 inherited rows, two Access
checks and eight configuration cases, with 31 baseline rows after rollback.
Native equivalence/scan/rollback and current controller authorization remain
pending; the accepted live genealogy baseline is unchanged. No commit/push.

**Current continuation, 2026-10-20:** the corrected first S0 probe was downloaded
and measured, and genealogy restored with 31/31 regressions and passing final
checks. D6/D7 are selected in the design note. See
[runtime evidence](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md),
[V2 draft](AB_FROZEN_CONTRACTS_V2.json) and
[Part III amendment draft](AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md).
**Owner approved the target drafts on 2026-10-20: “Approve drafts and proceed
to S1”. The S1 reference-oracle exit now passes at its recorded scope.** See
[S1 evidence](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md).
The supplementary S0 runtime session completed on 2026-10-21 with owner
Capacity fit, exact 2 MiB fragmented reads, browse-name root, effective access,
precise LREAL vectors, 31/31 restored regressions and passing final checks; see
[supplementary evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md). The
following hand-over state is historical; its original probe was superseded by
[the corrected preparation](Evidence/AB_S0_CANONICAL_PROBE_PREPARATION_2026-10-20.md).

### Echo

- **Loaded image:** `fraktal_ab_genealogy_demo`, manifest
  `6DEC4C1DC2F7F78A`. Re-downloaded on 10-19 with 31/31 regressions; see
  [AB_ECHO_REDOWNLOAD_2026-10-19](Evidence/AB_ECHO_REDOWNLOAD_2026-10-19.md).
- **The Echo service fails to start at boot.** The host rebooted on 10-19
  20:38 and on 10-20 21:40, and both times the FactoryTalk Logix Echo Service
  timed out on start (Service Control Manager events 7009/7000). The service
  ACL lets only SYSTEM and elevated Administrators start it, so the owner must
  run `Start-Service "FactoryTalk Logix Echo Service"` from an elevated shell.
- **An HMI session was still logged in** (`echo_admin`, level 4) at the last
  check. The preflight refuses to download over an active session. Do not
  weaken that guard; ask the owner to log out.

### S0 (prepared, not downloaded)

- **Tools** (uncommitted):
  - `tools/fraktal_ab_s0_canonical_probe.py` — generator;
  - `tools/fraktal_ab_s0_canonical_measure.py` — read-only template decoder
    and measurement;
  - `tools/test_fraktal_ab_s0_canonical_probe.py` — 7 tests, passing.
- **Work folder:** `C:/work/fraktal-ab-s0-20261019/`.
  - The combined probe `combined/s0_combined.L5X` compiles on both v38 targets
    with equivalent read-back.
  - The prepared ACD `s0_probe.ACD` (SHA-256 `F7E54A1A…`) has equivalent
    read-back and a clean log.
  - `session/S0Session.exe` has the modes `prepare-probe` (done), `backup`,
    `deploy-probe` and `restore-genealogy`.
  - `scripts/preflight.py`, `scripts/guard_echo.py` and
    `scripts/probe_loaded.py` support the session.
- **Compiler facts already measured** (v38, offline SDK build):
  - A member named after a type (`Time`, `DT`, …) fails with
    `RxSTX_E_UNEXPECTED_TOKEN`.
  - Time literals must be normalised: `T#1500ms` fails and `T#1s500ms`
    compiles. The `TIME#` prefix fails.
  - `TIME32`, `LTIME`, `DT` and `LDT` declare.
  - Assigning a LINT into `TIME`/`DT`/`LDT` compiles.
  - ST has no `MOV` (`RxSTX_E_INVALID_FUNC`).
  - Studio canonicalises structured members to `Radix="NullType"`.
  - StringFamily widths up to 480 compile.
- **Runtime facts already measured** (Echo, read-only, 10-19):
  - Symbol/Template discovery returns member names, types, offsets and BOOL
    bit numbers.
  - The generic decoder matches the layout decoder on all 47 `FRK_Press_Unit`
    members.
  - StringFamily members are recognised by shape.
  - The golden projection capture is
    `C:/work/fraktal-ab-echo-20261019/projection_capture_01.json`
    (50 reads, 4,437 values, SHA-256 `5CA907E6…`).

### Uncommitted working tree

- The design note and this plan.
- The S0 tools and their tests.
- The 10-19 Echo evidence record.
- The removal of the CIP spike's hex-dump `print`s in
  `HMI/lib/data/cip/eip_cip_client.dart`.
- Pre-existing owner edits that are not this work: `.gitignore`,
  `AGENTS.md`, and the `.dart_tool` files under the Siemens archive snapshot.

## 3. Invariants for every stage

- **One source.** The declaration remains the only source; the generator emits
  the L5X. Hand-authored L5X is forbidden, and no station knowledge may enter a
  client.
- **Canonical paths.** Paths, leaf names, enum ordinals and logical types equal
  TC3's (`HMI_CONTRACT.md`, `HMI/lib/domain/types.dart`). Array indices follow
  each array's Core-declared bound (D2).
- **Published versus private.** Published members are External Access *Read
  Only*; only `HmiRequest` is *Read/Write*; private storage is *None*. The R6
  allow-list audit runs on every generated image.
- **Native types per D3–D7.** Never name a member after a type. Use
  normalised time literals.
- **Language parity.** ST/SFC/LD parity holds; the rendition gate and the 31
  regressions stay green.
- **Controller-changing operations.** Each needs the owner's **current**
  authorization, the exact identity guard immediately before use, a backup
  upload, and restoration with acceptance afterwards. Evidence is append-only
  under `Specification/AllenBradley/Evidence/`, including failed runs.
- **Budget.** Memory and scan time are measured per stage (Studio Capacity
  Estimate; native `TASK` `MaxScanTime`). The owner requested an automatic
  estimate on 2026-10-21; the [calibrated forecast](AB_CAPACITY_FORECAST_METHOD_2026-10-21.md)
  provides offline budgets. The qualified automatic Studio collector now
  supplies the exact offline Capacity values from a hash-checked review copy;
  it reproduced the owner's S3a values before measuring S3b. This replaces
  routine screenshot requests on the qualified L81E/v38 English setup, while
  preserving the measured gate. Forecasts remain advisory. No feature is cut
  and no validation weakened to make an image fit.

## 4. Stages

### S0 — Measure the type rules and draft contract V2 (target drafts approved)

Steps 1–3, 5 and 6's draft preparation have completed for the first probe.
The supplementary step-4 session completed on 2026-10-21; see
[runtime evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md) and
[preparation evidence](Evidence/AB_S0_SUPPLEMENTARY_PREPARATION_2026-10-21.md).
Five positive cases compile/read back on both v38 targets. Echo reads all
2,097,152 bytes exactly at both 500/4000-byte connection settings, with
fragmented reads from byte zero. The 2 MiB + 4-byte UDT is rejected at import
on both compiler targets; no global array-tag size limit is claimed. The
browse-name root and precise LREAL `L`-suffix/typed-data vectors pass. Owner
Capacity displays 69%: 2,189,916 used / 3,145,728 total blocks, 955,812 available.
Native task MaxScanTime is 10 us with zero overlaps on this inert 10 ms probe.
Genealogy and all five live documents were restored, 31/31 regressions pass,
and final read-only checks pass. This completed session must not be reused. The
first image's untyped decimal rounded to REAL before LREAL assignment. Retain
this finding and the failed
reader/acquisition attempts in the runtime evidence. The first session's
preflight, backup and download outputs already exist and must not be overwritten.

1. Owner starts Echo (elevated) and logs out of the HMI. Get current download
   authorization.
2. Run `S0Session.exe backup` (guard, preflight, upload), then
   `deploy-probe`.
3. Run the read-only `fraktal_ab_s0_canonical_measure.py --expect-serial
   601FC87B --generation combined/combined.json --output <new>.json`. Record:
   - template type codes for `TIME`/`TIME32`/`LTIME`/`DT`/`LDT`;
   - their units, by comparison with the assigned literals;
   - what LINT→`DT`/`LDT` assignment does to the value (Rockwell treats every
     LINT as an `LDT` in conversion);
   - BOOL bit packing, string LEN and bytes (UTF-8), nested structure arrays.
4. Extend the probe with the questions S2 depends on, compiled and measured
   in the same session if possible:
   - **Size:** the largest single structure and tag the controller accepts,
     and whether reads need Read Tag Fragmented (`0x52`).
   - **Naming:** a controller-scope root tag named exactly as the root's
     browse name (`Press`).
   - **Discoverable access:** whether External Access shows in the Symbol and
     Template access bits.
5. Run `restore-genealogy`, then `fraktal_ab_genealogy_execute.py`
   (configuration restore and 31 regressions) and the final read-only checks.
6. **Decide** D6 and D7 from the measurements. Write the evidence record,
   `AB_FROZEN_CONTRACTS_V2.json` (draft) and the Part III amendment draft. The
   amendment covers §3.8 type map V2, §3.10 exposure, §11.1 (desktop direct
   per D9, replacing "Direct CIP from the HMI is not the reference design"),
   and the L24ER retirement.

**Exit:** the owner approves the V2 draft. Achieved on 2026-10-20. The
supplementary gates before S2 now pass at their measured Echo scope.
Access findings correct the earlier physical assumption: a writable descendant
needs Read/Write on every ancestor, with Read Only on other public members.
None members prevent whole-structure reads, so private working storage stays
outside the canonical whole-read records. Symbol attribute 10 distinguishes
top-level RO (2) / RW (0) on this Echo; raw Template metadata does not distinguish
member RO/RW/None. The V6 manifest therefore publishes effective member access
alongside logical types and bounds. These findings implement the approved
leaf policy; they do not activate shipping V2 or authorize an S2 download.

### S1 — Generic reference reader (Python, test oracle)

- **New tool** `tools/fraktal_ab_canonical_reader.py`. It discovers through
  Symbol, Template and manifest, decodes with the S0 decoder, and emits the
  same `values` document shape as `fraktal_ab_projection.project`. It is a gate
  oracle, not a shipped runtime: no gateway uses it.
- **New tool** `tools/fraktal_ab_canonical_equivalence.py`. It compares the
  reader's output with the projection for the same controller state, both live
  and from recorded captures. Its report lists every differing path, with the
  D2 allow-list explicit.
- **Capture fixtures.** Promote `projection_capture_01.json` (and a press
  capture) to compact test fixtures, plus Symbol/Template/tag-byte captures for
  the canonical image once S2 exists. Fixtures are recorded data, never
  hand-edited. Keep them within a stated size budget; compress if necessary.
- **Tests:** synthetic-template unit tests, extending
  `test_fraktal_ab_s0_canonical_probe.py`, and capture-replay tests.

**Exit:** the reader reproduces S0 measurements and the equivalence tool runs
in the AB suite.

**Oracle exit passed, 2026-10-20:** 1,921 AB tests (20 canonical tests), 74 root
tests, clean spec/contracts/strict consistency, both unchanged S0 v38 offline
build/read-backs, full 47-check S0 replay and 4,437-value legacy replay. See
[S1 evidence](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md) for the remaining
capture/wire-adapter boundary and exact outputs. No controller change occurred.

**Implementation boundary clarified on 2026-10-20:** S1's generic reader uses
a normalized PLC-manifest annotation model. The physical V6 layout is explicitly
S2 work in the approved V2 target; therefore the standard wire-manifest loader
and stable paired live V1/V2 acquisition belong to S2, alongside its first image.
The S1 live seam requires that loader, never a station declaration or an external
manifest file. Matching configuration tokens does not prove scan atomicity.

No recorded press projection read/values capture was found in the checkout or
`C:/work`; only the genealogy golden capture exists. Record the press fixture
on an appropriately gated image before full S3 equivalence acceptance. Do not
re-contact the retired L24ER to fill this gap, relabel genealogy, or manufacture
recorded values. Canonical Symbol/Template/byte captures remain S2 work as above.

S0's recorded bytes omit Template structure sizes and have no canonical root
or manifest. S1 replays them diagnostically and reproduces all 47 checks,
including the two DT/LREAL findings. Strict canonical decoding requires Template
attribute **5** byte sizes. Synthetic templates test that path; a read-only Echo
observation confirms the attribute service against 50 legacy templates, without
claiming V6 acceptance or settling the supplementary maximum-size/access probe.

### S2 — Canonical module tree (first published surface)

**Offline candidate prepared, 2026-10-21:** the opt-in genealogy image publishes
46 S2 paths for one Unit and six CMs, alongside unchanged legacy contexts and
its V5 oracle manifest. The separate V6 manifest and generic physical loader
are implemented; see [wire candidate](AB_CANONICAL_PUBLICATION_S2_WIRE_DRAFT_2026-10-21.md)
and [preparation evidence](Evidence/AB_S2_CANONICAL_PREPARATION_2026-10-21.md).
Both v38 targets compile/read back; prepared ACD pin is 2B3F99D9...D200973.
The fixture's same-state gate uses an equal-even generation around all paired
reads, bracketed around the entire PLC scan. **S2 exit passed on 2026-10-21**:
46/46 paths and types match with same-scan proof, both owner Capacity values
and native scan deltas are recorded, and candidate/restored-baseline
regressions pass 31/31 each. Genealogy is restored and final checks pass. See
[runtime evidence](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md), including
the retained interrupted backup and guarded recovery. The next surface is S3a;
shipping V2 activation and the remaining stages are still open.

During migration V5 remains solely for the existing oracle/harnesses. V6 is
the canonical client's manifest; no client reinterprets the V5 context rows.
The first Status slice contains identity/state/fault fields; diagnostics follow
in S3b. ModelCode retains the application's existing 80-byte catalog bound.
The module forest is discovered from native Status members. Private scratch
and the test generation/timing records are not module roots.

- **Generator** (`fraktal_ab_generate.py`):
  - a root record (`FRK_T_<App>Root`) and a controller tag named exactly as the
    root's browse name;
  - every module's `Status : ST_ModuleStatus` equivalent as named members;
  - children as members named after the schematic;
  - mode, run style, model, `Step`/`CurrentStep`.
  - During S2–S3 the canonical structures are written **alongside** the
    existing contexts. Running both is a migration device only; S6 collapses
    them.
  - Derived values move into generated ST in the owning service
    (`unit_logic`, `module_logic`, `diagnostic_logic`, …), never into a client.
- **Manifest** (`fraktal_ab_manifest.py`): `Fields` rows describe canonical
  paths with `LogicalType` and the D2 logical lower bound/element count. BOOL
  arrays are expanded from template DWORD storage using that logical extent.
  Manifest major steps to 6.
  Effective member access is published where native discovery does not provide
  it; derive it from the same owning declarations as the UDT access settings.
  Canonical whole-read records contain no None members. Ancestors of a writable
  mailbox are Read/Write while other public branches remain Read Only.
  `content_hash`/`config_revision` stay the coherence token.
- **Tests:** generator unit tests (member names, access, radix, no reserved
  names), compile and read-back on both targets, then live equivalence on Echo
  for the published subset.

**Exit:** equivalence for the S2 subset, plus memory and scan deltas recorded.

### S3 — Remaining surfaces, one at a time

Migrate in this order, smallest dependency first. Each surface is one commit
with its own equivalence, Capacity and scan record.

S3a uses a [94-path inventory](AB_CANONICAL_PUBLICATION_S3A_NOTES_2026-10-21.md).
The code exposes a distinction the original surface list did not spell out:
physical array capacity differs from the current logical view, and the model
count changes at runtime. V6.0's static exact-extent rows need a versioned
published view before this image can be generated. Decision.Timeout/SourcePath
also have no oracle paths; resolve that separate Core gap explicitly. Neither
finding permits weakening the five-D2-only equivalence rule. The owner selected the logical-view option, and the
[V6.1 candidate](AB_CANONICAL_PUBLICATION_S3A_WIRE_DRAFT_2026-10-21.md) implements
explicit selections/live count references with validation even for empty
arrays. S2 output is unchanged. **S3a offline preparation passes:** 1,960 AB
tests, 74 root tests, both v38 compiler/read-backs and a pinned reopened ACD.
See [preparation evidence](Evidence/AB_S3A_CANONICAL_PREPARATION_2026-10-21.md).
**S3a runtime exit passes at this subset**, after current owner authorization
for the pinned F1D24CA8...A7EE79F image. Capacity is 817,476 used / 2,328,252
available / 3,145,728 total blocks (displayed 25%), +72,232 blocks over S2.
All 94 paths/types match, including four active-decision pairs. Candidate
and restored-genealogy regressions pass 31/31 each. The first candidate run's
18 completed rows and failed same-scan acquisition are retained; moving
metadata copies/decoding after the closing generation read fixes the harness
without changing PLC code, proof or retry budget. Native candidate median
LastScanTime is 110 us, cumulative MaxScanTime 1,178 us, zero overlaps; the
prior S2 observations were 109 / 1,177 us. Workloads differ by the disclosed
failed/retried fixture and paired captures, so these are observations rather
than isolated cost measurements. Genealogy is restored and final checks pass.
See [runtime evidence](Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21.md).
S3b offline preparation now passes 2,007 AB tests, 74 root tests, the native
compiler/read-back and automatic Capacity gates; see
[preparation evidence](Evidence/AB_S3B_CANONICAL_PREPARATION_2026-10-21.md).
Its independent inventory has 304 paths: the accepted 94, six diagnostic
fields on seven modules (42), and seven timing fields on eight rows for three
commanded CMs (168). The fixture has no EM. Several full-Core status fields have
no oracle paths; these remain explicit gaps in
[the S3b notes](AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md).
The prepared ACD is pinned to `634A3A86...4394EEF`. Automatic Studio Capacity
is 991,612 used / 2,154,116 available / 3,145,728 total blocks (31% displayed),
+174,136 blocks over S3a. **S3b runtime exit now passes at this subset** after
current owner approval of that exact image: 304/304 paths/types, four decision
pairs, ten held pairs and four Unit first-out fault pairs, covering all three
renditions. Candidate and restored-genealogy regressions pass 31/31 each.
The first eight-row run failed same-scan acquisition because mailbox commands
set the shared connection to 500 bytes. An independent 4,000-byte read observer
fixes this without changing framing or proof. A subsequent 31-row run lacked
fault observations after child Execute-drop; observing the owning Unit's
latched first-out closes the original coverage gate. All failures and 39 extra
candidate rows remain recorded. Accepted captures need one or two attempts.
Native candidate median LastScanTime is 123 us (122–123), cumulative maximum
1,190 us, zero overlaps; prior S3a was 110/1,178 us. These are observations
under disclosed different workloads, not isolated publication costs.
Genealogy/five documents are restored and final checks pass. Final gates:
2,011 AB tests, 74 root tests, spec/contracts/strict consistency and native
download/read-back/access checks. See
[runtime evidence](Evidence/AB_S3B_CANONICAL_RUNTIME_2026-10-21.md).
S3c offline preparation passes at an independently inventoried
647 paths (304 prior plus 343 sequence/current-step leaves). Both v38 builds,
strict read-backs/access, 2,052 AB tests and 74 root tests pass. Automatic
Capacity is 1,107,552 used / 2,038,176 available / 3,145,728 total Blocks (35%),
+115,940 over S3b. ACD pin: A2559188...0C2286C. See
[preparation evidence](Evidence/AB_S3C_CANONICAL_PREPARATION_2026-10-22.md) and the
[S3c notes](AB_CANONICAL_PUBLICATION_S3C_NOTES_2026-10-22.md) and
[V6.2 record-binding draft](AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md).
Definitions live in a separate PLC record bound by the manifest; the PLC Chart
still owns fast-step history. The native root carries the cursor, history,
sparse notes and current-step detail. Generic discovery imports no station.

**S3c runtime exit passes at this subset** after current owner approval of
A2559188...0C2286C. Candidate/baseline regressions pass 31/31 each on their first
runs. All 647 paths/types match across four decisions, 14 held/fault pairs and
21 sequence pairs, covering ST/SFC/LD mode clear, sparse warning notes and
retained completed fast steps. Idle equivalence and generic discovery also
pass. All 40 paired captures and the generic capture replay identically.
Same-scan attempts range 1-6 within the unchanged 100-attempt/five-second gate.
Native candidate median/range is 200 us / 200-201, cumulative maximum 1,600 us,
zero overlaps; prior S3b observations were 123/1,190 us. Different workloads
preclude an isolated publication-cost claim. Restored genealogy is 99/1,167 us.
See [runtime evidence](Evidence/AB_S3C_CANONICAL_RUNTIME_2026-10-22.md).

**Readiness correction, 2026-10-22:** the inherited work scripts called Mode 0
MANUAL; the declaration defines AUTO=0, MANUAL=1. Earlier MANUAL claims remain
unsupported and sealed evidence is unchanged. Under the S3c approval the fixed
helper performed three LOGIN/SET_MODE(1)/LOGOUT normalizations, without policy
or stimulus changes. Final guards now verify actual MANUAL=1/idle, Run, not
faulted, Remote, scanning, logged out, not restoring, saved/live documents
equal, restored policy and the original preflight. The initial legacy-backup
access audit used the wrong canonical allow-list and stopped deployment; an
exact tag/access comparison with the sealed genealogy artifact passes before
download. The failed audit is retained; no controller or reader rule changed.

S3d offline preparation passes at 2,125 paths: the accepted 647 plus 1,469
AlarmLog paths and nine StateFlags paths. The original table's 1,469 described
AlarmLog alone; see the [S3d inventory/notes](AB_CANONICAL_PUBLICATION_S3D_NOTES_2026-10-22.md).
Both v38 builds/read-backs/access and 2,062 AB tests pass. The prepared ACD pin
is E5CA9AB3...7CF7C9D. Automatic Capacity is 1,290,016 used / 1,855,712 available /
3,145,728 total Blocks (41%), +182,464 over S3c. One shared PLC calendar routine
serves diagnostics, event timestamps and flags; caches avoid unchanged text/time
work. Alarm append/reset ownership and all earlier image outputs are unchanged.

S3d runtime now passes under the owner's exact-session approval. Candidate
and restored-baseline fixtures pass 31/31; four decision, 14 held/fault,
21 sequence and eight reset captures (four before/after pairs) cover ST/SFC/LD.
All 2,125 paths/types match; 48 paired captures including idle replay exactly.
Active/closed events, nonzero duration, ring wrap, flag transitions and one-reset
Blocking release are observed. WAIT_RESET is model-covered but was not observed
in these runtime captures. Full-Core event Category, ResetAt and ShelvedUntil
remain explicit oracle gaps. See [runtime evidence](Evidence/AB_S3D_CANONICAL_RUNTIME_2026-10-22.md).

**Acquisition correction:** the original full-record read exceeded the 10 ms
task window. Two retained attempts stopped after eight and 26 passing rows.
The acceptance harness now caches PLC-bound V6.2 metadata under equal manifest
revision tokens and reads live canonical/oracle records on two independently
guarded read-only connections. Both finish inside the same unchanged equal-even
scan proof (100 attempts/five seconds); accepted attempts range 1-8. The generic
reader, PLC image, task period and regression stimuli are unchanged. Actual
recorded regression rows total 96, including 34 from the failed attempts;
individual tag-write calls were not instrumented. This fixes the read plan,
without weakening the gate or treating failed runs as accepted coverage.

Native root/sequence/alarm-metadata payloads measure 77,304 / 7,308 / 16,616
bytes. Candidate scan median/range is 437 us / 436-437, cumulative maximum
3,111 us, zero overlaps. Restored genealogy is 99 us / 99-100, maximum 1,167 us.
These workloads differ; their difference is not an isolated publication cost.
Genealogy is restored, actual MANUAL=1/idle, Run, not faulted, Remote, scanning,
logged out, five saved/live documents equal, policy and original preflight
verified. The S3d approval is consumed; S3e preparation is next and a future
controller session needs its own gates/authorization. No commit/push is authorized.

Final S3d gates: 2,066 AB tests / 276.677 s and 74 root tests / 1.942 s;
spec/contracts, strict consistency (0 errors/warnings) and whitespace pass.
Only the acquisition oracle and its tests changed from the preparation seal;
68 other bound sources, including all PLC/generator inputs, are unchanged.
Both native v38 build/read-back gates remain bound to that exact image.

S3e offline preparation now covers 2,154 paths, adding 29 Access/data-policy
paths and enriching the existing ring's audit Description/SourcePath in place.
See its [independent inventory and notes](AB_CANONICAL_PUBLICATION_S3E_NOTES_2026-10-22.md).
Policy.Required completes the fifth D2 zero-bound mapping. A generic BITSTRING32
reader correction preserves the unsigned LoginResultSequence high bit; no
station fact enters the reader. All five earlier images/replays are unchanged.
Both v38 builds/read-back/access and 2,078 AB tests pass. Original prepared pin
95E85B50...A1B240B has automatic measured Capacity 1,568,852 / 3,145,728 Blocks
(49%, +278,836 over S3d). The source, review copy and receipt are hash-bound.

The next fixture scope includes the inherited 31 rows plus two explicit Access
checks (unknown-user login refusal, one class read-level edit/restoration), six
read-only Access phases and the inherited decision/condition/sequence/reset
captures. The owner subsequently approved and completed that S3e session. Its
exact-artifact [preparation record](Evidence/AB_S3E_CANONICAL_PREPARATION_2026-10-22.md)
binds both native builds, 2,078 AB / 74 root tests, spec/contracts, strict
consistency/whitespace, measured Capacity, helpers and false approval template.
Runtime now passes at all 2,154 values/types: 31 inherited candidate rows, two
fixed Access checks, four decisions, 14 held/fault, 21 sequence, eight reset and
six Access captures, plus idle (54 paired captures, independently replayed).
LoginBusy/failure/success/logout, manual/class-policy changes and audit actor/
action text are observed. The original whole-scan proof remains 100 attempts /
five seconds, with accepted attempts 1-41; metadata uses V6.2 revision coherence.
See [runtime evidence](Evidence/AB_S3E_CANONICAL_RUNTIME_2026-10-22.md).

The first complete candidate matrix passed. Its first coverage audit incorrectly
checked Required[1] for MANUAL; the owner uses zero-based gate 2. An unnecessary
partial repeat stopped after one inherited row and two passing Access checks
under that same wrong observer expectation. Both cleanups restored documents/
policy. The corrected audit derives the gate from the owning action map and
accepts the original complete captures, which already include 0/1 at Required[2].
The temporary observer/test edits were restored byte-for-byte. All 76 prepared
root sources still match; no PLC/image/stimulus/proof change was needed.

Baseline regressions pass 31/31. Actual recorded rows total 67 (64 accepted,
three extra from the partial repeat). Known additional fixed-vector/normalization
mailbox commands total 12; per-tag write calls are unmeasured. Native root/
sequence/alarm-metadata payloads are 77,856 / 7,308 / 16,616 bytes. Candidate
TASK median/range is 817 us / 816-817, cumulative maximum 4,033 us, zero overlaps;
genealogy is 99 us / 99-100, maximum 1,167 us. Workloads differ; this is not an
isolated publication-cost measurement. WAIT_RESET, high-bit injection and
data-denial detail retain explicit model-only scope where not runtime-observed.
Genealogy is restored, Run/not faulted, Remote, scanning, actual MANUAL=1/idle,
logged out, five saved/live documents equal, original policy/preflight verified.
S3e authorization is consumed. S3f preparation is next; future controller work
requires its own exact-image gates and current approval. No commit/push.

**S3f inventory finding, 2026-10-22:** the independent
[inventory](AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json) identifies
801 additional legacy paths (2,955 cumulative), including 30 configuration
entries of 25 fields. The current oracle conflicts with the target's Core
types at 110 paths, omits 12 Core fields, and serves all 30 entries as one
host-assembled page. PendingSince is time-of-day without a date; revisions
exclude boot identity; non-empty set/document responses are host overlays.
Read the [contract correction proposal](AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md).
The owner has approved its bounded-page/type/time/provider corrections for
offline implementation; section 1 now names this exact additional exception.
The immutable inventory evidence records the earlier pending state. S3f offline
implementation and compiler/model validation are in progress; no controller
operation is authorized and no S3f runtime acceptance is claimed. The reference window of
16 is an implementation choice; Core requires bounded paging without a full
manifest buffer, rather than mandating that numeric window size.

| Order | Surface | Notes |
|---|---|---|
| 3a | Unit core: `Decision`, `Catalog`, `ModePolicy`, `Supported*Published`, `AvailableModels` | Apply D2 bounds (`ModePolicy`, `SupportedModesPublished`, `SupportedRunStylesPublished` from 0) |
| 3b | CM/EM status, command timing, diagnostics | The PLC publishes `DescriptionKey`/reason codes, never rendered text |
| 3c | Sequence: `SequenceSteps`, `SequenceAnnotations`, `ActiveSteps`, step definitions | `ActiveSteps` from 0 (D2); keep fast-step history PLC-side |
| 3d | `AlarmLog` (Active, Ring, Meta), `StateFlags` | 1,469 AlarmLog + 9 flag paths; 2,125 cumulative. Preserve S0 size/read qualification and measure actual same-scan acquisition |
| 3e | `Access` (`Policy.Required` from 0, D2), audit, data policy | Login stays plain PIN through the mailbox. The gateway's salt pre-hash used declaration data and is dropped; the PLC hashes, with `LoginBusy` covering latency |
| 3f | Configuration pages, `ConfigPersist`, `ConfigSets` listing | Pages come from the PLC on `QUERY_CONFIG` (as TC3), not assembled by a client |
| 3g | `Oee`, `OeeTrend`, `Profiler`, `SystemHealth` | Profiler is 900 paths; derivations are event-driven, not per scan |
| 3h | `Part` (+ genealogy), `HostEvents`, `Nameplate`, `SignalTower`/`MachineState` | Keep the existing single append owners; only the publication form changes |
| 3i | `Line` (calendar, shifts) | Line keys stay `line.`-prefixed |
| 3j | Fieldbus topology as its own published data product (TC3 `GVL_<Project>Fieldbus.Topology`) | Not a module root |
| 3k | `HmiResponse` / release report, `HmiRequest` mailbox | The mailbox stays the single write surface, with ordering per `OPCUA_TRANSPORT.md` |

**Exit:** full equivalence (4,437 genealogy paths, plus the press) on Echo;
31/31 regressions; rendition gate green.

### S4 — Generic Dart `CipSessionClient` and the desktop path

- **New** `HMI/packages/fraktal_opcua_client/lib/src/cip_session_client.dart`,
  exported like `ads_session_client.dart`. It covers:
  - EtherNet/IP session handling and a large Forward Open;
  - Symbol list (`0x6B`), Template reads (`0x6C`) and Read Tag Fragmented;
  - template-driven decoding plus the manifest lower bound and logical type;
  - `fraktal.opcua.snapshot.v1`, fast/slow tiers like `WebApiSessionClient`;
  - blocking work in a worker isolate, like `AdsSessionClient`.
- **Writes** follow `OPCUA_TRANSPORT.md`, but stay disabled unless the endpoint
  is a commissioned CIP Security session (S7). The repository exposes the
  read-only state so the HMI states it explicitly (Core §11.2). Check the
  existing gateway read-only behaviour first and reuse its mechanism.
- **Factory:** `external_repository_factory_native.dart` routes `cip://` to
  the new client.
- **Delete** the spike `HMI/lib/data/cip/` (`cip_session_client.dart`,
  `eip_cip_client.dart`, `fraktal_manifest.dart`, `libplctag_bridge.dart`).
- **Golden tests** replay recorded Symbol/Template/tag bytes to the expected
  snapshot from S1.
- **Gates:** `flutter analyze`, the full HMI suite with the pinned Flutter
  `--enforce-lockfile`, and desktop acceptance on Echo (render all surfaces,
  writes refused with an explicit read-only state).

### S5 — Dart gateway `cip://` for Web clients and commanding

- `HMI/gateway/bin/fraktal_gateway.dart`: add `cip://` beside `ads://` and
  `s7web://`, using the same session client. Add the deployment switches the
  scheme needs (serial pin, slot) and document them in `DEPLOYMENT.md`.
- Writes reach the PLC through the gateway's existing Core §14 gate (token +
  `wss://`, write roots). For each station, ask and record **read-only or
  write-enabled** (AGENTS §3a).
- Update the Windows installer and tray: an instance may use a `cip://`
  endpoint. Drop the never-exercised Python AB gateway packaging path.
- **Acceptance:** the Web HMI renders and commands Echo through the Dart
  gateway, and recovers after a gateway restart.

### S6 — Retirement and collapse

1. **Migrate the harnesses.** 22 tools and 44 test modules read the generated
   contexts (`read_unit`, `read_layout`, `*_context_members`, the projection).
   Move every acceptance harness, including the 31-row regressions and the
   Part, tower and genealogy executes, onto canonical reads through the S1
   reader. The equivalence gate must stay green throughout.
2. **Collapse the generator.** Make the canonical structures the working
   storage. Remove the old contexts, the v5 manifest tables they described and
   the copy logic. Record the memory and scan savings.
3. **Persistence (§3.8b).** Relocate it per the owner decision (see §6). TC3
   and TIA keep documents and sets on a PLC-owned medium, so the coherent
   target is a controller medium behind the existing store seam.
   - Probe Logix file and SD services on the 5580 and on Echo first (v38 audit
     N8).
   - Until it is accepted, the Python live-document keeper and set store
     remain as a standalone adapter reading through the S1 reader, not as a
     gateway.
4. **Host-event sink.** Keep it as a deployment adapter (Core §11.6), reading
   the canonical `HostEvents` through a generic reader. Its durability,
   cursor and dedup behaviour is unchanged.
5. **Delete** `fraktal_ab_projection.py`, `fraktal_ab_gateway.py` and the code
   only they used. Update `check_ab_spec.py` and `check_ab_contracts.py` (V2)
   and `check_consistency`.
6. **Documents:**
   - Part III (final form of the S0 drafts);
   - `OPCUA_TRANSPORT.md` (new "Allen-Bradley CIP transport" section beside
     ADS and S7 Web API);
   - `AGENTS.md` §3a (baseline v37+, L24ER retired, `cip://` no longer a
     spike) and §5;
   - the AB README and `AB_NEW_PROJECT_GUIDE.md`;
   - `HMI_CONTRACT.md` (the five D2 bounds).

### S7 — Physical controller and CIP Security

- Obtain a CIP Security-capable 5380/5580 at v37 or above. Commission a
  FactoryTalk Policy Manager policy. Add a TLS client (port 2221,
  certificate-based) to `CipSessionClient`.
- Enable direct writes per D9.
- Physical acceptance: Capacity/fit, scan, retention across power cycle,
  download and upgrade, and Part III §11.2.1 security evidence.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scan time grows as Python derivations move into ST | Measure per surface. Compute derivations on change, not every scan. Keep owners single (one append owner per ring) |
| Structure-size or CIP read limits for large roots (AlarmLog, Profiler) | Measure in S0 step 4. If needed, publish a surface as its own data-product tag with the identical canonical path rule, decided once in Part III |
| String memory at Core widths | Budgeted against 3 MB; measured per stage |
| Persistence relocation (Echo may not emulate SD/file services) | Probe first. Keep the standalone adapter until a medium is accepted. Owner decision recorded |
| Harness migration volume (22 tools, 44 tests) | Migrate behind the equivalence gate before deleting anything |
| Echo availability after reboot | Elevated start by the owner. Check the service and listener before any guarded step |
| HMI customization bound to the five old AB array paths | Call it out in release notes. The mapper is already base-agnostic |

## 6. Owner decisions pending

1. V2/Part III target approval **recorded 2026-10-20** (D6/D7 included); no longer pending.
2. The §3.8b persistence medium (controller medium versus a standalone
   adapter) after the S6 probe.
3. Read-only or write-enabled for each gateway station (S5, AGENTS §3a).
4. Hardware for S7.
5. Commit and push policy for this work. Nothing is committed yet.

## 7. Relative size (estimate, not a commitment)

| Stage | Estimate |
|---|---|
| S0 | 1–2 days |
| S1 | 2–3 days |
| S2 | about 1 week |
| S3 | 3–6 weeks |
| S4 | 1–2 weeks |
| S5 | about 1 week |
| S6 | 2–3 weeks |
| S7 | hardware-bound |

Native gates (owner Capacity, downloads) set the real pace.

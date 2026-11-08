# C5 - harnesses and command-only publication

Working notes, 2026-11-06. Entry `43201509f` on main. The owner requests
continuation and authorizes commit/push on main after the gates. Owner edits
in `.vscode/settings.json`, the Siemens Manifest README and root
`analysis_options.yaml` are excluded. No controller operations in C5 so far;
native integration remains S6-Q after C7 under standing O3.

## Scope and implementation order

C5a qualifies the common O11 command path and selected O10 reads first. It
makes the basic collapsed press walk use the gateway, without changing its
case or wait predicates. It is not the exit of C5. The remaining HX readers,
configuration/set clients and host-adapter lifecycle join in the next
increment before Frame/staged endpoints can be removed under V6.12.

1. Finish the O10 harness views and O11 command switch for every HX consumer.
   Preserve assertions, fixed plant-write scopes and explicit restoration.
2. Remove Frame and legacy staged endpoints from collapsed profiles only.
   Private working buffers may remain as the single owning state.
3. Publish V6.12 (Services empty; HostServiceBindings retained), update both
   generic readers and all gates. Legacy declarations remain byte-identical
   until retirement. Integrated native acceptance remains S6-Q after C7.

## C5a complete offline

- The generic row reader selects native members from O10 V1/V2 Templates.
  Scalars and DINT arrays use their native extents and element counts. The
  strict progressing scan proof covers canonical leaves and private facts
  together; the private facts never borrow the longer owner-proof window.
  Original whole-V1 reads remain supported.
- V2 adds the exact private `Mailbox.DiagnosticKey` and a shape-derived type
  name. Press carries its original 29 private facts plus that key; genealogy
  initially carries only the key, not a claim that its remaining HX readers
  have migrated. The fixture remains Read Only and outside the manifest.
- The old mailbox ACK is not a Core ACK alias. Two accepted S3 press captures
  show that they differ under the dual-ingress adapter. Command observation
  reads Core request/ACK/Accepted/Diagnostic and the private numeric key under
  one scan proof instead.
- Collapsed `px.command`/`px.manual` use the existing brand-neutral gateway
  command client. The gateway remains the only native encoder. Manual
  requests use dotted identity and command; the PLC resolves the ordinal.
  There is no retry, queue or native-write fallback after transport failure.
- A supervised gateway lease pins the compiled executable hash, serial/slot
  endpoint, root and unique instance nonce. Readiness and the owned process
  must still match before every command. A wrong listener, changed policy,
  package or target refuses. Only the owned gateway child is terminated.
- Apparatus state belongs to the native connection: pylogix PLC is slotted.
  Its context exit calls `conn.close()` directly, so that boundary owns
  gateway cleanup. Tests exercise the installed driver without connecting it.
- The collapsed press now enables the already approved V6.7 counter bindings.
  Its frozen S3 parent is V6.6; the earlier C4b replay supplied those bindings
  synthetically. The new emitted-header test and schema declaration close
  this metadata prerequisite. The frozen parent remains unchanged.

## Qualification ledger

Append-only logs are in `C:/work/fraktal-ab-c5-control-20261106/`.
The final 37 command/lease tests pass with no ResourceWarning. The earlier
103-test focused run passed before the added V6.7 emitted-header test; its
nine-test image/declaration rerun now passes too. Both preliminary schema
checks and the exact executable-token delta proof pass. The final discovery
rerun passes all 2,612 AB tests; the old storage test is corrected to treat
Mailbox as a scalar record owner, with all 10 storage tests passing. Both
profiles build/read back on both v38 targets, with access/default audits,
byte-identical regeneration and legacy-output checks. Capacity is 60% for
genealogy (1,915,620 used / 1,230,108 available / 3,145,728 Blocks) and 46% for
press (1,447,072 / 1,698,656 / 3,145,728). All 44 gateway tests, locked
dependencies, analyzer and executable build pass, as do the 85 root tests and
three root gates. The sealed scope is recorded in
[C5a evidence](Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06.md).

Failures/superseded runs remain. They include the legacy/Core ACK mismatch;
old fixture-count expectations; a malformed-name test expecting refusal later
than the constructor; the slotted-driver/lifecycle cleanup discoveries;
newline-only normalization; the missing V6.7 binding; a decorated-versus-wire
header test error; an over-strict effective-access check; and a stale private
ACD-helper path. No accepted case predicate was weakened. Preparation reuses
successful artifacts only by exact source/read-back hashes.

## Code-driven plan clarifications

The old Phase 6 viewer expects a read-only QUERY_CONFIG mailbox ACK.
`gateway/bin/fraktal_gateway.dart` sets
`allowMailboxConfigurationQueries: !isCip`. The approved S4b read-only view and
`readConfigurationPage` are now that browsing path. Preserve the browsing and
refusal checks through that API; do not enable the obsolete exception.
The Python gateway/projection mutation subjects retire under RT/MO.

The private AST provenance experiments (`fact_provenance_01/02`) are not an
accepted O10 census. Version 02 resolves more literal/comprehension keys, but
unknown source expressions and cross-module arguments still need manual
review. A zero unresolved-key count does not prove that every read was found.
No extra context facts from those experiments have been declared.

`c5b_catalogue_01.json` instead records literal AST call sites and candidate
row/check predicate hashes across the same 24 HX modules: 303 source sites
and 127 case candidates. It imports no harness and reads no credentials.
Those are source counts, not runtime coverage or an accepted private-fact
inventory. Dynamic helpers and inherited reads still need review. In that
review, distinguish Core UInt32/Boolean values from native DINT/0-or-1 facts
at high-bit/wrap boundaries; do not infer raw equivalence from normal captures.

## Remaining in C5

- Account the remaining HX facts precisely per instance and read site; replay
  them against accepted captures without changing case predicates.
- Migrate access, alarm/report/audit/configuration/OEE and other HX reads.
  Numeric-key expectations must use PLC-published localization, not fresh
  generator ordinals after C4's storage narrowing.
- Bring the collapsed press onto the already approved configuration-view,
  owner-revision and host-service publications before its configuration/set
  clients join; its frozen S3 parent stays unchanged.
- Move all remaining command/set clients to the public gateway and V6.11
  host adapter. Replace MailboxWriter/broker/keeper interception, preserve
  original documents and all explicit restoration, and migrate the standalone
  canonical press launcher away from MO/observation-frame helpers.
- Remove Frame/staged services, publish V6.12 and update Python/Dart readers;
  run all stage gates before C6. C6 removes legacy exposure/tables, C7 narrows
  production AUTO, then S6-Q proves native integration and retirement.

## C5b1 - capture and read-only configuration browsing

C5b1 is complete offline, with 2,629 AB and 85 root tests passing. The final
85-test focused run also passes. Qualification records are in
`C:/work/fraktal-ab-c5b-control-20261106/`. This is the configuration/capture
slice of C5b, not its exit. The collapsed press enables the already approved
V6.8 read view and V6.10 owner revisions; its frozen S3 declaration remains
unchanged. Host services are not enabled on the press by this increment.

Phase 6 capture now uses typed Core identity/key/revision arguments. It reads
the current PLC revision rather than a generator-side constant, and checks
refusals against the deployed command key table. That table is immutable
activation metadata resolved through its published Symbol and native Template,
cached for one guarded connection only. Sparse numeric keys are valid; wrong
types, malformed strings, duplicate keys and a changed root revision refuse
without caching a partial result. No cyclic value is supplied from this cache.

The independent capture check reads definitions from the PLC's read-only view.
The viewer check starts a separately owned, hash/serial/root-pinned read-only
Dart gateway and uses its existing `readConfigurationPage` RPC. It verifies
the returned key and unchanged controller sequence, then attempts START and
requires refusal before a commit. It neither writes QUERY_CONFIG nor enables
the old unsecured-CIP mailbox exception. The new RPC reuses the command
client's framing and failure-close behavior; it adds no transport encoder.

The typed foreign-root refusal is the approved Core `TARGET_KEY`, rather than
the legacy Frame `CONFIG_KEY_UNKNOWN_KEY`. The capture candidate remains
999999 in TextValue and must still be ignored by the PLC. All machine-value,
audit, no-change, restoration and final disarm assertions remain. Restoration
uses typed WRITE_CONFIG with the live revision. These are the two protocol
subject adaptations recorded above, not relaxed equipment acceptance.

O10 grows from 30 to 40 facts: Cfg0.SchemaVersion/BaselineWorkMs; ConfigAudit
Head/Sequence/Kind/Value/SourceKey/Revision; Profiler.LastWork; and the air
permissive. ConfigAudit arrays retain all 16 native cells. The fingerprint uses
the accounted configuration schema; capture compares the exact unmasked raw
value and audit, independently of gateway output. Neither access masking nor
configuration values are reconstructed in the apparatus.

The old 86 accepted press captures contain four of the new facts. The replay
adds those facts from their original raw inputs. They do not contain
ConfigAudit: its six fields are covered by the generated-writer/ST model and
exact token proof only, with native capture/audit acceptance explicitly left
to S6-Q. The frozen C5a source, overlaid with just the two approved feature
flags, produces a reference whose other 62 routines match exactly. The sole
executable delta is the literal append for the ten O10 facts. Genealogy's
image remains byte-identical to C5a.

The press builds on both v38 targets and passes read-back/access/default
audits. Studio Capacity is 1,554,428 used / 1,591,300 available / 3,145,728
Blocks (49%), 107,356 more used than C5a. Genealogy retains its hash-bound
C5a build/read-back/Capacity evidence (60%). Scan is not measured offline.
No controller operation or native acceptance has run. Failed preparation
and superseded test attempts are retained.

Next: C5b2 moves the set/document workflows onto the Dart V6.11 host adapter
with an isolated store, explicit original-document restoration and an owned
process lifecycle. Other HX facts/clients still need individual accounting;
the partial capture migration does not qualify the whole Phase 5/6 suite.
The Python gateway actor-state test must retire with that subject, with an
honest packaged write-scope refusal replacing it. Frame/staged endpoints stay
until all consumers migrate in C5c/V6.12; C6, C7 and S6-Q follow afterward.

## C5b2 - Dart set and live-document ownership

C5b2 is complete offline: 2,664 AB tests, 85 root tests, 75 focused checks and
25 native-capture replay/writer/storage checks pass. The fresh Dart gateway
suite has 44 passes; locked dependencies, analyzer, host compile and CLI check
pass on Dart 3.13.4. Records are in `C:/work/fraktal-ab-c5b2-control-20261106/`.
This increment migrates the Phase 6 set fixture and the shared
`Run.restore_configuration` branch for collapsed profiles. It does not qualify
the remaining Part/genealogy/access/data/shelving harnesses as a whole.

- The set fixture commands through O11 and independently reads exports,
  catalog entries and named rejections from canonical CIP rows. It waits for
  the PLC's published ConfigPersist receipt, not just the command ACK. Ordinary
  cleanup requests remain possible after an adapter failure; a set request
  cannot proceed without its live owned adapter.
- The existing Dart V6.11 adapter owns the files and every keep/restore job.
  Python provides a process lease, an opaque seed copy and read-only file
  comparisons. The collapsed branch constructs no broker or keeper.
- Gateway and adapter share the process/close boundary. Both are executable-
  hash and target pinned; only their owned children are closed. Adapter startup
  checks for another recognized Echo adapter. Serving roots and failures come
  from the child's JSON status; failure is latched and there is no restart.
- Every adapter uses a fresh isolated store. `fraktal_ab_harness_seed.py`
  records confirmed original live files and their hashes, outside the original
  folder. Named sets are opt-in; unrelated files and unconfirmed leftovers are
  excluded. The adapter opens a copy, and original source hashes are checked
  afterward. A shared restore requires its prepared seed; it cannot silently
  substitute an empty medium for original documents.
- Live verification reads all configured keys, kinds, readable values and
  model banks through the published V6.8 view, and the active/catalog identities
  through Core paths. It brackets the catalog with the configuration revision.
  It compares every expected portable record against confirmed medium files,
  including current document revisions. It supplies no missing/masked value.
- The V6.11 reply is read from its published Symbol and native Template in one
  CPS-protected structure read. Fragmentation refuses. This host status is not
  a canonical freshness certificate; ordinary values retain their row proofs.
- Originals are captured after Dart restoration. All station values and four
  fixture set names are restored independently; final checks include every raw
  record, original-medium hashes and every kept live document. A failed final
  check does not skip the others or closing the owned child.

The press enables the already approved V6.11 host binding. Its eight set
operations now advertise `RequiresSetStage=false`; Frame/staged endpoints are
still present for the remaining migration. O10 grows 40 to 75: the remaining 32 record
members, set SchemaVersion/AuditSequence, and RestoreLost join the earlier
facts. The 35 additions replay from the old 86 accepted captures. The six
ConfigAudit fields remain without old raw bytes and await native S6-Q.

The existing set-case predicates match after normalizing only acquisition,
the read-only portable file reopen, and deployed key lookup. The old Python
connection-state denial is replaced by the packaged read-only gateway policy
case, preserving refusal and unchanged sequence. Model loads retain their
existing refusal; the adapter's live restoration is a separate owner route.

The press passes both v38 builds/read-backs/defaults/access and measures
1,703,672 used / 1,442,056 available / 3,145,728 Blocks (54%), 149,244 more
used than C5b1. The frozen C5b1 code, with only host services enabled, has 65
identical other routines; the fixture's exact 35 fact copies are its sole
code delta. Genealogy remains byte-identical, with prior hash-bound 60%
qualification. No controller operation or native scan measurement ran.

The first access audit expected HostRingRevision for every host-enabled image.
The press advertises no HostEvents, so that tag is correctly absent. The
corrected audit requires it only when the service is advertised; all actual
top-level/member access checks remain. The initial token helper compared a
list to a tuple; its fresh corrected run passes. Failed runs are retained.

Prepared runtime inputs are `FRAKTAL_HARNESS_HOST_ADAPTER` and its `_SHA256`,
`FRAKTAL_HARNESS_HOST_SEED` and its `_SHA256`, plus the existing gateway pins
and optional `FRAKTAL_HARNESS_OUTPUT`. Source seed files are never archived.
This fixture copy makes no production persistence-medium decision.

Remaining C5 work: account/migrate the other HX readers and launchers, then
remove Frame/staged endpoints and publish V6.12 in C5c. C6/C7 and native S6-Q
follow. Native set receipts, original-document restoration, scan/retention and
the complete HX walk remain unproven on the collapsed image until that gate.


## C5b3 policy slice - access, data classes and shelving

C5b3 policy qualification passes offline: 2,681 AB tests, 85 root tests and
63 focused checks pass, along with 25 replay/storage checks and the separate
annotation replay. Records are in `C:/work/fraktal-ab-c5b3-control-20261106/`.
This slice migrates the three Phase 6 policy fixtures. C5b3's other HX
consumers and launchers remain open; this is not C5's exit.

The collapsed fixtures read exact native access/session, audit-slot, alarm and
Start-release facts through O10. The 27 appended fields retain DINT values and
full native extents, including signed audit/login serials and current-user
byte cells. All 27 occur in all 86 accepted press captures. The fixture now has
102 facts; the native audits absent from the older captures remain S6-Q's.
Public class policy, selected configuration metadata/values, alarm text and
annunciation come directly from their canonical paths. No Python formatter
supplies those values. Configuration acquisition reads only the active values
of the three keys the data fixture consumes; other model-bank value text is
not acquired. Audit descriptions are separate row proofs, never a whole-ring
certificate, and single-slot checks acquire only their consumed slot.

A shared command-side-table reader owns native Template/extent validation,
packet bounds and root-revision checks for both keys and capability IDs.
Sparse published IDs, not generator ordinals, govern the data-audit assertion.
Only complete validated activation metadata is cached on the guarded session;
no cyclic state is cached. Configuration probes use typed identity, text and
live revisions. The old direct Frame probe becomes one O11 request with an
independent CIP acknowledgement; the collapsed branch neither invokes a
legacy writer nor reinitializes the existing adapter. Claimed-user denial,
no-change, actual actor/level and time-bound predicates remain.

Client context ownership now encloses the original snapshots. Login keeps its
own modulo-uint32 result correlation and polls the PLC's published timeout;
invalid timeouts refuse before a PIN is sent. Each fixture retains independent
policy, timeout, value and session restoration. The data fixture explicitly
deletes its isolated named set before logout; this replaces disposal of its
old temporary Python store. Shared finalization checks all original records,
original medium hashes and every kept document, and closes owned helpers even
when a prior check fails. The primitive stimulus guard remains the existing
identity-only HL helper; legacy branches/imports retire with WP6.7.

The executable delta from C5b2 is exactly 27 fixture copies: 65 other routines
are identical. ST tokens increase 115,596 to 116,007 (+411). Both v38 targets
build/read back and pass access/default/SDK audits. Studio Capacity is
1,713,204 used / 1,432,524 available / 3,145,728 Blocks (54%), +9,532 used.
Genealogy is byte-identical and retains its hash-bound 60% qualification.

Early failures are retained: the cleanup test double lacked the newly required
context/close boundary; the first predicate helper missed an acquisition
alias; the schema summary printer used the wrong result field name after a
passing comparison. Corrected focused/predicate/schema runs pass. No PLC
algorithm or acceptance predicate was changed to resolve them.

No controller operation or native scan measurement ran. Shipping HMI/Dart
sources and both prepared runtime executables match the sealed C5b2 bindings;
its 44-test Dart/analyzer/locked-dependency qualification is reused by hashes.
The full Flutter suite/UI builds are not rerun for unchanged shipping sources.
The seed-copy workflow makes no production persistence-medium decision.

Next: remaining Phase 5 OEE/report/metric reads, Part/genealogy and inherited
runners, and the standalone canonical press launcher need their own fact and
predicate accounting. Frame/staged retirement/V6.12 stays behind those
migrations. C6, C7, native S6-Q, final retirement/spec activation and physical
S7 acceptance follow. Native policy/security/retention, original document
restore/keep and scan acceptance remain unproven on the collapsed image.

Native eligibility finding: the base press has `require_controller_metrics=False`,
while the original shelving fixture requires metrics-unavailable reason 21.
The accepted idle input and the parent/migrated preflights both refuse that
precondition. Preserve the base exclusion and the guard. A dedicated shelving
acceptance profile/event precondition remains before positive native shelving
acceptance; the offline migration does not close this gap.


## C5b3 shelving acceptance profile - offline follow-up

The [dedicated profile qualification](Evidence/AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06.md) passes:
2,689 AB tests, 85 root tests, 52 focused service/profile checks, both v38
build/read-back/access/default/SDK gates and 54% Studio Capacity
(1,713,240 used / 1,432,488 available / 3,145,728 Blocks, +36 used versus
the normal press). Only the optional metrics requirement changes: nine added
ST tokens in ScanHealth, 65 routines unchanged, identical public schema,
initial values and manifest hashes. The existing 102-field fixture remains.

`fraktal_ab_press_s6_shelving_echo38` supplies the standing reason-21 warning
through the existing health/alarm owner after its first-sample guard. The
normal press keeps the exclusion, and every original eligibility/session
guard remains. This is offline service/preparation proof, not a typed-wire,
gateway, scan, retention or native shelving acceptance result. S6-Q after C7
now sequences genealogy, the dedicated shelving profile, then the normal
press, ending on the qualified genealogy baseline. Rebuild/requalify the
profile after intervening collapse work. No controller operation ran.

All shipping HMI/Dart/runtime bindings are unchanged; the hash-bound C5b2
44-test package qualification is reused. Early failed setup/proof/receipt
runs are sealed, with corrected fresh runs passing. Owner edits remain out.
The next source inventory finds 18 direct legacy calls/21 row sites in Phase 5
and three calls in Part; genealogy delegates its reads. Phase 5 also requires
reason 21. Those migrations, inherited reads and the canonical launcher are
next, followed by C5c/V6.12, C6/C7 and native S6-Q. O5 already chose FileMedium;
O2 defers hardware-only S7 without a date as a declared exclusion. Revisit
software CIP Security only after S4b-S6 exit.


## C5b3 Phase 5 metrics and reports - offline qualification

The [Phase 5 migration record](Evidence/AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06.md) passes offline:
2,696 AB tests, 85 root tests, 62 focused checks and 27 native-capture
replay/storage checks pass. `fraktal_ab_phase5_execute.py` has zero direct
legacy projection or layout calls; all 21 row predicates and 16 wait predicates
are preserved. O10 grows from 102 to 141 facts (+39) in `FRK_T_PressFixtureV2_2A276D94`,
shared across the normal press and the shelving acceptance profile. Cylinder
`TimCount`/`TimLast` are read as canonical public aliases from `Timing/Rows[1..2]`
because C1/R3 removed duplicate timing arrays from collapsed module contexts.
All 39 added private facts and all canonical metric/report readers (`oee_card`,
`machine_summary`, `run_style_offer`, `profiler_summary`, `timing_row`,
`alarm_ring_entry`, `state_flags` and `system_health`) match across all 86
accepted native press captures.

Promoting the five asserted cylinder fields to AOI `Output` parameters under
C4c updates the derived C4 AOI hashes and V5 field/localization numbering;
refusal keys in Phase 5 resolve from the deployed PLC command table via
`views.numeric_key`. After removing the 39 appended O10 copy statements (+552
ST tokens) and normalizing C4c AOI names, V5 numeric keys and four equivalent
text-pool slices, all 66 routines match the prior C5b3 sources token-for-token
(`125,551 -> 126,103` ST tokens on the normal press; `125,560 -> 126,112` on
the shelving profile). Both v38 profiles build/read back on both targets, pass
SDK/access/default audits, and fit at 54% Studio Capacity (1,726,208 Blocks on
normal press, +13,004; 1,726,244 Blocks on shelving profile, +13,004).
Genealogy remains byte-identical to C5a (60% Capacity), and shipping HMI/Dart
sources and runtime executables remain hash-bound to C5b2 (44 Dart tests).

Phase 5's `health_rows` requires standing reason 21 (`CONTROLLER_METRICS_UNAVAILABLE`),
which `fraktal_ab_press_s6_shelving_echo38` supplies after its second health
sample while `fraktal_ab_press_s6_collapse_echo38` keeps `require_controller_metrics=False`.
Next in C5b3: migrate `fraktal_ab_part_execute.py` (3 direct legacy calls),
`fraktal_ab_genealogy_execute.py`, inherited runners and
`fraktal_ab_press_canonical_execute.py`, then retire Frame/staged endpoints and
publish V6.12 in C5c before C6/C7 and native S6-Q.


## C5b3 Part/genealogy acquisition slice - 2026-11-07

The [acquisition record](Evidence/AB_S6_COLLAPSE_C5B3_PART_READS_OFFLINE_2026-11-07.md) passes offline: 2,707 AB tests,
85 root and 74 focused tests; 25 checks/11 waits preserved; 40-leaf Part/native-result and
HostEvents replays; both v38 target/read-back/access/default/SDK gates; 60%
Capacity (1,916,892 used / 1,228,836 available / 3,145,728 Blocks,
+1,272). O10 grows from one to thirteen facts for the Part recovery matrix.
Twelve exact copies add 111 ST tokens; all 72 routines otherwise match.
Other public data and the three manifest hashes remain identical. Both press
profiles regenerate byte-identically and reuse their 54% qualification.
The lightweight fresh manifest pin uses discovered native Templates; no
cached activation value substitutes for the read. Shipping Dart is unchanged.

This is the acquisition slice, not a complete runner/C5 exit. Next are the
inherited tower bootstrap/snapshot/configuration reads and document-preserving
isolated host lifecycle, including the explicit disconnect boundary, then the
canonical press launcher. Existing predicates and disconnect time bounds stay.
The previous Phase 5 narrative genealogy hash is corrected by this new record:
the artifact-bound source is `5557604A...273A95A`, not `07C771DF...36DB417`.
The old evidence stays immutable. No controller operation ran. C5c/V6.12,
C6/C7, native S6-Q and final retirement/spec activation remain open; O2/O5
remain decided as recorded in the plan.


## C5b3 shared runner and disconnect lifecycle - 2026-11-07

The [shared runner record](Evidence/AB_S6_COLLAPSE_C5B3_RUNNER_OFFLINE_2026-11-07.md) passes offline:
2,716 AB tests, 85 root tests and 71 focused checks pass, with zero controller
operations. All 5 migrated shared/inherited runners (`fraktal_ab_tower_execute`,
`fraktal_ab_part_execute`, `fraktal_ab_genealogy_execute`,
`fraktal_ab_resource_execute`, `fraktal_ab_text_resource_execute`) have zero
unguarded collapsed-reachable legacy calls while retaining 20 legacy-branch
calls strictly behind `not app.canonical_collapse` until WP6.7.

- `views.signal_tower` reads canonical `MachineState` and the seven
  `SignalTower/*` leaves under one scan-counter row proof and replays
  identically over the sealed S6 native capture.
- `read_seed_files` in `fraktal_ab_harness_host` is the single validation owner
  shared by `seed_store` and `seed_documents`; `compare_seed_documents` in
  `fraktal_ab_harness_documents` checks invariant headers and record payloads
  across image revisions while recording `previousRevisions` and
  `currentRevision`.
- Collapsed `Guarded` restricts `allowed` to `externally_writable(app)` (O11)
  and `frozenset()` on read-only observers, and owns explicit connection phases
  (`close_phase`, `open_new_phase`, `open_observer`, `check_owned_leases`,
  `originals_unchanged`). Before `LAMP_TEST`, `exercise` pre-opens and warms a
  read-only `observer`; `close_phase()` closes the primary session and its owned
  gateway/host leases, preserves the complete `disconnected = 3.2` s quiet
  interval with zero traffic, and reads the expired tower row on `observer`
  within `elapsed < 4.0` s without restarting or clearing any latched
  `ProcessLease` failure. `execute_fixture`'s `finally` opens phase 2 if
  `_phase_closed is True` so cleanup and restoration still run after a
  mid-disconnect failure.
- Zero PLC/L5X or shipping HMI/Dart sources changed; all three collapsed L5X
  profiles (`57FDB0BC...`, `0E3E19A8...`, `D7FB6960...`) regenerate
  byte-identically, reusing their 60% and 54% Capacity qualifications and C5b2's
  hash-bound 44-test Dart/runtime qualification (84 shipping sources). Failed
  preparation runs and `ab_full_suite_01` (`Mock` truthiness on `_phase_closed`,
  fixed with `is True`) remain sealed.

Next in C5b3: migrate the standalone canonical press launcher
(`fraktal_ab_press_canonical_execute.py`), then account/migrate the remaining
station-reading HX harnesses (`fraktal_ab_press_parity.py`,
`fraktal_ab_phase1_execute.py`..`fraktal_ab_phase4_execute.py`, and
`fraktal_ab_s3_execute.py`; `fraktal_ab_s9_{mutations,read_execute,write_execute}.py`
retire with RT/MO, and `fraktal_ab_mailbox_execute.py` uses the gateway
WebSocket protocol directly) before C5c/V6.12, C6/C7 and native S6-Q.


## C5b3 standalone canonical press launcher - 2026-11-07

The [launcher record](Evidence/AB_S6_COLLAPSE_C5B3_LAUNCHER_OFFLINE_2026-11-07.md) passes offline with
zero controller operations. `fraktal_ab_press_canonical_execute.py` accepts
`fraktal_ab_press_s6_collapse_echo38` and `fraktal_ab_press_s6_shelving_echo38`
and runs `PressRun` through the shared runner without any MO import path being
taken: no `typed.authorize`, `paired_run`, S3k equivalence gate, projection or
legacy keeper. A standalone `authorize` keeps all seven exact-image approval
checks (serial, pin, owner and write approvals, fault-clear and clock-set
explicitly false).

- First commissioning reads the downloaded image's V6.8 configuration view via
  `expected_documents`, brackets it with `Status/ConfigRev`, writes the five
  live documents into an empty isolated medium beside the output, and records a
  hash-pinned seed manifest via `fraktal_ab_harness_seed.record`. The shared
  runner's preservation row then compares against that manifest. Over the
  emitted press view, the seeded documents equal legacy `fraktal_ab_live.documents`
  content for both profiles.
- The medium must start empty: an existing seed variable, manifest, index or
  document refuses, as does a revision change while seeding. The launcher
  clears the isolation and seed variables in `finally`, including when the
  inner runner refuses its arguments.
- `PressRun` keeps its C3 AST byte-for-byte (the predicate gate in
  `test_fraktal_ab_fixture_reads` caught a first attempt that rewrote its hold
  wait; `px.read_module` already routes to the O10 view under C5a). All 10
  original checks, 6 waits and the 0.75 s hold bound are preserved. Zero
  unguarded collapsed-reachable legacy/MO calls remain across six runners.
- An end-to-end simulated run on both profiles yields 23 passing rows (two
  leading rows plus seven core cases in each of ST, SFC and LD), with full
  restoration, policy restoration and original-medium checks.

No PLC, L5X or shipping Dart source changed; all three collapsed profiles
regenerate byte-identically and reuse their 60%/54% Capacity and C5b2 44-test
Dart qualifications. Next in C5b3: `fraktal_ab_press_parity.py`,
`fraktal_ab_phase1_execute.py`..`fraktal_ab_phase4_execute.py` and
`fraktal_ab_s3_execute.py`, then C5c/V6.12, C6/C7 and native S6-Q.

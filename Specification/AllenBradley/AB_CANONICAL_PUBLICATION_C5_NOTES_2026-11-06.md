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

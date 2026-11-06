# S6 WP6.6 C5a - gateway commands and selected fixture reads

2026-11-06. Entry main commit `43201509f`. Offline qualification only.
No controller connection, download, tag write, mode change, fault/TASK-counter
clear, clock change or power operation was performed. C5 remains open.

## Change and preservation

Collapsed `px.command`/`px.manual` send the nine Core arguments then Sequence
through O11's brand-neutral writeBatch client. The Dart gateway remains the
one native command encoder. A supervised child is pinned by executable hash,
immutable serial/slot endpoint, root, process liveness and unique readiness
identity. Wrong packages, listeners, targets or write policies refuse. Each
request observes the PLC's acknowledgement independently over CIP; there is
no retry, queue or native-write fallback after an ambiguous failure.

pylogix PLC is slotted, and its context exit calls conn.close directly.
Apparatus state and gateway cleanup therefore belong to that connection.
Tests exercise the installed driver without connecting it and close both of
its initial sockets. Cleanup terminates only the owned stateless gateway.

O10 V2 reads selected native members, including full DINT arrays with their
Template counts. The same progressing scan proof covers canonical and private
facts; neither owner windows nor freshness limits are enlarged. Whole-V1
reads remain supported. V2 shape signatures prevent different layouts sharing
one type name. Press carries 29 prior private facts plus Mailbox.DiagnosticKey;
genealogy initially carries only that key. The fixture is Read Only and never
enters the manifest. It contains no credential or command input.

The old legacy ACK is not a Core ACK alias: two accepted native press captures
show different cursors. Commands co-read the Core request/ACK/Accepted/
Diagnostic plus the raw numeric key instead. All 86 accepted native-state
replays preserve the accounted facts and unchanged case/wait predicates.
These are offline replays with synthetic later metadata, not native C5 runs.

The collapsed press now emits the already approved V6.7 scan bindings. Its
frozen S3 parent is V6.6; the old C4 replay overlaid those bindings. The new
emitted-header test checks actual prefixes, counter, protocol and period.
The schema gate declares this addition explicitly. No new contract decision
or canonical value change is introduced.

## Results

- **2,612 AB tests pass**, by full discovery on 448 frozen tool
  sources/fixtures. Final bytes match that freeze. The completed preceding
  run had one obsolete storage-test assumption; its correction passes all
  ten storage tests, and the final full discovery rerun passes.
- **85 root tests pass**; AB specification/contracts and strict consistency
  pass. All 37 command/lease tests and nine fixture image tests pass.
- **44 Dart gateway tests pass**, locked dependencies, analyzer, executable
  compilation and CLI help pass. All 84
  tracked gateway/client files are byte-identical to the entry commit.
  Dart 3.13.4 was used from the Flutter 3.47.5 toolchain under C:/work.
  The full Flutter suite was not rerun because no HMI source changed.
- **Both profiles build and read back on both v38 targets**, EchoController
  and PhysicalController. SDK, effective-access and per-instance/default
  audits pass. New outputs regenerated from the final sources are identical.
- **Schema identity and exact executable-token proofs pass.** Only the
  accounted diagnostic-key copy/call changes executable code. Existing Core
  values and ST/SFC/ladder graphs remain unchanged. The two frozen legacy
  declarations regenerate byte-identically.

| Profile | Used Standard | Available | Total | Studio display |
|---|---:|---:|---:|---:|
| Genealogy | 1,915,620 | 1,230,108 | 3,145,728 | 60% |
| Press | 1,447,072 | 1,698,656 | 3,145,728 | 46% |

Capacity units are **Blocks**, from offline Studio Capacity Estimate on
hash-checked review copies. These are not native scan/retention measurements.

Genealogy source SHA-256 `5557604A02885ECE5C67392B552F41F15FDC9B747ED139E275D987064273A95A`; ACD `58582B5295887E84BBD167C5AB1EDE75ED88DBA8D4B56E624A4DFED2D2F8D5E4`.
Press source SHA-256 `AE5A783348AFF67DABC48E9FEF281F12E78C305C7608E23A4DB7C3DF426B4F19`; ACD `9313CD2EDEF50D012BDED3548FE9F21B2F041F2F69A3654A98539B0E5A0E1BF3`.
Inputs, read-backs, preparation executables, seed and compiled gateway are
bound by hashes. Generated L5X/ACD/EXE binaries are not copied into the payload.

## Retained failures and corrections

The payload retains every failed/superseded run, including:

- `private_selection_01`: the malformed Template was refused earlier than
  the new test expected; its expected-refusal scope was corrected.
- `command_adapter_baseline_01`: the legacy/Core ACK mismatch above.
- `observation_v2_01`: the old 29-fact/no-genealogy-fixture expectations.
- `gateway_close_01`: the actual driver is slotted; its exit also bypasses
  PLC.Close. State/cleanup moved to the owned connection. Later socket
  warnings in the two new tests were corrected by closing msg_socket too.
- `coherence_focused_01`: a decorated L5X record was incorrectly treated as
  the typed S1 wire decoder's output. The emitted identifiers/counts are now
  checked and compared with validated V6.7 metadata.
- `access_genealogy_EchoController_01`: an over-strict new member-only rule
  ignored the Read Only parent tag. Effective access is the intersection of
  tag and member access; unreadable members still refuse.
- `preparation_02`: a private wrapper referenced a stale S3j work-folder path
  after successful builds; no ACD preparation ran at that failed step.
- `access_press_EchoController_03` / `preparation_03` / `qualification_03`:
  genealogy's three optional public owners were wrongly expected on press.
  The audit now removes only those exact expectations when their declaration
  disables the owner; unexpected access still fails.
- `ab_suite_01/02/03`: intentionally stopped owned Python runs, with reasons
  recorded separately (socket cleanup, verified newline-only normalization,
  and the missing emitted V6.7 prerequisite). They qualify no final source.
- `ab_suite_04`: 2,612 tests, one old test error treating Mailbox as a module.
  The module-parameter assertion now excludes scalar record owners, whose
  copy/access is tested independently. No accepted case predicate was relaxed.

Successful artifacts are reused only through exact source/read-back hashes.
Earlier files are never overwritten. Bench credential files were neither opened nor archived.

## Remaining work and next step

This qualifies the shared command path and basic collapsed press walk offline.
It does not qualify every old harness merely because it calls px.command:
legacy operation-specific arguments, reads, set clients and restore lifecycles
still need migration. The private C5b catalogue records 303 literal call sites
and 127 candidate predicate hashes across 24 HX modules; these source counts
are not runtime coverage or an accepted private-fact census.

Next, account those facts per instance/read site, migrate the remaining
configuration/access/set and standalone canonical fixtures, and use the
V6.11 host adapter instead of Python broker/keeper interception. Press needs
the already approved configuration-view/owner/host publications for those
clients. The approved read-only configuration RPC replaces an old viewer's
QUERY_CONFIG mailbox assumption; no write exception is enabled.

Then remove Frame/staged endpoints and publish/read V6.12. C6 removes legacy
exposure/tables, C7 selects production AUTO, and native S6-Q proves integrated
regression, coherence, scan and retention before retirement/activation. S7
remains physical CIP Security acceptance. The frozen V2 target stays inactive.

Payload: [AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06/artifact_manifest.json](AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06/artifact_manifest.json).
Manifest SHA-256 `12211B9D7821534793ABFD00B921C17C99DB4E824AEEE699E1543FBFF25723BD`. Gate receipts, failed logs, source bindings,
proofs and private preparation scripts are included; no credentials or
compiled binaries are archived.

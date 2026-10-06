# Fraktal/AB Phase 6 item 1 — capture and read-only configuration, offline build

**Date:** 2026-10-01, America/Bogota. **Stage:** generated and tested offline;
owner Studio import, Verify/download and guarded controller verification pending.
Parent revision: `0a9c850`. No controller writes or download were performed.
The last verified bench build is press53; this record does not supersede its
[hardware measurements](AB_PHASE6_ROOM_ON_HARDWARE_2026-10-01.md).

## Generated artifacts

The declaration and generator emitted both files from `C:\work\seed_v33.L5X`.
Neither L5X was hand-edited; both reproduce byte-for-byte from current sources.

| Property | Press | Station template |
|---|---|---|
| File | `C:\work\press54.L5X` | `C:\work\phase6_capture_template.L5X` |
| SHA-256 | `703B896F0A8FED206612D08E44F0A976A5DBF4F4C5AEE5D4ED31E606FF18E6BC` | `890DF7211B2326F0DFA42671057BD60E80CCE56E8CFD144C3ADEB366F18C9C3E` |
| ContentHash | `287D251E9DD97551` | `7604048C7D8F36D6` |
| ConfigRevision | 2653477 | 7734276 |
| Manifest major | 3 | 3 |
| Manifest bytes | 79,992 | 79,992 |
| Fields | 499 / 768 | 313 / 768 |
| Localization | 477 / 768 | 388 / 768 |
| WriteCapabilities | 9 / 64 | 4 / 64 |

`CaptureSourceKey` appends one DINT to the versioned V3 capability row, adding
256 bytes at capacity. The major change prevents an old reader from interpreting
the larger layout. The generation budget rises to 102,400 bytes (100 KiB), keeping
the tested 80-character key envelope of 98,472 bytes inside the bound. Capacity
and byte-budget overflow still refuse generation before producing a file.
[S7's cost curve](AB_S7_MANIFEST_EVIDENCE.md) projects about 536/113 ms for this
build and 686/144 ms for the budget, at 500/4000-byte connections. These are
estimates; actual read time and coherent row equality await controller readback.

## Capture behavior

`decl.capture` registers one source beside an existing editable scalar. Source
validation uses the same authoritative root-field list as the manifest: no
private scalar, array, other module or free-form expression is accepted.
The press and template teach their editable `BaselineWorkMs` from their own
published `Profiler.LastWork`, also shown by the generic cycle profiler.
This bench has no Integrated Motion axis to provide a taught position.

The gateway resolves `(Scope, WriteKey)` to the declared ordinal, retains the
capability revision and zeros the client's candidate. The PLC samples the
registered source and checks that revision, manual setup mode, root Error/Aborted,
the root's declared start/release permissives, and ordinary write readiness and
range. It then uses the same storage path as a typed write. Capture always targets
the current record, matching TC3. Unknown, foreign, stale or unregistered
captures refuse by name and change neither configuration nor accepted-write audit.

Typed writes and captures record accepted values in the same 16-entry controller
audit: request sequence/kind, field capability, stored value, capture source key,
model, contract revision, controller date/time and claimed actor. Wrap is bounded
and replaces old actor bytes. Audit structures are read by dimension-aware layout.
The published CIP audit is read on demand by hosts and the fixture; it is not
added to every cyclic HMI snapshot or allowed to change discovery during an ack.

## D5 in both gateways

A complete `QUERY_CONFIG` page/model batch is a logical read, even though it
stages a transient request and sequence in the mailbox. The AB viewer may use
only its canonical station root; TC3 requires a discovered, readable Unit.
Kind, page, model and final Sequence must be present and valid; unused strings
must be empty and BoolValue false. Nested/unknown members, nonempty unused
arguments, single-member staging and every other kind retain the mutation gate.

Both routes preserve their ordinary sequence discipline and serialize shared
mailbox transactions. A failed AB transaction changes neither sequence bookkeeping
nor the connection's selected configuration model. A mutation still requires the
deployment's write scope and authentication. No AB HMI screen was added.

## Offline verification

- AB suite: 1324 tests passed.
- HMI suite: 428 passed, 6 skipped; TC3 gateway subset: 24/24 passed.
- Flutter analysis: no issues.
- Consistency: 0 errors, 0 warnings; suite 32/32 passed.
- Python mutations: 18/18 killed, exercising sampled value, revision, mode,
  permissives, readiness, range, registration, audit/wrap/source/actor replacement,
  identity resolution, query kind/arguments/scope, serialization and restoration.
- TC3 gateway mutations: 4/4 killed, removing kind, inert-argument, direct-member
  or readable/discovered-root checks. The baseline and each compiled mutant ran
  all 24 tests in an external copy; repository Dart source was never mutated.

Python gates used `-B`, disabled bytecode writes and fresh cache prefixes.
Python mutations changed imported code in child memory only.

XML comparison with actual press53 shows unchanged module AOIs, I/O and tasks.
Only `FRK_PressHmiMailbox` changes behavior; Main differs solely in regenerated
interned diagnostic key numbers. Added tags are the read-only audit and private
candidate scratch; added types are the audit and V3 capability row. Manifest
tables/header update together. The native SFC graph remains byte-identical:
18 steps and 21 transitions. The full suite also checks the ST/SFC/LD renditions.

The new `fraktal_ab_phase6_execute.py` checks serial and fingerprint before any
write, begins with two read-only rows, and requires `--execute-fixture` for its
ten-row verification. It tests a pinned gateway object with no credential or
write root, then capture against an actual completed plant cycle, stale/foreign/
unregistered requests, setup mode and air permissive. Finally it attempts every
baseline/mode/run-style restoration, reads them back and disarms all fixture
inputs. Five offline guard tests prove refusal and cleanup, including failures.
The hardware harness has not yet run.

## Deployment and claim

The posture remains the v33 legacy zone-and-conduit bench, write-enabled by the
owner's 2026-09-29 decision. This item widens that write surface with registered
captures. Phase 6 will add sets, login and shelving. Per-user controller sessions
and `DATA_WRITE` enforcement remain item 3: an audit User is currently the
request's claim, not an authenticated controller principal. The write-enabled
claim remains **owed until S9 passes**.

The handover assigns import, Verify and download to the owner on the licensed
desktop; the recorded SDK probe reports **No valid license** on this workstation.
Import `C:\work\press54.L5X` in Studio 5000 v33, run Verify Controller, download
to `192.168.100.89`, serial `7036B510`, and restart the gateway. The owner's
`done` authorizes the named guarded verification harness writes on that target.
First expect manifest `passed: true`, major 3, 79,992 bytes and the hash above;
then gateway readiness, S3, parity, Phases 1–5 and the new armed Phase 6 harness.
No hardware completion is claimed by this offline record.

The [JSON record](AB_PHASE6_CAPTURE_BUILD_2026-10-01.json) includes generator
reports, artifact hashes, scope comparison, mutation results and gate summary.

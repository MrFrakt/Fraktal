# Fraktal/AB Phase 6 item 2 — parameter sets, offline build

**Date:** 2026-10-02, America/Bogota. **Stage:** generated and tested offline;
owner Studio v33 import, Verify/download and guarded verification pending.
Parent revision: `bb0a141`. No controller writes or download were performed.
The last verified bench build is press54; this record does not replace its
[hardware measurements](AB_PHASE6_CAPTURE_ON_HARDWARE_2026-10-01.md).

## Generated artifacts

The press and station template were generated from `C:\work\seed_v33.L5X`.
Both reproduce byte-for-byte; no L5X was hand-edited.

| Property | Press | Station template |
|---|---|---|
| File | `C:\work\press55.L5X` | `C:\work\phase6_sets_template.L5X` |
| SHA-256 | `AF0DFBC9080296BDC5E8D8D92BCD3464CBFDF3C6D276CE04A192F6594E9D3A23` | `E78B6F1912C376CF3BB2EAFA70C372C7A5725C175954247ADE8BB3A5EB1B04F4` |
| ContentHash | `5A1BD77C6D63F5FD` | `60F474017C3C8BF2` |
| ConfigRevision | 5905367 | 6354036 |
| Manifest major | 3 | 3 |
| Manifest bytes | 79,992 | 79,992 |
| Fields | 526 / 768 | 340 / 768 |
| Localization | 514 / 768 | 425 / 768 |
| Rationalization | 23 / 32 | 19 / 32 |
| WriteCapabilities | 9 / 64 | 4 / 64 |

The manifest capacities and 102,400-byte budget are unchanged. Its tested
80-character key envelope remains 98,472 bytes. The earlier measured press54
read time is historical; press55 coherence and runtime cost await readback.
New DINT storage is bounded: request payload 1,652 bytes, private copy 1,652,
read-only state 7,900 (template 7,880), three loop scratch values 12. The total
addition is 11,216 bytes on the press, before platform bookkeeping.
Audit/name storage dominates this cost; its layout is read on demand, not added
to every cyclic HMI poll. The snapshot array follows actual editable count.

## Controller-owned transaction

The declaration's editable walk is the sole schema authority, shared by
WRITE_CONFIG, capture, the manifest and set translation/validation. Six kinds
route: SAVE, LOAD, LIST, EXPORT, IMPORT and DELETE_CONFIG_SET. The existing
ACK_CONFIG_RESTORE route keeps its reported-loss gate.

HmiRequestV2 preserves the original member prefix and appends a versioned DINT
ConfigSet payload. The Web client continues using the original members;
arbitrary nested payload writes remain refused. The broker stages every argument
before Sequence, and holds the gateway's shared mailbox lock through the answer
and store receipt. Native CIP is untrusted; per-user controller access is still owed.

On dispatch, CPS copies the payload into a controller-private, externally
inaccessible tag. Pass one checks root/schema/revisions, payload sequence and
kind, bounds, READY, every registered capability/type/kind/range, and duplicate
or unknown identities. Pass two applies values only after every check succeeds.
No child WRITE_CONFIG transactions are issued. Invalid last records cannot apply
valid earlier records; tests also alter the external payload after the private
copy and prove it cannot change the committed values.
Rockwell documents same-type whole-structure copying and ST
`CPS(Source,Dest,Length)` for CompactLogix 5370 in its
[CPS reference](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/array-file-misc-instructions/copy-synchronous-copy-file--cps-.html).
The private-copy/interlock design follows that guidance; this is not a Studio
v33 compile result or an adversarial CIP security measurement.

Save snapshots the controller's live values and timestamp. Station loads apply
the validated transaction in one scan. Model save/export works; model load
explicitly refuses until recipe-store integration, matching TC3. This binding
has no Line owner, so Line saves/loads refuse. A 16-entry controller ring records
accepted and refused requests, first bad record, timestamp, name and claimed User;
bounded wrap clears unused name/actor bytes.

## Gateway-owned document and medium

The existing generic HMI sets dialog uses connection-local catalog, export and
rejection answers. A refusal reads its offending scope/key directly, before the
next cyclic snapshot. Read-tier exclusions keep these answers out of requested
cyclic streams while preserving targeted reads. The underlying controller
projection still polls as a whole; slow tiers do not reduce that poll yet.

Each commissioned root/serial owns a four-name host directory. The default is
`%LOCALAPPDATA%/Fraktal/ConfigSets/<serial>-<root>`; deployment may provision
`FRAKTAL_AB_CONFIG_SET_DIR`. SHA-256 filenames make names data, never paths.
Replacement flushes/fsyncs a temporary file then atomically replaces the exact
target. Failure preserves the previous document; no recursive deletion is used.

Portable JSON lines use TC3's field order and exact record counts. They refuse
duplicate JSON members, malformed fields, unsupported text and oversize rather
than truncating. The frozen AB transport bounds ASCII lines at 480 characters,
fragments at 255, names at 80 and records at 64. Partial imports belong to one
connection; another command, malformed piece or early commit aborts them.
Import stores a document and never applies equipment values. Foreign documents
may be stored/exported, but their load fails controller validation.

Save/delete/final import expose Pending until a matching host file receipt, for
at most 5,000 ms. Failed I/O or expiry publishes CONFIG_PERSIST_FAILED and updates
the originating audit/refusal if still current. A later query/list cannot retarget
the pending sequence. This receipt describes document storage, not physical
retention of ordinary configuration writes. Power-cycle/download/upgrade
retention remains **provisional** pending its measured matrix.

## Offline verification

- AB suite: 1,363 tests passed; consistency 32/32, 0 errors and 0 warnings.
- HMI: 429 passed, 6 skipped; Flutter analysis: no issues.
- Python mutations: 23/23 killed, each running the same 64-test baseline.
  They remove identity/schema/revision/type/kind/range/READY/duplicate checks,
  permit partial commits and mutable payloads, substitute client snapshots,
  break audit wrap and receipt expiry, loosen JSON/import bounds, destroy atomic
  replacement, permit post-commit replay or omit fixture restoration.
- HMI mutations: 2/2 killed with all nine repository tests executing: stale
  refusal reads and lost offending keys.

Python mutations execute changed source in child memory only, with `-B`, disabled
bytecode writes and fresh prefixes. HMI mutations run in an external copy;
repository source is never mutated. XML comparison against actual press54 shows
unchanged module AOIs, I/O, tasks, native SFC graph and native ladder routine.
Only Main and the HMI mailbox routine change. Both declarations use the same
feature implementation; disabled declarations keep named refusals.

The new `--sets` fixture retains the parent serial/fingerprint/read-only gates
and explicit `--execute-fixture` arm. It uses a new isolated directory, no
listener and no real credential. It verifies save/reopen/list/export, changed
plant values restored by load, import without application, atomic imported load,
invalid/stale/foreign rejection identity, model refusal, READY and authentication
gates, restore acknowledgement and deletion. Finally it attempts every original
station value and deletes only its four fixture names; the parent restores
baseline/mode/run style and disarms all ten inputs. Offline tests prove cleanup
continues after failures. This hardware fixture has **not** run.

## Deployment and claim

The posture remains the v33 legacy zone-and-conduit bench, write-enabled by the
owner's 2026-09-29 decision. This item widens writes to whole station sets and
named host documents. The audit actor is a request claim until item 3 establishes
controller principals. Controller per-user enforcement and the write-enabled
claim remain **owed until S9 passes**. This item does not complete either gate.

The handover assigns import/Verify/download to the licensed owner desktop; its
recorded SDK probe refused **No valid license**. Import `C:\work\press55.L5X`
in Studio 5000 v33, Verify Controller, download to serial `7036B510` at
`192.168.100.89`, then restart the gateway. The owner's `done` authorizes the
named guarded hardware fixtures. First read the whole manifest and require
major 3, 79,992 bytes, row equality and the hash above; then check gateway
readiness, S3, parity, Phases 1–5 and both Phase 6 fixtures, including
`fraktal_ab_phase6_execute.py ... --sets --execute-fixture`.

The [JSON record](AB_PHASE6_SETS_BUILD_2026-10-02.json) contains generator
reports, source/artifact hashes, storage bounds, scope comparison and mutations.

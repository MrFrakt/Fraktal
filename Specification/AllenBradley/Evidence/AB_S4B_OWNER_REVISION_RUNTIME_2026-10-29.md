# S4b V6.10 native acceptance — 2026-10-29

**S4b passes E1–E9 together on local Echo.** The generic desktop discovers the
PLC-owned canonical tree without a station declaration, reads configuration
without mailbox queries and stays read-only. Echo ends back on genealogy with
the five original documents, 31 baseline cases and every final check passed.
Physical/CIP Security acceptance remains deferred; V2/Part III activation is S6.

Target: 601FC87B, 127.0.0.1 slot 0, 1756-L81E v38.011, under standing O3.
Session starts 2026-10-29 UTC and finishes 2026-10-30 UTC (2026-10-29 local).
Workspace `C:/work/fraktal-ab-s4b-owner-20261029/session_03`.

| Gate | Result |
|---|---|
| E1 candidate cases | 41/41: 31 main, two Access, eight configuration; exact restoration |
| E2 independent raw-read replays | 87/87, exact values and types |
| E3 concurrent Dart observer | 2,538 samples, zero Bad, zero client writes; Good limits and payload-free Uncertain checks pass |
| E4 independent configuration | Four pages, 1,100 exact scalars against a fresh legacy/Core oracle |
| E5 idle equivalence | 5,407 paths, zero differences |
| E6 generic acquisition | 5,407 values, seven modules; native V6.10 manifest and eight owner bindings |
| E7 native desktop | All 31 views LIVE; seven modules, three bus nodes; read-only action refusals; maximum mapped effective age 255.856 ms |
| E8 native scan | 7,135 monitor observations plus 20 final samples; median 966 µs, cumulative maximum 8,974 µs, zero overlaps on the 10 ms task |
| E9 rollback | Genealogy copy download/audits, five exact original host documents, 31/31 baseline cases, MANUAL/idle/logout, scanning/not restoring, saved=live, final checks/preflight/timing |

The SDK upload backup, download, read-back and effective-access audits pass.
TASK monitoring starts before download and uses the pre-Run marker; counters
are never cleared. Host/emulator CPU records are retained. No dumps, faults
requiring clearance, clock changes, power/vendor-state operations or Echo hard
kills occur. The original genealogy ACD is never opened.

Prepared ACD:
`84EC495F9D526316BC73C8412FAFAF4067B6A942BF1FD27E2369CCC3C516FBAC`.
Generated source:
`22DD1C2EBBDEFAB9BF45896F810B56DA9D90058274B0C0B1E497FAA303DAEE06`.
Native manifest:
`BBA485936140CE9EE1C7693824BB06E935940A335D86A8EB2FBAD9AD35C847B6`.
Exact Studio Capacity is 66%: 2,077,924 used / 1,067,804 available /
3,145,728 Blocks. SDK-mutated deployment/restore copies have separate retained
hashes; the pristine prepared image and original genealogy pin remain intact.

O9 publishes independent owner revisions for 29 existing header leaves/seven
modules and the read-only configuration view, plus separate scan progress.
Protocol 2 permits proofs inside its declared one-second bound; protocol 1
retains its strict scan-period bound. The observer's largest accepted row
window is 15.789 ms; this is not a widened protocol-1 allowance. Core values/
types, read tiers/freshness, attempts and D9 policy remain. No observation frame
is used by the Dart client; the migration oracle still uses its frozen proof.

Prerequisites are sealed in the [collector preparation](AB_S4B_OWNER_REVISION_COLLECTOR_PREPARATION_2026-10-29.md)
and [collector correction](AB_S4B_OWNER_REVISION_COLLECTOR_CORRECTION_2026-10-29.md):
2,356 AB tests, 759 HMI passed/12 skipped, 74 root tests, both v38 builds/
read-backs/access/SDK audits, locked dependencies, analyzer and Windows profile
build on Flutter 3.47.5/Dart 3.13.4. Three final-source profile rehearsals pass
at 383.054/407.711/420.990 ms; debug reproduces STALE. Hashes retain every
unchanged proof input. Preparation includes Capacity equality, scope-denial and
rollback failure-injection tests, and a prebuilt 16-file native desktop.

Two earlier sessions remain separate, unchanged records:

1. [Capacity precheck refusal](AB_S4B_OWNER_REVISION_PRECHECK_ATTEMPT_2026-10-29.md):
   the authorization template retained old figures. The guard stopped before
   any controller change; confirmation now derives from the measured image,
   with three readiness tests.
2. [Collector refusal](AB_S4B_OWNER_REVISION_RUNTIME_ATTEMPT_2026-10-29.md): Python
   acquisition omitted new owner-counter Symbols. The validator stopped the
   initial comparison. The correction captures declared scalars and still
   rejects missing/non-DINT/structured/array counters; the old code reproduces
   the refusal offline. That session rolled back with 31/31 baseline checks.

All failures remain archived, including the earlier offline timing/profile
attempts. Credentials, binaries and ACD/BAK are excluded from this payload.
Raw captures, source snapshots, logs, screenshots, metadata and hashes remain
append-only. The stage-exit commit/push follows O1, excluding unrelated edits.
Next: S5 typed command writer, Dart gateway and installer/tray on this accepted
image; then S6 retirement/host services. Physical S7 remains deferred under O2.

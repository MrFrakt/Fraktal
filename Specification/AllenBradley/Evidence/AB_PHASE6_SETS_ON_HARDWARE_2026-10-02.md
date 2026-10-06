# Fraktal/AB Phase 6 item 2 — parameter sets on hardware

**Result:** press55's station sets save, load, list, export, import and delete;
loads validate the whole transaction on the controller and apply no partial
values on refusal. All regression harnesses pass. Item 2 is complete on the
bench for station sets. Model load retains TC3's refusal pending integration.

**Date:** 2026-10-02, America/Bogota. The successful fixture/regression run was
06:30:12–06:34:14 UTC. The first attempt began at 06:22:44 UTC and exposed a
harness sequence defect, described below. Source build revision: `114ce9e`,
plus the three harness/test fixes recorded by SHA-256 in the JSON evidence.
The owner replied `done` after the requested Studio 5000 v33 import,
Verify/download and gateway restart. Studio verification is owner-reported;
no Studio transcript was captured here.

This append-only record follows the
[offline build](AB_PHASE6_SETS_BUILD_2026-10-02.md). The
[raw JSON](AB_PHASE6_SETS_ON_HARDWARE_2026-10-02.json) preserves the failed
attempt, cleanup, successful rerun, every regression, final readback and gates.

## Build readback

| Property | Observed |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510`, `192.168.100.89` |
| Build | `C:\work\press55.L5X` |
| SHA-256 | `AF0DFBC9080296BDC5E8D8D92BCD3464CBFDF3C6D276CE04A192F6594E9D3A23` |
| ContentHash / ConfigRevision | `5A1BD77C6D63F5FD` / `5905367` |
| Manifest major | 3 |
| Fields / Localization | 526/768 and 514/768 |
| Rationalization / WriteCapabilities | 23/32 and 9/64 |
| Manifest | **79,992 bytes**, coherent, every declared row equal, no findings |
| Timing | Initial 199.605 ms; repeat after fixtures 171.329 ms; 11 requests each |
| Valid / Truncated | 1 / 0 |
| Gateway | `ready`, `plcReady: true` before/after fixtures and after gates |

The template remains generated and tested offline. These are press55
measurements, not a claim for every target or the 100 KiB generation bound.

## Parameter-set behavior

The guarded set fixture passed **17/17**, including three read-only prerequisites.

| Check | Controller/host result |
|---|---|
| Save, export, reopen | Five live station records; portable header names Press and revision 5905367; reopened file equals export |
| List | One `phase6-station` entry through the generic HMI contract |
| Actual load | StationNumber changed from 1 to **99**, then load restored 1 and all five original station values |
| Import | Stored `phase6-import` without changing equipment values |
| Imported load | Applied the complete station document; StationNumber became 99 |
| Unknown final key | Refused; `Press / phase6.unknown`; all values unchanged |
| Invalid final value | Refused; `Press / press.requireTwoHandStart`; all values unchanged |
| Stale record revision | Refused; same final record identity; all values unchanged |
| Foreign root | Refused; scope `Other`; all values unchanged |
| Model save/export | Four live model records, model `M-100` |
| Model load | Refused with `project.mailbox.refused.config_set_model_load` (475), matching TC3 |
| READY | Actual AUTO `Running=1`, step 100; load refused (499), no changes |
| Authentication | Unauthenticated viewer LIST refused before commit; sequence stayed 136 |
| Restore acknowledgement | With no loss, ACK_CONFIG_RESTORE refused by its existing key (498) |
| Delete | Deleted one name; catalog count changed from four to three |

Unknown/invalid/stale/foreign and READY refusals use
`std.error.configSetRejected` (499). Successful loads are proved by values,
not acknowledgements alone. For the invalid final records, the first valid
record would have changed StationNumber from 99 to 1; it remained 99, proving
the controller did not partially apply that document.

Final readback confirms a bounded **16-entry** controller set audit with both
accepted requests and refusals, names, record counts and claimed User
`phase6-fixture`. Foreign-root, model-load and READY refusals remain in the ring,
beside model save/export and cleanup deletes. The controller reports
StorePresent 1, FILE_JSON 1, WindowMs 5000, Pending 0, Failed 0 and RestoreLost 0.
Successful host receipts are observed here; failed-I/O/expiry paths retain their
offline tests and mutations. Physical controller retention is not established.

The fixture instantiated the real gateway dispatch and serial-guarded writer
without a listener or real credential, using a new isolated host directory.
It did not modify the deployment's production set directory or read its secret.
The owner's existing gateway remained ready. No AB-specific HMI screen was added;
the HMI tests and refusal-read mutations remain offline evidence.

## First attempt and harness correction

The first attempt failed with:

```text
stale mailbox sequence: expected 56, got 57
```

Direct fixture helpers advanced the controller while the fixture gateway kept
its previous sequence. The strict gateway correctly refused the gap. Every
controller value, baseline, mode/style and all ten inputs were restored, but
four fixture documents remained in that isolated directory because cleanup
hit the same guard. A fresh serial/fingerprint-checked client deleted only those
four named documents; the cleanup record verifies the directory is empty and
all five station values match the original image.

The shared idle helper now accepts a command callback, retaining one owning
idle recipe. Idle, mode/start and typed writes in the set fixture all route
through its own gateway. The READY observation also uses the returned unit,
not the always-truthy wait tuple. The new regression exercises idle and typed
writes with direct commands forbidden. Three in-memory mutations—direct idle,
direct typed write and skipped restoration—are all killed by the 20-test baseline.

Only `fraktal_ab_phase6_sets_execute.py`, `fraktal_ab_press_execute.py` and its
new fixture regression test changed. Controller declarations, generator and
gateway implementation did not. Regeneration after the fixes still produces
press55 byte-for-byte; no additional download was needed. The corrected fixture
then passed 17/17 and restored all documents and station values.

## Regressions and final state

| Harness | Result |
|---|---|
| S3 health/timing, read-only | 6/6 |
| Phase 6 sets, unarmed | 3/3 |
| Phase 6 sets, armed | 17/17 |
| Phase 6 capture and read-only query | 10/10 |
| ST/SFC/LD parity | 25/25 |
| Phases 1, 2, 3, 4, 5 | 7/7, 6/6, 8/8, 11/11, 25/25 |

All writing harnesses checked serial/fingerprint and reported ten inputs cleared.
Final readback confirms StationNumber 1, RamExtendLimitMs 2000,
AirPressureMinKpa 450, ConflictTime 500, RequireTwoHandStart 1, baseline **950**,
AUTO **0**, CONTINUOUS **0**, Running/Error/Aborted/Complete all zero, and all
ten fixture inputs zero. Both isolated directories are empty. A subsequent
serial-guarded [full configuration read](AB_PHASE6_SETS_FINAL_CONFIG_2026-10-02.json)
also confirms baseline 950 after every regression.

S3 sampled 490 scans in 4.897 seconds. Execution was 575–770 µs, median
611.5 µs; initial task maximum 996 µs. Final readback after set/regression work
reports maximum **1710 µs** against the 10,000 µs period, zero overlap and
zero major/minor fault bits. This does not attribute the maximum to any one
operation. Clock synchronization/PTP remain zero and CPU/memory unavailable,
as already recorded for this bench.

Before this evidence commit, the AB suite passed **1364** tests; consistency
passed **32/32** with 0 errors and 0 warnings. These used `-B`, disabled bytecode
writes and fresh prefixes. The build's 23 Python/two HMI mutations and
429 HMI tests/6 skips remain its offline record; the three additional harness
mutations passed in this verification turn.

## Authorization and claim

The owner's current `done` authorized the named guarded fixture writes on this
exact controller, including restoration. No download, keyswitch, firmware,
network or clock change, nor gateway write-enablement, was performed by the agent.

The posture remains **v33 legacy zone-and-conduit**, write-enabled by the owner's
recorded 2026-09-29 decision. This item widens writes to whole station sets and
named host documents. Audit User remains a request claim. Controller per-user
access is item 3; model-load integration and the physical power-cycle/download/
upgrade retention matrix remain owed. **S9 and the write-enabled claim remain
owed.** The next handover item is controller per-user access, on `go on`.

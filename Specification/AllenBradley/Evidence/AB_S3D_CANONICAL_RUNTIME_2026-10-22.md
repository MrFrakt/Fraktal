# S3d canonical AlarmLog and StateFlags: accepted Echo runtime

Date: **2026-10-22**, America/Mexico_City. UTC timestamps in the payload span
October 22-23. Scope: local Echo **601FC87B**, 1756-L81E v38.011,
127.0.0.1 slot 0. This is the explicit **2,125-path genealogy subset**;
shipping V1/Part III remain authoritative and V2 stays inactive. No physical
controller, full-Core, production scheduler or HMI acceptance is claimed.

The owner approved the exact prepared image and guarded backup, download,
candidate fixture/observations, genealogy rollback, baseline fixture, MANUAL
normalization and final checks. The response and scope are in
`Session/authorization.json`. Fault clearing and clock changes were outside
scope and did not occur. No commit or push occurred. Authorization is consumed.

## Artifacts and native gates

| Artifact | SHA-256 |
|---|---|
| Generated source | `03E0775EDD8A1A22D88D198D4D3CE2B7C19A2F2029A40E3C428CB838FC2EE962` |
| Original prepared ACD pin | `E5CA9AB3493AABF93E72A728EBDF5630E8056EEA2AC82254B38913B8C7CF7C9D` |
| SDK-saved candidate | `8FBACD120BEB46891D34C8730ADB368081DC7F14D009421D10A24140154E8E01` |
| Fresh uploaded backup | `A16E4A88721408894E29B28042DDAA42E31F1D2994429EF1337214DF0F8E326F` |
| Immutable genealogy original | `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084` |

The original pin was never replaced after SDK saves. The genealogy original
was hash-checked and copied; only the copy was opened/downloaded. Its final
SDK-saved hash is `DC33DFAADB6B3447472CFC39B28B00FA06FE6BDD83FBC79A7733626249F25A01`.
Backup, candidate and rollback SDK logs pass `fraktal_ab_sdk_log_gate`;
backup requires Save/Save As because the upload operation is named Open Project
From Controller. Download/read-back and restored genealogy compare equivalently.
Backup/rollback access equals the sealed baseline's 109-tag policy; candidate
access audits the 132-tag image, including both read-only metadata bindings.

Both v38 compiler/build/read-back gates are reused from the exact unchanged
[preparation](AB_S3D_CANONICAL_PREPARATION_2026-10-22.md). All PLC/generator inputs
remain hash-identical. Of 70 preparation source bindings, 68 remain unchanged;
only the read-only acceptance acquisition harness and its tests changed here.
The payload preserves before/intermediate versions and both source bindings.

## Failed runs and acquisition correction

`initialize_01` stopped before authorization/controller work because its working
copy verifier expected an archived `.L5X.gz` filename to exist uncompressed.
`initialize_02` verifies decompressed bytes, all 216 sealed preparation artifacts,
70 source bindings and both ACD pins, then records the current approval.

The original paired read included all three canonical records and legacy
records. It took about **13.5 ms** against the unchanged **10 ms** task and
exhausted the 100-attempt scan proof. `candidate_regressions_01` stopped after
**eight passing rows**, at its first held-condition observation. State and
policy restoration passed; the acceptance audit correctly failed.

The first observer correction used V6.2 revision-cached definition records and
reduced legacy MSP batches from four to three. Idle 2,125-path equivalence then
passed, but `candidate_regressions_02` still exhausted 100 attempts after
**26 passing rows**. Its 36 earlier comparison captures passed; they are retained
as failed-run evidence, not substituted into the accepted fixture. Cleanup and
policy restoration passed again. The second acceptance audit correctly failed.

The final observer acquires the live root and legacy records over **two separate
read-only connections**, each identity-guarded to this Echo. Both acquisitions
finish before the closing generation sample. Cached records come from the
PLC's V6.2 binding rows; equal manifest/configuration/FragmentRevision tokens
enclose their use, and any intervening change rejects the comparison. Response
decoding happens after the proof closes. Partition/cache refusal and concurrent
completion inside the proof have focused tests.

The **whole-scan equal-even generation proof, 100 attempts/five-second budget,
PLC image, task period, generic reader and regression stimuli are unchanged**.
`candidate_regressions_03` passes all 31 rows. Accepted proof attempts range
**1-8** across the 48 paired captures including idle. This correction qualifies
the migration oracle; S4 production scheduling/transport budgets remain open.

## Accepted value and behavior scope

The approved image adds 1,469 alarm and nine flag paths to the prior 647:
**2,125 values and 2,125 types match**, with only the five explicit D2 array
bound mappings. Generic discovery reads seven modules and 2,125 paths without
a runtime station declaration. Native captures and legacy raw responses
independently re-decode to identical snapshots/oracle values in `capture_replay_02`.

| Accepted observations | Count / result |
|---|---|
| Candidate regression rows | 31/31 |
| Restored-baseline rows | 31/31, first run |
| Decision captures | 4 |
| Held/fault captures | 14; both kinds at ST/SFC/LD |
| Sequence captures | 21; seven cases per rendition |
| Reset captures | 8, forming four before/after pairs; all renditions |
| Paired captures including idle | 48, independently replayed |
| State-flag values | false and true |
| Alarm states observed in active slots | EMPTY=0, ACTIVE=1 |
| Closed event duration | positive; maximum observed 1,360 ms |
| Ring wrap | observed |
| Blocking reset | true before, false after; all renditions |

Sequence coverage retains completed steps shorter than 100 ms, sparse handled
warning notes, mode clearing, HELD/resume, abort, adopted fault and single-reset
restart across ST/SFC/LD. **WAIT_RESET was not runtime-observed**; it and slot
reuse retain model-test coverage. Full-Core event Category, ResetAt and
ShelvedUntil have no legacy oracle/store paths and remain explicit gaps.
Time-quality fields preserve the legacy false values. Flag Stale stays false
because its owner evaluates flags unconditionally. This fixture has no EM or
concurrent sequence branch; earlier stage gaps remain open.

There are **96 recorded regression rows** across the four executions:
8 + 26 + 31 candidate rows, then 31 baseline rows. The first two contribute
**34 extra recorded rows** and additional fixture commands. The initial MANUAL
check needed zero writes; candidate and baseline cleanup each needed existing
LOGIN/SET_MODE(1)/LOGOUT frames, **six known additional mailbox commands**.
Individual controller tag-write calls were not instrumented; these row counts
must not be presented as an exact total write count.

## Capacity, sizes and scan

Qualified automatic Studio Capacity is **41%**: **1,290,016 used /
1,855,712 available / 3,145,728 total Blocks**, **+182,464** over S3c. The
source-preserving, two-sample receipt is sealed in preparation. Blocks are not
assumed bytes. This offline estimate is separate from online memory.

The held-out five-sample forecast was 1,287,360 Blocks, error -2,656
(-0.2059%), planning budget 1,550,445. It remains advisory; the accepted
measurement is added as the sixth catalog sample for future forecasts.

| Native record | Template / complete payload bytes |
|---|---:|
| Press root | 77,304 |
| Sequence definitions | 7,308 |
| Alarm metadata | 16,616 |
| Total | 101,228 |

Each Template byte size equals its complete native raw payload. These are
measured records, not source-size estimates or transport-overhead assumptions.

| Native TASK observation, 20 samples | Candidate | Restored genealogy |
|---|---:|---:|
| LastScanUs median | 437 | 99 |
| LastScanUs range | 436-437 | 99-100 |
| Cumulative MaxScanUs | 3,111 | 1,167 |
| OverlapCount | 0 | 0 |

Workloads/history differ; subtracting these observations does not isolate
publication cost. A separate earlier read-only diagnostic sample is also retained.

## Closing gates and state

Exact gate output is preserved in `Runtime/`:

- AB discovery suite: **Ran 2066 tests in 276.677s / OK**.
- Root tests: **Ran 74 tests in 1.942s / OK**.
- Focused final read-window/MSP tests: **Ran 14 tests in 0.007s / OK**.
- `check_ab_spec.py`, `check_ab_contracts.py`: pass.
- `check_consistency.py --strict`: **0 error(s), 0 warning(s)**.
- Whitespace gate: pass, with CR-at-EOL configuration.
- Both v38 native compiler/read-back/access gates: pass in unchanged preparation;
  downloaded candidate and restored baseline read-back/access: pass here.
- HMI/Flutter gates: not applicable; no HMI change was made by this work.

Final and closing read-only guards confirm exact identity, Echo service/listener,
**Run, not faulted, Remote, scanning, actual MANUAL=1/idle, logged out, not
restoring**, all five saved/live documents equal, original policy and unchanged
preflight. The immutable original hash is unchanged. No fault clear or clock
change occurred. All **14 predecessor seals / 2,258 artifacts** verify unchanged.

The payload manifest hashes every archived file and this report. Native ACDs
and credential files/contents are excluded. Failed runs remain archived. S3d
passes at this scope; **S3e preparation is next**, with a new exact-image gate
and current authorization required before any future controller session.

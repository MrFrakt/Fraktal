# Fraktal/AB Phase 6 access — Studio Boolean assignment correction

**Date:** 2026-10-02, America/Bogota. **Parent:** `e09f6cf`.
**Stage:** regenerated and tested offline; owner Studio v33 Verify/download and
hardware verification pending. No controller writes were performed.
The original [press56 build record](AB_PHASE6_ACCESS_BUILD_2026-10-02.md)
remains unchanged. The companion [JSON](AB_PHASE6_ACCESS_BOOLEAN_FIX_2026-10-02.json)
records corrected artifacts, source hashes, gates and the regression mutation.

## Owner compiler result and cause

Owner Studio v33 Verify of press56 reported **54 errors, zero warnings**:
`'TRUE': Referenced tag is undefined.` The affected lines run from 16 through
713 of the SHA routine. All 54 are emitted by the same `_move_bits` helper's
`AccessBits.EnableIn := TRUE;` statement. I introduced that unsupported literal;
the test model also incorrectly accepted TRUE/FALSE as Boolean literals, so its
successful SHA runs did not expose the compile defect.

The helper now emits `AccessBits.EnableIn := 1;`. The model tokenizes TRUE/FALSE
as ordinary tag names, matching the reported compiler behavior; referencing
either without a declared tag faults. A platform regression scans every emitted
ST routine in both press and template, including SHA and SFC actions, to reject
these names. It strips comments so explanatory text is allowed.
Rockwell's [1756-PM007 Structured Text manual](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm007_-en-p.pdf)
defines Boolean results as 1/0 (pages 14, 16–17) and uses numeric assignments for
open/closed outlets (page 25). The owner's v33 result is the evidence for the
literal-name rejection; Studio Verify of the corrected artifact is still pending.

## Corrected artifacts

Both declarations were regenerated from `C:\work\seed_v33.L5X`. A second
generation reproduces each file byte-for-byte. Comparison against the original
artifacts proves the complete change is exactly 54 `EnableIn := TRUE`
assignments replaced by `EnableIn := 1`; no L5X was hand-edited.

| Property | Press | Station template |
|---|---|---|
| File | `C:\work\press57.L5X` | `C:\work\phase6_access_bool_fix_template.L5X` |
| SHA-256 | `85D65A2A093A4DD1381309378917BA1FEA25C95EF4176C1988C752E0F09B9622` | `08B3C27ADDF4B6F6FE42DB5A63190FEFD478847969E17D28116F43A81C31C0B6` |
| ContentHash | `0FC1A37DB998B41C` | `C18743A4092531BF` |
| ConfigRevision | 1032611 | 12683075 |
| Manifest bytes / major | 79,992 / 3 | 79,992 / 3 |
| Fields | 544 / 768 | 358 / 768 |
| Localization | 541 / 768 | 452 / 768 |

The published contract, capacities, private registrations, audit data, HMI,
I/O, tasks, AOIs and mode-chain routines are unchanged. ContentHash and revision
therefore stay the same; the file SHA identifies this corrected logic build.
The prior generic HMI Web artifact remains applicable.

## Checks and handoff

- Full AB suite: **1,401 passed**, including independent SHA vectors, strict
  intermediate arithmetic checks and the complete emitted 257-hash login.
- Consistency: **33 passed**, zero errors and warnings.
- Restoring the bad EnableIn emission in child memory makes the new platform
  regression fail by assertion: **one mutation killed**, one-test baseline passes.
  Bytecode writes were disabled, a fresh cache prefix used, and no repository
  source or existing cache was changed by the mutation run.
- The corrected-file SDK probe exited 1 during OpenLogixProjectAsync:
  `OperationFailedException: No valid license. C:\work\press57.L5X`.
  Owner Studio remains the required compile gate; no corrected compile pass is
  claimed here. HMI source is unchanged, so its prior 431-pass, six-skip,
  clean-analysis and successful Web-build record is retained.

Import **`C:\work\press57.L5X`** in Studio 5000 v33 and Verify Controller.
On a clean Verify, download to serial `7036B510` at `192.168.100.89`, restart
the gateway and reply `done` for the guarded hardware loop. The v33 legacy
zone-and-conduit bench remains write-enabled by the 2026-09-29 decision;
controller access, runtime hash cost, physical retention and the S9 write-enabled
claim still require their pending hardware evidence. This correction adds no
new write operation and does not authorize controller writes by the agent.

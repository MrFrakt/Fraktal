# Fraktal/AB — Phase 1 on the bench: compiled, downloaded, observed

**Result:** Phase 1 of the AB/TC3 parity plan
([`Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md`](../../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md))
**compiled in Studio v33, was downloaded, re-passed §146 parity 17 of 17, and
passed 7 of 7 checks of its own features on the controller.**

**Date:** 2026-09-30 · **Repository revision:** `f21aad7`
**Raw record:** [`AB_PHASE1_ON_HARDWARE_2026-09-30.json`](AB_PHASE1_ON_HARDWARE_2026-09-30.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press30.L5X`: `ContentHash 382A4E596132C0B0`, manifest schema major 2 |
| Declaration | the same hash, so the controller matches the repository |

## 1. The compile gate

The Logix Designer SDK probe on the bench workstation still refuses with
`OperationFailedException: No valid license`, as it did for press26 and
press28. The owner imported press30 in Studio 5000 v33 on the licensed desktop
and downloaded it, and the controller reports its hash. That is the real
compiler accepting the constructs this generator emitted for the first time in
Phase 1:

- `GSV(WallClockTime,,DateTime,FRK_Press_Clock[0])` in structured text;
- `FOR` loops over the alarm slots;
- `MOD`, in the millisecond arithmetic and the ring index;
- the new members in the library AOI's context, `FRK_T_ModuleCtx`.

## 2. §146 parity, re-run because Phase 1 changed control flow

Phase 1 moved the alarm log and the diagnostic stamps after the chain
renditions, made every step write its condition records in all three
languages, and added `ReportedSource` to the REPORT step. The 17/17 of
press28 therefore did not transfer.

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0 | 1341.4 ms | 1137.3 ms | 1324.9 ms |
| HELD at step 180 → self-resumed | ✓ | ✓ | ✓ |
| Held reason / severity | 6130 / LOW | same | same |
| Abort stands down to step 0, Running 0, Error 0 | 3.0 ms | 3.0 ms | 2.9 ms |

Trace and visited step set match ST for SFC and LD. **17 of 17.** Mailbox
sequence seed 13. Cycle times are within 5 ms of press28's, so the added
per-scan work is not visible at this resolution.

## 3. Phase 1's own features, on the controller

`fraktal_ab_phase1_execute.py`, through the harness's declared write surface
only. Each row reads the controller's tags and the projection a client reads.
The rendition is ST; section 2 already showed the three renditions agree.

| Row | Observed |
|---|---|
| Conditions at N100 | part absent, air ok, two-hand released: `CondOk` `[0, 1, 0]`, `ActiveStepNumber` 100; published `partPresent` ✗, `airPressureOk` ✓, `twoHandStart` ✗, slot 4 empty |
| A condition follows its input | a part arrives: `[1, 1, 0]`, still at 100 |
| Adopted fault → blocking manual alarm | the slide's device fault adopted: slot 1 ACTIVE, reason 6102, MANUAL_RESET, HIGH, `SourceModuleId` 4 (`Press.PartSlide`), come `2026-09-30T17:47:12.798Z`, `Blocking` 1; the Unit's `DiagReason` 6102, published `project.reason.device_fault`, `IoTag` empty |
| START refused while it waits | refused, `DiagnosticKey` 227 = `alarm_blocks_start` |
| One reset closes it into the ring | `RingHead` 1, CLOSED, gone 230 ms after come, `Blocking` 0, the Unit's diagnostic clear |
| START accepted after the reset | accepted |
| A report is an occurrence | the ram failing at N200 is reported, not adopted: one closed AUTO_RESET ring entry, come = gone, sourced `Press.PressRam`; `Blocking` 0; the Unit waits at the N210 decision with **no** diagnostic |

The last row is the defect Phase 1 item 4 fixed, observed fixed: before it,
this report would have become the Unit's published diagnostic permanently.

## 4. Not observed on hardware, and why

- **The sensor a timeout names.** A cylinder TIMEOUT needs a `Par_TimeoutMs`
  shorter than the declared 500 ms, and that parameter is not on the harness
  write surface. The write surface is a safety property of these tools, so it
  was not widened for a test. The device fault injected here correctly names
  no sensor (`IoRoles` 0). The timeout's attribution, `_101B301A` extending
  the slide and so on, is proved on the ST model (`test_fraktal_ab_diagnostics`),
  which runs the same generated AOI body.
- **The clock is not synchronized.** The published onset read about 7.8 s
  ahead of this workstation's clock. That is why every timestamp is published
  with `TimeSynchronized` false: PTP is not enabled on this bench (AB S9).

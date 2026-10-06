# Fraktal/AB — TC3's run styles on the bench (Phase 5a)

**Result:** press44 was downloaded. **Phase 5 passed 10/10.** SINGLE_STEP and
HOLD_TO_RUN pace the press in ST, SFC and LD alike, and nothing regressed:
§146 parity 25/25, Phase 1 7/7, Phase 2 6/6, Phase 3 8/8, Phase 4 11/11.

**Date:** 2026-10-01 · **Repository revision:** `2abfad4`
**Raw record:** [`AB_PHASE5A_RUN_STYLES_ON_HARDWARE_2026-10-01.json`](AB_PHASE5A_RUN_STYLES_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press44.L5X`: `ContentHash F1200055EB9C8388`, `ConfigRevision 15802368` |
| Manifest | read back from the controller, every table matching; 40,824 bytes |
| Gateway | `/healthz` ready, PLC ready: it projected the station against the new hash |

## 1. Run styles

Proved by what the plant did, counted from the modules' own command counters
(the lesson of D7), never by the steps the chain entered.

| Row | Observed |
|---|---|
| Published | `SupportedRunStylesPublished` true for all three; `RunStyle` 0 |
| Refusals | style 3 refused with `std.error.unsupportedRunStyleRequest`, style kept; a Step while stopped and a hold in SINGLE_STEP refused by name; a release accepted |
| SINGLE_STEP, ST / SFC / LD | commands issued before the first Step and after each one: `[0, 1, 1, 1, 1, 1, 1, 1, 1]` in each; the cycle closes and parks at N100; 4.57 / 4.56 / 4.57 s |
| HOLD_TO_RUN, ST / SFC / LD | unheld for 0.6 s: at N110, nothing issued. Held, then released once the slide was commanded: the slide arrived, and the chain waits at N180 with the door close un-issued (3 commands so far). Held again: the cycle completes with its 8 commands. The same in each rendition |
| A stop ends the hold | held (`HoldRun` 1), then STOP: `HoldRun` 0. The next START in HOLD_TO_RUN waits at N110, nothing issued |
| Left as found | CONTINUOUS, stopped |

The release-mid-motion row is TC3's own semantics: `M_TryIssue` paces the
command, not the motion, so a command once issued runs to Done.

The stop row is the binding's one deliberate difference from TC3. A Unit that
is not running holds no hold. TC3 keeps `_holdRun` across a stop, which a
release lost with the HMI link would turn into an unheld START.

## 2. A harness defect, found and fixed on this run

The first run also passed 10/10. Its stepped cycles took 8.6, 8.6 and 12.6 s,
not the ~4.5 s the idles and motions account for.

- **The wait.** After each Step the harness waited for `Issued` to rise. A
  command that completes at once (the ram already up, the door already open)
  holds `Issued` for about two 10 ms scans, under one CIP read, so the poll
  missed it and ran into its 4 s settle.
- **The counts were not affected.** They come from the module counters, not
  from that wait.
- **The fix.** The harness now waits for `StepPending` to return to 0, which
  the issue consumes and which stays consumed. The re-run took 4.57 / 4.56 /
  4.57 s. Both runs are in the raw record.

## 3. Regression

| Gate | Result |
|---|---|
| §146 parity | 25/25. ST 966.7 ms, SFC 966.6 ms, LD 967.3 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 (alarm log, step conditions, reset) | 7/7 |
| Phase 2 (flow chart) | 6/6 |
| Phase 3 (modules, stall, dwell, air) | 8/8 |
| Phase 4 (manual commands, interlocks, release reports) | 11/11 |

Every harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared.

## 4. Not shown here

- **The HMI's step toggle, Step button and hold button, in a browser.** The
  paths the HMI reads (`RunStyle`, `SupportedRunStylesPublished`) are the
  ones read above, and its three requests are the mailbox kinds exercised
  here.
- **Access gating** of the style and of Step and hold, which waits for
  Phase 6.

# Fraktal/AB — the two-hand start on the bench (Phase 3, item 2)

**Result:** the third library type, TC3's `FB_TwoHandStartCM`, and the press's
use of it (a start from the buttons and a latched start) **compiled in Studio
v33 and were downloaded. §146 parity re-passed 17 of 17, and Phases 1, 2 and 3
re-passed 7/7, 6/6 and 6/6.** The last now shows on the controller that a press
made before the part never starts the stroke.

**Date:** 2026-09-30 · **Repository revision:** `577b4b2`, plus the Phase 2
script correction in §4
**Raw record:** [`AB_PHASE3_TWO_HAND_ON_HARDWARE_2026-09-30.json`](AB_PHASE3_TWO_HAND_ON_HARDWARE_2026-09-30.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press35.L5X`: `ContentHash 2D6DF2306FB4F5CF`, manifest schema major 2 |
| Declaration | the same hash, so the controller matches the repository |

## 1. §146 parity, now started the way TC3 starts

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0, parked at N100 | 958.0 ms | 743.5 ms | 943.2 ms |
| HELD at step 180 → self-resumed | ✓ | ✓ | ✓ |
| Held reason | 12001 | same | same |

**17 of 17.** Every cycle was started by START and then a fresh two-hand
press (`px.start_cycle`): release, the module arms, press, `StartPulse`, and
`StartLatched` with the part and air present. N180's hold now reads the
module's `SafeActive`, and it held and self-resumed in all three renditions.
Each cycle parked at N100: the cycle end dropped the latch, and N100 waited for
a press that the harness withheld.

## 2. Phases 1 and 2

Phase 1: **7 of 7.** Phase 2: **6 of 6** (see §4).

## 3. Phase 3 (`fraktal_ab_phase3_execute.py`): 6 of 6

| Row | Observed |
|---|---|
| The part-present sensor follows its source | 0 → 1 → 0 at quality 1, `std.moduleType.digitalInput` |
| A stuck slide times out and names its sensor | 589 ms, `10101`, `_101B301A` on the Unit and the alarm |
| A held child rolls up | the ram held at N110: the Unit's `2003`, not timed out |
| A step that waits past StallTime is stalled | N100 with no part: timed out at `StallMs` 30000, `2005`, no error |
| **A press before the part never starts the stroke** | START and a two-hand press with no part, then the part arrives: after 0.5 s still at N100, `StartLatched` 0, `Running` 1 |
| The stall clears when the step moves | a fresh press with the part there: step 110, `StepTimedOut` 0 |

The fifth row is TC3's `FB_PressDemoUnit` rule observed on AB's controller:
the latch counts a press only when the part and air are already there.

## 4. One script correction

Phase 2's last row failed on the first run: `annotations` 1, `WarnReason`
10101 still on N200. The row waited for the *next* cycle to pass N200 cleanly,
but that cycle correctly waited at N100 for a fresh two-hand press. The cycle
end drops the latched start, and the script never pressed. The row now waits
for N100 and presses (`px.two_hand_press`). The re-run passed 6 of 6, and the
recorded Phase 2 result is that re-run. No controller change.

## 5. Not observed on hardware

- **`Par_RequireRelease` off, and an unhealthy bus.** Neither is on the
  declared write surface. Both are proved on the ST model
  (`test_fraktal_ab_two_hand`).
- **A two-hand press starting the press from ready without START.** The
  harness always sends START first. The start rule and its ordering are proved
  on the model, including that an open manual alarm blocks it.

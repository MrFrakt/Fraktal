# Fraktal/AB — press24.L5X, and a correction to two earlier records

**Result:** the press demo regenerated from the current declaration as
`press24.L5X`, carrying `ContentHash 5BEB5FFDF33D77E2` / `ConfigRevision
6024031` and `FRK_Press_ModelRequest` at `ExternalAccess="None"`. It is ready
for Studio import, Verify and download. **Nothing was downloaded.**

It also corrects a claim made earlier today.

**Date:** 2026-09-29 · **Repository revision:** `a173275`
**Seed:** `C:/work/seed_v33.L5X` · **Output:** `C:/work/press24.L5X`

## 1. The correction

[`AB_PARITY_HARNESS_AND_MODELREQUEST_2026-09-29.md`](AB_PARITY_HARNESS_AND_MODELREQUEST_2026-09-29.md)
§1 and [`AB_PARITY_146_2026-09-29.md`](AB_PARITY_146_2026-09-29.md) §1 both say
the generated **logic** is byte-identical across `0f96173`. **That is wrong.**
Both stand as written — evidence is append-only — and this record supersedes
the claim in each.

The measurement behind it was `all_generated_logic(app)`, compared before and
after. That function is `module_logic` + `unit_logic` + `routine_logic`. It does
**not** include the mailbox dispatch routine, which `fraktal_ab_mailbox.py`
emits. Its name reads like a complete answer and it is not one — the same shape
of error as the read-surface gate that reported clean while comparing nothing.
The honest check is to regenerate and diff the artifact, which is what this
record does.

## 2. What `0f96173` actually changes

Diffed against an L5X generated from `4e65ba6`, the commit immediately before
it, from the same seed:

| Change | Lines |
|---|---|
| `FRK_Press_ModelRequest` `Read/Write` → `None` | 2 |
| `DiagnosticKey := N` literals in mailbox refusal branches | 40 |
| Manifest data rows (`Fields`, `Localization`, `Rationalization`, `Operations`) | the remainder of 520 |

All 40 ST lines are the same shape: a numeric key shifted by exactly one,
each still carrying the comment naming the same portable key, because removing
`FRK_Press_ModelRequest` renumbered every key at or above 152 and the
`Localization` table moved with them.

**Unchanged:** control flow, every mode chain in all three renditions, every
module AOI, every UDT, the task, and the scan order. The parity result in
[`AB_PARITY_146_2026-09-29.md`](AB_PARITY_146_2026-09-29.md) therefore still
transfers — the program it measured is the program this build runs, and the
refusal behaviour is identical because the index and its table moved together.

## 3. A property worth knowing: the hash does not cover the logic

`press23.L5X` (the build the controller carries) and an L5X generated from
`4e65ba6` **both report `122F979D6C141EC8`**, yet they differ: two `CASE` label
lines in the mailbox dispatch gained kinds 35 and 36 between them, as refused
kinds. Adding a refused kind changes the program and not the published
contract, so the hash is unmoved.

`ContentHash` is a hash of the **published contract**, not of the build. It
answers "does a client's picture of this station still hold". It does not
answer "is this the same program". Compare programs by regenerating and
diffing; that is now stated in Part III §11 so the next reader does not have to
rediscover it.

## 4. The generated build

| | |
|---|---|
| `ContentHash` | `5BEB5FFDF33D77E2` |
| `ConfigRevision` | `6024031` |
| Modules | 4 — `Press`, `Press/Door`, `Press/PartSlide`, `Press/PressRam` |
| Fields | 156 of 192 |
| Localization | **250 of 256** |
| Rationalization | 12 of 32 |
| Operations | 6 of 32 |
| Truncated | false |
| Programs / Routines / Tasks | 1 / 1 / 1 |

**The `Localization` table has six rows of headroom.** It is the only table
near its capacity, and every new reason, step, chain or refusal key consumes a
row. The next handful of keys will need the capacity raised; a table that fills
is reported by `Truncated`, so it fails visibly rather than silently, but six
rows is not much warning.

## 5. Not done

Studio v33 Verify and the download both need a logged-in Studio desktop and
explicit authorization at the download step. Neither was attempted here. Until
one happens, the controller runs `122F979D6C141EC8` with
`FRK_Press_ModelRequest` still externally writable.
